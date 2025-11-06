"""
비플로우 웹사이트 자동 업로드 모듈
Selenium을 사용하여 연동쇼핑몰 프로모션 관리에 엑셀 파일 업로드
"""

import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class BeeflowUploader:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.driver = None
        
    def init_driver(self):
        """Chrome 드라이버 초기화"""
        options = webdriver.ChromeOptions()
        # options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 15)
        
    def login(self):
        """비플로우 로그인"""
        print("  [로그인] 시작...")
        self.driver.get("https://b-flow.co.kr")
        time.sleep(2)
        
        try:
            login_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '로그인')]"))
            )
            self.driver.execute_script("arguments[0].click();", login_btn)
            time.sleep(1.5)
            
            email_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
            )
            email_input.send_keys(self.email)
            time.sleep(0.5)
            
            password_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            password_input.send_keys(self.password)
            time.sleep(0.5)
            
            submit_btn = self.driver.find_element(By.CSS_SELECTOR, ".modal .login-btn, .v--modal .login-btn")
            self.driver.execute_script("arguments[0].click();", submit_btn)
            
            time.sleep(2)
            print("  ✓ 로그인 완료")
            
        except Exception as e:
            print(f"  ✗ 로그인 실패: {e}")
            self.driver.save_screenshot("login_error.png")
            raise
    
    def select_date_in_calendar(self, target_date: datetime, is_end_time: bool = False):
        """vdatetime 캘린더에서 날짜 + 시간 선택"""
        try:
            time.sleep(1)
            
            # 1. 연도 확인
            try:
                year_div = self.driver.find_element(By.CSS_SELECTOR, ".vdatetime-popup__year")
                current_year_text = year_div.text.strip()
                
                if current_year_text and current_year_text.isdigit():
                    current_year = int(current_year_text)
                    
                    if current_year != target_date.year:
                        self.driver.execute_script("arguments[0].click();", year_div)
                        time.sleep(0.8)
                        
                        year_items = self.driver.find_elements(By.CSS_SELECTOR, ".vdatetime-popup__list-picker__item")
                        for item in year_items:
                            if item.text == str(target_date.year):
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", item)
                                time.sleep(0.3)
                                self.driver.execute_script("arguments[0].click();", item)
                                time.sleep(1)
                                break
            except Exception as e:
                pass
            
            # 2. 월 선택
            try:
                max_attempts = 24
                for attempt in range(max_attempts):
                    try:
                        month_selector = self.driver.find_element(By.CSS_SELECTOR, ".vdatetime-popup__month-selector__current")
                        month_text = month_selector.text.strip()
                        
                        if not month_text:
                            time.sleep(0.5)
                            continue
                        
                        parts = month_text.split('월')
                        current_month = int(parts[0].strip())
                        current_year_in_month = int(parts[1].strip())
                        
                        if current_year_in_month == target_date.year and current_month == target_date.month:
                            break
                        
                        if current_year_in_month < target_date.year:
                            next_btn = self.driver.find_element(By.CSS_SELECTOR, ".vdatetime-popup__month-selector__next")
                            self.driver.execute_script("arguments[0].click();", next_btn)
                        elif current_year_in_month > target_date.year:
                            prev_btn = self.driver.find_element(By.CSS_SELECTOR, ".vdatetime-popup__month-selector__previous")
                            self.driver.execute_script("arguments[0].click();", prev_btn)
                        else:
                            if current_month < target_date.month:
                                next_btn = self.driver.find_element(By.CSS_SELECTOR, ".vdatetime-popup__month-selector__next")
                                self.driver.execute_script("arguments[0].click();", next_btn)
                            else:
                                prev_btn = self.driver.find_element(By.CSS_SELECTOR, ".vdatetime-popup__month-selector__previous")
                                self.driver.execute_script("arguments[0].click();", prev_btn)
                        
                        time.sleep(0.4)
                        
                    except Exception as e:
                        time.sleep(0.5)
                        continue
                        
            except Exception as e:
                pass
            
            # 3. 일 선택
            try:
                date_items = self.driver.find_elements(By.CSS_SELECTOR, 
                    ".vdatetime-popup__date-picker__item:not(.vdatetime-popup__date-picker__item--header):not(.vdatetime-popup__date-picker__item--disabled)")
                
                for item in date_items:
                    if item.text.strip() == str(target_date.day):
                        self.driver.execute_script("arguments[0].click();", item)
                        time.sleep(0.5)
                        break
            except Exception as e:
                pass
            
            # 4. OK 버튼 클릭 (날짜 확인)
            try:
                ok_btn = self.driver.find_element(By.XPATH, "//div[@class='vdatetime-popup__actions__button' and text()='Ok']")
                self.driver.execute_script("arguments[0].click();", ok_btn)
                time.sleep(1)
            except Exception as e:
                pass
            
            # 5. 시간 선택
            try:
                time.sleep(1)
                time_pickers = self.driver.find_elements(By.CSS_SELECTOR, ".vdatetime-popup__list-picker")
                
                if len(time_pickers) >= 2:
                    # 시(hour)
                    hour_picker = time_pickers[0]
                    target_hour = "23" if is_end_time else "00"
                    
                    hour_items = hour_picker.find_elements(By.CSS_SELECTOR, ".vdatetime-popup__list-picker__item")
                    for item in hour_items:
                        if item.text.strip() == target_hour:
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", item)
                            time.sleep(0.2)
                            self.driver.execute_script("arguments[0].click();", item)
                            break
                    
                    time.sleep(0.3)
                    
                    # 분(minute)
                    minute_picker = time_pickers[1]
                    target_minute = "59" if is_end_time else "00"
                    
                    minute_items = minute_picker.find_elements(By.CSS_SELECTOR, ".vdatetime-popup__list-picker__item")
                    for item in minute_items:
                        if item.text.strip() == target_minute:
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", item)
                            time.sleep(0.2)
                            self.driver.execute_script("arguments[0].click();", item)
                            break
                    
                    time.sleep(0.3)
                    
            except Exception as e:
                pass
            
            # 6. OK 버튼 클릭 (캘린더 닫기)
            try:
                ok_btn = self.driver.find_element(By.XPATH, "//div[@class='vdatetime-popup__actions__button' and text()='Ok']")
                self.driver.execute_script("arguments[0].click();", ok_btn)
                time.sleep(0.5)
            except Exception as e:
                pass
                
        except Exception as e:
            print(f"      캘린더 선택 실패: {e}")
    
    def select_channel_from_multiselect(self, channel_name: str):
        """multiselect에서 채널 선택"""
        try:
            # 채널명 매핑 (한글 → 영문)
            channel_mapping = {
                "SSG": "ssg",
                "지마켓": "gmarket",
                "지마켓(상품번호)": "gmarket",
                "옥션": "auction",
                "옥션(상품번호)": "auction",
                "11번가": "11st",
                "쿠팡": "coupang",
                "위메프": "wemakeprice",
                "GS샵": "gsshop",
                "롯데ON": "lotte",
                "CJ몰": "cjmall",
                "하프클럽(신규)": "newhalfclub",
                "롯데아이몰": "lotteimall",
                "카카오쇼핑하기": "kakaotalkshopping",
                "카카오스타일": "kakaostyle",
                "H몰": "hmall"
            }
            
            api_channel_name = channel_mapping.get(channel_name, channel_name.lower())
            
            # multiselect 찾기
            multiselect = None
            try:
                multiselect = self.driver.find_element(By.CSS_SELECTOR, ".multiselect.br-select")
            except:
                try:
                    multiselect = self.driver.find_element(By.CSS_SELECTOR, ".multiselect")
                except:
                    return False
            
            # multiselect 클릭하여 드롭다운 열기
            self.driver.execute_script("arguments[0].scrollIntoView(true);", multiselect)
            time.sleep(0.3)
            self.driver.execute_script("arguments[0].click();", multiselect)
            time.sleep(1.5)
            
            # 채널 옵션 선택
            channel_options = self.driver.find_elements(By.CSS_SELECTOR, ".multiselect__element")
            
            for option in channel_options:
                try:
                    inner_span = option.find_element(By.CSS_SELECTOR, ".multiselect__option span")
                    option_text = inner_span.get_attribute('textContent').strip().lower()
                except:
                    option_text = option.get_attribute('textContent').strip().lower()
                
                if option_text == api_channel_name:
                    clickable = option.find_element(By.CSS_SELECTOR, ".multiselect__option")
                    self.driver.execute_script("arguments[0].click();", clickable)
                    time.sleep(1)
                    print(f"    ✓ 채널 선택: {channel_name}")
                    return True
            
            print(f"    ✗ 채널 '{channel_name}' 찾을 수 없음")
            return False
            
        except Exception as e:
            print(f"    ✗ 채널 선택 실패: {e}")
            return False
            
    def upload_promotion(self, file_path: str, channel_name: str, start_date: datetime, end_date: datetime):
        """프로모션 업로드"""
        filename = os.path.basename(file_path)
        promotion_name = filename.replace('.xlsx', '').replace('_', ' ')
        
        print(f"\n  [업로드] {filename}")
        print(f"    채널: {channel_name}")
        print(f"    기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
        
        try:
            # 페이지 접속
            self.driver.get("https://b-flow.co.kr/distribution/promotion/create#/")
            time.sleep(2)
            
            # 프로모션명 입력
            name_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='프로모션']"))
            )
            name_input.clear()
            name_input.send_keys(promotion_name)
            time.sleep(0.5)
            
            # 시작일 설정
            date_inputs = self.driver.find_elements(By.CSS_SELECTOR, ".vdatetime input.form-control")
            if date_inputs:
                self.driver.execute_script("arguments[0].click();", date_inputs[0])
                self.select_date_in_calendar(start_date, is_end_time=False)
            
            # 종료일 설정
            date_inputs = self.driver.find_elements(By.CSS_SELECTOR, ".vdatetime input.form-control")
            if len(date_inputs) > 1:
                self.driver.execute_script("arguments[0].click();", date_inputs[1])
                self.select_date_in_calendar(end_date, is_end_time=True)
            
            # 채널 선택
            self.select_channel_from_multiselect(channel_name)
            
            # 상품 체크박스 클릭
            checkboxes = []
            try:
                checkboxes = self.driver.find_elements(By.XPATH, "//label[contains(text(), '상품')]/ancestor::div[contains(@class, 'pretty')]//input[@type='checkbox']")
            except:
                pass
            
            if not checkboxes:
                try:
                    pretty_divs = self.driver.find_elements(By.CSS_SELECTOR, ".pretty")
                    for div in pretty_divs:
                        label = div.find_element(By.TAG_NAME, "label")
                        if "상품" in label.get_attribute('textContent'):
                            checkbox = div.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
                            checkboxes = [checkbox]
                            break
                except:
                    pass
            
            if checkboxes:
                self.driver.execute_script("arguments[0].scrollIntoView(true);", checkboxes[0])
                time.sleep(0.3)
                
                if not checkboxes[0].is_selected():
                    try:
                        self.driver.execute_script("arguments[0].click();", checkboxes[0])
                    except:
                        parent_div = checkboxes[0].find_element(By.XPATH, "..")
                        self.driver.execute_script("arguments[0].click();", parent_div)
                    time.sleep(2)
                    print("    ✓ 상품 체크박스 선택")
            
            # 엑셀 업로드 버튼 클릭
            upload_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), '엑셀 업로드')]")
            for btn in upload_buttons:
                if btn.is_displayed() and btn.is_enabled():
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                    time.sleep(0.3)
                    self.driver.execute_script("arguments[0].click();", btn)
                    time.sleep(2)
                    break
            
            # 파일 업로드
            if not os.path.isabs(file_path):
                possible_paths = [
                    os.path.abspath(file_path),
                    os.path.abspath(os.path.join("..", file_path)),
                    os.path.abspath(os.path.join(".", file_path.replace("outputs/", "")))
                ]
                
                for test_path in possible_paths:
                    if os.path.exists(test_path):
                        abs_file_path = test_path
                        break
                else:
                    raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
            else:
                abs_file_path = file_path
                
            if not os.path.exists(abs_file_path):
                raise FileNotFoundError(f"파일이 존재하지 않습니다: {abs_file_path}")
            
            file_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            if file_inputs:
                file_inputs[0].send_keys(abs_file_path)
                time.sleep(2)
                print(f"    ✓ 파일 업로드")
            
            # 모달 업로드 버튼 클릭
            modal_upload_btns = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'modal')]//button[contains(text(), '업로드')]")
            if not modal_upload_btns:
                modal_upload_btns = self.driver.find_elements(By.XPATH, "//button[contains(text(), '업로드')]")
            
            for btn in modal_upload_btns:
                if btn.is_displayed() and btn.is_enabled():
                    self.driver.execute_script("arguments[0].click();", btn)
                    break
            
            # JavaScript Alert 처리
            try:
                time.sleep(1)
                alert = self.driver.switch_to.alert
                alert.accept()
                time.sleep(2)
                print("    ✓ 업로드 확인")
            except:
                pass
            
            # 모달 닫기
            try:
                close_btns = self.driver.find_elements(By.XPATH, "//button[contains(text(), '닫기')]")
                for btn in close_btns:
                    if btn.is_displayed():
                        self.driver.execute_script("arguments[0].click();", btn)
                        break
                time.sleep(0.5)
            except:
                pass
            
            # 저장
            save_btns = self.driver.find_elements(By.XPATH, "//button[contains(text(), '저장')]")
            for btn in save_btns:
                if btn.is_displayed() and btn.is_enabled():
                    self.driver.execute_script("arguments[0].click();", btn)
                    break
            time.sleep(2)
            
            print("    ✓ 업로드 완료")
            
        except Exception as e:
            print(f"    ✗ 실패: {e}")
            try:
                self.driver.save_screenshot(f"error_{filename}.png")
            except:
                pass
            raise
            
    def close(self):
        """드라이버 종료"""
        if self.driver:
            self.driver.quit()


