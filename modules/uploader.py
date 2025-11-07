#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
비플로우 웹사이트 자동 업로드 모듈
Selenium을 사용하여 프로모션 관리에 엑셀 파일 업로드
상품 프로모션과 브랜드 프로모션 지원
"""

import os
import time
from datetime import datetime
from typing import List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoAlertPresentException, TimeoutException


class BeeflowUploader:
    """비플로우 프로모션 업로더"""
    
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
        """비플로우 로그인 (불필요한 sleep 최소화)"""
        print("  [로그인] 시작...")
        self.driver.get("https://b-flow.co.kr")
        
        try:
            # 로그인 버튼이 실제로 클릭 가능할 때까지 대기
            login_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '로그인')]"))
            )
            self.driver.execute_script("arguments[0].click();", login_btn)
            
            # 이메일 입력창이 보일 때까지 대기
            email_input = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='email']"))
            )
            email_input.clear()
            email_input.send_keys(self.email)
            
            # 비밀번호 입력
            password_input = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='password']"))
            )
            password_input.clear()
            password_input.send_keys(self.password)
            
            # 로그인 버튼 클릭
            submit_btn = self.driver.find_element(
                By.CSS_SELECTOR, ".modal .login-btn, .v--modal .login-btn"
            )
            self.driver.execute_script("arguments[0].click();", submit_btn)
            
            # 로그인 성공 후, 상단 메뉴(예: '배포관리')가 보일 때까지 대기
            # (필요하면 CSS 셀렉터를 다른 걸로 바꿔도 됨)
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "nav, .br-gnb, .navbar"))
            )
            
            print("  ✓ 로그인 완료")
            
        except Exception as e:
            print(f"  ✗ 로그인 실패: {e}")
            try:
                self.driver.save_screenshot("login_error.png")
                print("  (스크린샷 저장: login_error.png)")
            except Exception:
                pass
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
                "GS Shop": "gsshop",
                "롯데ON": "lotte",
                "CJ몰": "cjmall",
                "하프클럽(신규)": "newhalfclub",
                "Halfclub": "newhalfclub",
                "롯데i몰": "lotteimall",
                "카카오쇼핑하기": "kakaotalkshopping",
                "카카오스타일": "kakaostyle",
                "H몰": "hmall",
                "홈앤쇼핑": "hnsmall",
                "퀸잇": "queenit"
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
            
    def upload_promotion(self, file_path: str, channel_name: str, start_date: datetime, 
                        end_date: datetime, promotion_type: str = "product") -> bool:
        """
        프로모션 업로드

        Args:
            file_path: 엑셀 파일 경로
            channel_name: 채널명
            start_date: 시작일
            end_date: 종료일
            promotion_type: "product" 또는 "brand"

        Returns:
            bool: 업로드 + 저장까지 정상 완료되면 True, 중간에 어떤 에러든 나면 False
        """
        filename = os.path.basename(file_path)
        promotion_name = filename.replace('.xlsx', '').replace('_', ' ')

        print(f"  ▷ 파일: {filename}")
        print(f"    - 채널: {channel_name}")
        print(f"    - 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
        print(f"    - 타입: {promotion_type}")

        # 알럿/모달 텍스트에서 에러 여부를 판별할 키워드
        excel_keywords = ["엑셀 양식", "양식이 맞지", "양식이 올바르지", "엑셀 형식", "엑셀형식"]
        fail_keywords = ["실패", "에러", "오류", "잘못된", "불러올 수 없습니다"]

        try:
            # 페이지 접속 (페이지 로딩은 name_input Wait으로 대체)
            self.driver.get("https://b-flow.co.kr/distribution/promotion/create#/")
            
            # 프로모션명 입력 (실제로 클릭 가능할 때까지 대기)
            name_input = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder*='프로모션']"))
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", name_input)
            time.sleep(0.2)
            try:
                name_input.clear()
            except Exception:
                self.driver.execute_script("arguments[0].value='';", name_input)
            time.sleep(0.1)
            name_input.send_keys(promotion_name)

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

            # 채널 선택 (실패 시 바로 False)
            selected = self.select_channel_from_multiselect(channel_name)
            if not selected:
                print(f"    ✗ 채널 선택 실패: {channel_name}")
                return False

            # 체크박스 클릭
            self._click_checkbox(promotion_type)

            # 엑셀 업로드 버튼 클릭
            upload_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), '엑셀 업로드')]")
            clicked_upload_btn = False
            for btn in upload_buttons:
                if btn.is_displayed() and btn.is_enabled():
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                    time.sleep(0.2)
                    self.driver.execute_script("arguments[0].click();", btn)
                    clicked_upload_btn = True
                    break

            if not clicked_upload_btn:
                print("    ✗ 엑셀 업로드 버튼을 찾을 수 없습니다.")
                return False

            # 파일 업로드
            abs_file_path = self._get_absolute_path(file_path)

            file_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            if file_inputs:
                file_inputs[0].send_keys(abs_file_path)
                time.sleep(0.5)
                print(f"    ✓ 파일 업로드 시도")
            else:
                print("    ✗ 파일 input 요소를 찾을 수 없습니다")
                return False

            # 모달 업로드 버튼 클릭
            time.sleep(0.5)  # 파일 선택 후 UI 업데이트 약간만 대기
            modal_upload_btns = self.driver.find_elements(
                By.XPATH,
                "//div[contains(@class, 'modal')]//button[contains(text(), '업로드')]"
            )
            if not modal_upload_btns:
                modal_upload_btns = self.driver.find_elements(By.XPATH, "//button[contains(text(), '업로드')]")

            clicked_modal_upload = False
            if modal_upload_btns:
                for btn in modal_upload_btns:
                    if btn.is_displayed() and btn.is_enabled():
                        print(f"    ✓ 모달 업로드 버튼 클릭")
                        self.driver.execute_script("arguments[0].click();", btn)
                        clicked_modal_upload = True
                        break

            if not clicked_modal_upload:
                print("    ✗ 모달 업로드 버튼을 찾을 수 없습니다.")
                return False

            # ─────────────────────────────────────────────
            # 1차 알럿: "업로드를 진행하시겠습니까?" (진행 여부)
            # ─────────────────────────────────────────────
            had_any_alert_error = False

            try:
                time.sleep(0.7)
                alert = self.driver.switch_to.alert
                alert_text = alert.text.strip()
                print(f"    [알럿-1] {alert_text}")
                alert.accept()
                time.sleep(0.5)

                if "업로드를 진행하시겠습니까" in alert_text:
                    print("    ✓ 업로드 진행 여부 알럿 처리 (실제 결과는 추가 확인)")
                else:
                    if any(k in alert_text for k in excel_keywords):
                        print(f"    ✗ 엑셀 양식 관련 오류(알럿-1)")
                        return False
                    elif any(k in alert_text for k in fail_keywords):
                        print(f"    ✗ 업로드 관련 오류(알럿-1)")
                        return False
                    else:
                        print("    ✓ 알럿-1 확인 (성공/정보 메시지로 판단)")

            except NoAlertPresentException:
                print("    (1차 알럿 없음)")

            # ─────────────────────────────────────────────
            # 2차 알럿: 실제 결과 알럿 (있을 수도, 없을 수도)
            # ─────────────────────────────────────────────
            if not had_any_alert_error:
                try:
                    time.sleep(0.7)
                    alert2 = self.driver.switch_to.alert
                    alert2_text = alert2.text.strip()
                    print(f"    [알럿-2] {alert2_text}")
                    alert2.accept()
                    time.sleep(0.5)

                    if any(k in alert2_text for k in excel_keywords):
                        print(f"    ✗ 엑셀 양식 관련 오류(알럿-2)")
                        return False
                    elif any(k in alert2_text for k in fail_keywords):
                        print(f"    ✗ 업로드 관련 오류(알럿-2)")
                        return False
                    else:
                        print("    ✓ 알럿-2 확인 (성공/정보 메시지로 판단)")

                except NoAlertPresentException:
                    print("    (2차 알럿 없음, 결과 모달만 있을 수 있음)")

            # ─────────────────────────────────────────────
            # 결과 모달 검사 (페이지 안에 뜨는 팝업 텍스트)
            # ─────────────────────────────────────────────
            time.sleep(0.7)
            modals = self.driver.find_elements(By.CSS_SELECTOR, ".modal, .v--modal-box")
            for modal in modals:
                try:
                    if not modal.is_displayed():
                        continue
                except Exception:
                    continue

                text = modal.text.strip()
                if not text:
                    continue

                lines = text.splitlines()
                preview = "\n      ".join(lines[:5])
                print("    [결과 모달 텍스트 일부]")
                print(f"      {preview}")

                if any(k in text for k in excel_keywords):
                    print(f"    ✗ 엑셀 양식 관련 오류(모달)")
                    return False
                if any(k in text for k in fail_keywords):
                    print(f"    ✗ 업로드 관련 오류(모달)")
                    return False

                # 에러 키워드가 없으면 닫기/확인 버튼 눌러서 정리
                try:
                    close_btns = modal.find_elements(
                        By.XPATH,
                        ".//button[contains(text(), '닫기') or contains(text(), '확인')]"
                    )
                    for btn in close_btns:
                        if btn.is_displayed() and btn.is_enabled():
                            self.driver.execute_script("arguments[0].click();", btn)
                            time.sleep(0.3)
                            break
                except Exception:
                    pass

            # 혹시 남아 있는 '닫기' 버튼 정리
            try:
                close_btns = self.driver.find_elements(By.XPATH, "//button[contains(text(), '닫기')]")
                for btn in close_btns:
                    if btn.is_displayed():
                        self.driver.execute_script("arguments[0].click();", btn)
                        break
                time.sleep(0.3)
            except Exception:
                pass

            # 저장 버튼 클릭 (실제 프로모션 저장 단계)
            save_btns = self.driver.find_elements(By.XPATH, "//button[contains(text(), '저장')]")
            for btn in save_btns:
                if btn.is_displayed() and btn.is_enabled():
                    self.driver.execute_script("arguments[0].click();", btn)
                    break
            time.sleep(0.7)

            # 중복 리스트 모달의 확인 버튼 처리
            try:
                confirm_btns = self.driver.find_elements(By.CSS_SELECTOR, ".br-btn-purple")
                for btn in confirm_btns:
                    if btn.is_displayed() and btn.is_enabled() and "확인" in btn.text:
                        self.driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.5)
                        break
            except Exception:
                pass

            # JavaScript Alert 처리 (중복 리스트 확인 후)
            try:
                time.sleep(0.5)
                alert = self.driver.switch_to.alert
                alert.accept()
                time.sleep(0.3)
            except Exception:
                pass

            print("    ✅ 업로드 + 저장 완료")

            # 다음 업로드를 위해 새 페이지로 이동 (대기도 wait 기반으로)
            self.driver.get("https://b-flow.co.kr/distribution/promotion/create#/")
            # 다음 루프에서 어차피 name_input을 다시 wait 하므로 여기선 추가 sleep 생략

            return True

        except Exception as e:
            print(f"    ✗ 예외 발생: {e}")
            try:
                self.driver.save_screenshot(f"error_{filename}.png")
                print(f"    (스크린샷 저장: error_{filename}.png)")
            except Exception:
                pass
            return False
    
    def _click_checkbox(self, promotion_type: str):
        """체크박스 클릭 (상품 또는 브랜드)"""
        checkbox_label = "상품" if promotion_type == "product" else "브랜드"
        
        checkboxes = []
        try:
            checkboxes = self.driver.find_elements(
                By.XPATH, 
                f"//label[contains(text(), '{checkbox_label}')]/ancestor::div[contains(@class, 'pretty')]//input[@type='checkbox']"
            )
        except:
            pass
        
        if not checkboxes:
            try:
                pretty_divs = self.driver.find_elements(By.CSS_SELECTOR, ".pretty")
                for div in pretty_divs:
                    label = div.find_element(By.TAG_NAME, "label")
                    if checkbox_label in label.get_attribute('textContent'):
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
                print(f"    ✓ {checkbox_label} 체크박스 선택")
    
    def _get_absolute_path(self, file_path: str) -> str:
        """절대 경로 가져오기"""
        if not os.path.isabs(file_path):
            possible_paths = [
                os.path.abspath(file_path),
                os.path.abspath(os.path.join("..", file_path)),
                os.path.abspath(os.path.join(".", file_path.replace("outputs/", "")))
            ]
            
            for test_path in possible_paths:
                if os.path.exists(test_path):
                    return test_path
            
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"파일이 존재하지 않습니다: {file_path}")
        
        return file_path
            
    def close(self):
        """드라이버 종료"""
        if self.driver:
            self.driver.quit()


def upload_promotions(output_files: List[str], output_dir: str, email: str, 
                     password: str):
    """
    생성된 엑셀 파일들을 비플로우에 자동 업로드
    
    Args:
        output_files: 업로드할 파일 경로 리스트
        output_dir: 출력 디렉토리
        email: 비플로우 이메일
        password: 비플로우 비밀번호
    """
    print("\n" + "=" * 60)
    print("비플로우 자동 업로드 시작")
    print("=" * 60)
    
    uploader = BeeflowUploader(email, password)
    
    try:
        uploader.init_driver()
        uploader.login()
        
        total = len(output_files)
        success_count = 0
        processed_count = 0

        for idx, file_path in enumerate(output_files, start=1):
            filename = os.path.basename(file_path)
            print("\n" + "-" * 60)
            print(f"[{idx}/{total}] 파일 처리 시작: {filename}")

            try:
                name_without_ext = filename.replace('.xlsx', '')
                parts = name_without_ext.split('_')
                
                if len(parts) < 3:
                    raise ValueError(f"파일명 형식이 예상과 다릅니다: {filename}")
                
                # 1) 날짜 범위
                date_range = parts[0]  # "251105-251205"
                dates = date_range.split('-')
                if len(dates) != 2:
                    raise ValueError(f"날짜 구간 형식이 잘못되었습니다: {date_range}")
                
                start_date = datetime.strptime('20' + dates[0], '%Y%m%d')
                end_date = datetime.strptime('20' + dates[1], '%Y%m%d')
                
                # 2) 프로모션 타입 (브랜드 / 상품)
                raw_type = parts[1]
                if "브랜드" in raw_type:
                    promotion_type = "brand"
                else:
                    promotion_type = "product"
                
                # 3) 채널명
                channel_name = parts[2]
                
                print(f"  - 유형: {raw_type} → {promotion_type}")
                print(f"  - 채널: {channel_name}")

                ok = uploader.upload_promotion(
                    file_path=file_path,
                    channel_name=channel_name,
                    start_date=start_date,
                    end_date=end_date,
                    promotion_type=promotion_type,
                )

                processed_count += 1

                if ok:
                    success_count += 1
                    print(f"[{idx}/{total}] ✅ 성공: {filename}")
                else:
                    print(f"[{idx}/{total}] ❌ 실패: {filename}")
                    print("\n‼ 첫 업로드 실패 발생 → 이후 작업을 중단합니다.")
                    break
            
            except Exception as e:
                processed_count += 1
                print(f"[{idx}/{total}] ❌ 예외로 실패: {filename}")
                print(f"  - 원인: {e}")
                print("\n‼ 예외 발생으로 인해 이후 작업을 중단합니다.")
                break
        
        print("\n" + "=" * 60)
        print("업로드 작업 요약")
        print("-" * 60)
        print(f"총 대상 파일 수 : {total}")
        print(f"처리한 파일 수 : {processed_count}")
        print(f"성공한 파일 수 : {success_count}")
        print(f"실패한 파일 수 : {processed_count - success_count}")
        if processed_count < total:
            print("※ 중간에 실패가 발생하여 남은 파일은 처리하지 않았습니다.")
        print("=" * 60)
        
    finally:
        time.sleep(1)
        uploader.close()


# ─────────────────────────────────────
# 하드코딩 계정 + 간단 main 진입점
# ─────────────────────────────────────
if __name__ == "__main__":
    from pathlib import Path

    # 🔐 하드코딩된 로그인 정보
    BEEFLOW_EMAIL = "jsj@brich.co.kr"
    BEEFLOW_PASSWORD = "young124@"

    print("=" * 60)
    print("비플로우 업로더 단독 테스트 모드")
    print("=" * 60)

    # 1) 경로 설정
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent
    output_dir = project_root / "outputs"

    print(f"- 프로젝트 루트: {project_root}")
    print(f"- 출력 디렉토리: {output_dir}")

    if not output_dir.exists():
        print(f"✗ 출력 디렉토리가 없습니다: {output_dir}")
        raise SystemExit(1)

    # 2) 엑셀 파일 스캔
    all_files = sorted(output_dir.glob("*.xlsx"))

    if not all_files:
        print("✗ 업로드할 엑셀 파일( *.xlsx )이 없습니다.")
        raise SystemExit(1)

    # 3) 브랜드 / 상품 후보 분리
    brand_files = [f for f in all_files if "브랜드" in f.name]
    product_files = [f for f in all_files if "상품" in f.name]

    print(f"- 브랜드 후보 파일 수 : {len(brand_files)}")
    print(f"- 상품 후보 파일 수  : {len(product_files)}")

    test_brand = brand_files[:2]
    test_product = product_files[:2]

    print("\n브랜드 테스트 대상 (최대 2개):")
    for f in test_brand:
        print(f"  - {f.name}")

    print("\n상품 테스트 대상 (최대 2개):")
    for f in test_product:
        print(f"  - {f.name}")

    # 4) 실제 업로드 실행 (바로 진행, y/n 질문 없음)
    test_files = test_brand + test_product
    if not test_files:
        print("✗ 테스트 대상으로 선택된 파일이 없습니다.")
        raise SystemExit(1)

    print("\n선택된 파일들에 대해 업로드를 바로 진행합니다.\n")

    upload_promotions(
        output_files=[str(p) for p in test_files],
        output_dir=str(output_dir),
        email=BEEFLOW_EMAIL,
        password=BEEFLOW_PASSWORD,
    )
