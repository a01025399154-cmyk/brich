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
        print("  [로그인] 비플로우 접속 중...")
        self.driver.get("https://b-flow.co.kr")
        time.sleep(2)
        
        try:
            print("  [로그인] 로그인 버튼 클릭...")
            login_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '로그인')]"))
            )
            self.driver.execute_script("arguments[0].click();", login_btn)
            time.sleep(1.5)
            
            print("  [로그인] 이메일 입력...")
            email_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
            )
            email_input.send_keys(self.email)
            time.sleep(0.5)
            
            print("  [로그인] 비밀번호 입력...")
            password_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            password_input.send_keys(self.password)
            time.sleep(0.5)
            
            print("  [로그인] 제출...")
            submit_btn = self.driver.find_element(By.CSS_SELECTOR, ".modal .login-btn, .v--modal .login-btn")
            self.driver.execute_script("arguments[0].click();", submit_btn)
            
            time.sleep(2)
            print("  ✓ 로그인 완료")
            
        except Exception as e:
            print(f"  ✗ 로그인 실패: {e}")
            self.driver.save_screenshot("login_error.png")
            raise
    
    def select_date_in_calendar(self, target_date: datetime, is_end_time: bool = False):
        """
        vdatetime 캘린더에서 날짜 + 시간 선택
        
        Args:
            target_date: 목표 날짜
            is_end_time: True면 23:59, False면 00:00
        """
        try:
            time.sleep(1)
            
            # 1. 연도 확인 - 다를 때만 클릭!
            try:
                year_div = self.driver.find_element(By.CSS_SELECTOR, ".vdatetime-popup__year")
                current_year_text = year_div.text.strip()
                
                if current_year_text and current_year_text.isdigit():
                    current_year = int(current_year_text)
                    
                    if current_year != target_date.year:
                        print(f"      연도 변경: {current_year} → {target_date.year}")
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
                    else:
                        print(f"      연도 일치: {current_year}")
            except Exception as e:
                print(f"      연도 확인 오류: {e}")
            
            # 2. 월 선택 - 화살표로만 이동
            try:
                max_attempts = 24
                for attempt in range(max_attempts):
                    try:
                        month_selector = self.driver.find_element(By.CSS_SELECTOR, ".vdatetime-popup__month-selector__current")
                        month_text = month_selector.text.strip()
                        
                        if not month_text:
                            print(f"      월 로딩 중... ({attempt+1}/{max_attempts})")
                            time.sleep(0.5)
                            continue
                        
                        parts = month_text.split('월')
                        current_month = int(parts[0].strip())
                        current_year_in_month = int(parts[1].strip())
                        
                        if current_year_in_month == target_date.year and current_month == target_date.month:
                            print(f"      월 일치!")
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
                        print(f"      월 이동 오류: {e}")
                        time.sleep(0.5)
                        continue
                        
            except Exception as e:
                print(f"      월 선택 실패: {e}")
            
            # 3. 일 선택
            try:
                date_items = self.driver.find_elements(By.CSS_SELECTOR, 
                    ".vdatetime-popup__date-picker__item:not(.vdatetime-popup__date-picker__item--header):not(.vdatetime-popup__date-picker__item--disabled)")
                
                for item in date_items:
                    if item.text.strip() == str(target_date.day):
                        print(f"      일 선택: {target_date.day}")
                        self.driver.execute_script("arguments[0].click();", item)
                        time.sleep(0.5)
                        break
            except Exception as e:
                print(f"      일 선택 실패: {e}")
            
            # 4. OK 버튼 클릭 (날짜 확인)
            try:
                ok_btn = self.driver.find_element(By.XPATH, "//div[@class='vdatetime-popup__actions__button' and text()='Ok']")
                self.driver.execute_script("arguments[0].click();", ok_btn)
                time.sleep(1)
                print(f"      날짜 OK 클릭")
            except Exception as e:
                print(f"      날짜 OK 버튼 클릭 실패: {e}")
            
            # 5. 시간 선택 (시:분)
            try:
                print(f"      시간 선택 중... ({'23:59' if is_end_time else '00:00'})")
                
                # 시간 선택 화면 대기
                time.sleep(1)
                
                # 시간 리스트 찾기
                time_pickers = self.driver.find_elements(By.CSS_SELECTOR, ".vdatetime-popup__list-picker")
                
                if len(time_pickers) >= 2:
                    # 시(hour) 선택
                    hour_picker = time_pickers[0]
                    target_hour = "23" if is_end_time else "00"
                    
                    hour_items = hour_picker.find_elements(By.CSS_SELECTOR, ".vdatetime-popup__list-picker__item")
                    for item in hour_items:
                        if item.text.strip() == target_hour:
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", item)
                            time.sleep(0.2)
                            self.driver.execute_script("arguments[0].click();", item)
                            print(f"        시: {target_hour}")
                            break
                    
                    time.sleep(0.3)
                    
                    # 분(minute) 선택
                    minute_picker = time_pickers[1]
                    target_minute = "59" if is_end_time else "00"
                    
                    minute_items = minute_picker.find_elements(By.CSS_SELECTOR, ".vdatetime-popup__list-picker__item")
                    for item in minute_items:
                        if item.text.strip() == target_minute:
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", item)
                            time.sleep(0.2)
                            self.driver.execute_script("arguments[0].click();", item)
                            print(f"        분: {target_minute}")
                            break
                    
                    time.sleep(0.3)
                    
            except Exception as e:
                print(f"      시간 선택 실패: {e}")
            
            # 6. OK 버튼 클릭 (시간 확인 및 캘린더 닫기)
            try:
                ok_btn = self.driver.find_element(By.XPATH, "//div[@class='vdatetime-popup__actions__button' and text()='Ok']")
                self.driver.execute_script("arguments[0].click();", ok_btn)
                time.sleep(0.5)
                print(f"      시간 OK 클릭 - 캘린더 닫힘")
            except Exception as e:
                print(f"      시간 OK 버튼 클릭 실패: {e}")
                
        except Exception as e:
            print(f"      캘린더 선택 실패: {e}")
            
    def upload_promotion(self, file_path: str, channel_name: str, start_date: datetime, end_date: datetime):
        """프로모션 업로드"""
        filename = os.path.basename(file_path)
        promotion_name = filename.replace('.xlsx', '').replace('_', ' ')
        
        print(f"\n  [업로드] {filename}")
        print(f"    프로모션명: {promotion_name}")
        print(f"    채널: {channel_name}")
        print(f"    기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
        
        try:
            print("    페이지 접속...")
            self.driver.get("https://b-flow.co.kr/distribution/promotion/create#/")
            time.sleep(2)
            
            print("    프로모션명 입력...")
            name_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='프로모션']"))
            )
            name_input.clear()
            name_input.send_keys(promotion_name)
            time.sleep(0.5)
            
            print("    시작일 설정 (00:00)...")
            date_inputs = self.driver.find_elements(By.CSS_SELECTOR, ".vdatetime input.form-control")
            if date_inputs:
                self.driver.execute_script("arguments[0].click();", date_inputs[0])
                self.select_date_in_calendar(start_date, is_end_time=False)
            
            print("    종료일 설정 (23:59)...")
            date_inputs = self.driver.find_elements(By.CSS_SELECTOR, ".vdatetime input.form-control")
            if len(date_inputs) > 1:
                self.driver.execute_script("arguments[0].click();", date_inputs[1])
                self.select_date_in_calendar(end_date, is_end_time=True)
            
            print("    채널 선택...")
            all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
            for inp in all_inputs:
                placeholder = inp.get_attribute('placeholder') or ''
                if '채널' in placeholder:
                    inp.clear()
                    inp.send_keys(channel_name)
                    time.sleep(0.8)
                    
                    try:
                        option = self.wait.until(
                            EC.element_to_be_clickable((By.XPATH, f"//li[contains(text(), '{channel_name}')]"))
                        )
                        self.driver.execute_script("arguments[0].click();", option)
                        time.sleep(0.5)
                    except:
                        print(f"      경고: 채널 드롭다운 선택 실패")
                    break
            
            print("    상품 버튼 클릭...")
            product_btns = self.driver.find_elements(By.XPATH, "//button[contains(text(), '상품')]")
            for btn in product_btns:
                if btn.is_displayed() and btn.is_enabled():
                    self.driver.execute_script("arguments[0].click();", btn)
                    break
            time.sleep(1.5)
            
            print("    파일 업로드...")
            file_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
            )
            file_input.send_keys(os.path.abspath(file_path))
            time.sleep(2)
            
            print("    업로드 버튼 클릭...")
            upload_btns = self.driver.find_elements(By.XPATH, "//button[contains(text(), '업로드')]")
            for btn in upload_btns:
                if btn.is_displayed() and btn.is_enabled():
                    self.driver.execute_script("arguments[0].click();", btn)
                    break
            time.sleep(2)
            
            try:
                close_btns = self.driver.find_elements(By.XPATH, "//button[contains(text(), '닫기')]")
                for btn in close_btns:
                    if btn.is_displayed():
                        self.driver.execute_script("arguments[0].click();", btn)
                        break
                time.sleep(0.5)
            except:
                pass
            
            print("    저장...")
            save_btns = self.driver.find_elements(By.XPATH, "//button[contains(text(), '저장')]")
            for btn in save_btns:
                if btn.is_displayed() and btn.is_enabled():
                    self.driver.execute_script("arguments[0].click();", btn)
                    break
            time.sleep(2)
            
            print("    ✓ 완료")
            
        except Exception as e:
            print(f"    ✗ 실패: {e}")
            screenshot_path = f"error_{filename}.png"
            try:
                self.driver.save_screenshot(screenshot_path)
                print(f"    스크린샷: {screenshot_path}")
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
    test_files = [
        "outputs/251105-251205_상품_SSG_22.xlsx"
    ]
    
    upload_promotions_to_beeflow(
        output_files=test_files,
        output_dir="outputs",
        email="jsj@brich.co.kr",
        password="young124@"
    )