def upload_promotions_to_beeflow(output_files: list, output_dir: str, email: str, password: str):
    """생성된 엑셀 파일들을 비플로우에 자동 업로드"""
    print("\n" + "=" * 60)
    print("비플로우 자동 업로드 시작")
    print("=" * 60)
    
    uploader = BeeflowUploader(email, password)
    
    try:
        uploader.init_driver()
        uploader.login()
        
        success_count = 0
        for file_path in output_files:
            try:
                filename = os.path.basename(file_path)
                parts = filename.replace('.xlsx', '').split('_')
                
                if len(parts) >= 3:
                    date_range = parts[0]
                    channel_name = parts[2]
                    
                    dates = date_range.split('-')
                    start_date = datetime.strptime('20' + dates[0], '%Y%m%d')
                    end_date = datetime.strptime('20' + dates[1], '%Y%m%d')
                    
                    uploader.upload_promotion(file_path, channel_name, start_date, end_date)
                    success_count += 1
                    
            except Exception as e:
                print(f"  ✗ {filename} 실패: {e}")
                continue
        
        print("\n" + "=" * 60)
        print(f"업로드 완료: {success_count}/{len(output_files)}개 성공")
        print("=" * 60)
        
    finally:
        time.sleep(2)
        uploader.close()


if __name__ == "__main__":
    # 테스트용 코드
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    if os.path.exists(os.path.join(script_dir, "..", "outputs")):
        outputs_dir = os.path.join(script_dir, "..", "outputs")
    elif os.path.exists(os.path.join(script_dir, "outputs")):
        outputs_dir = os.path.join(script_dir, "outputs")
    else:
        outputs_dir = "outputs"
    
    test_file = os.path.join(outputs_dir, "251105-251205_상품_SSG_22.xlsx")
    test_file = os.path.abspath(test_file)
    
    if not os.path.exists(test_file):
        print("오류: 테스트 파일을 찾을 수 없습니다.")
        import sys
        sys.exit(1)
    
    test_files = [test_file]
    
    upload_promotions_to_beeflow(
        output_files=test_files,
        output_dir=outputs_dir,
        email="jsj@brich.co.kr",
        password="young124@"
    )