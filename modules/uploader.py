#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
비플로우 웹사이트 자동 업로드 모듈 (재시도 로직 강화 버전)
Selenium을 사용하여 프로모션 관리에 엑셀 파일 업로드
상품 프로모션과 브랜드 프로모션 지원
"""

import os
import time
from datetime import datetime
from typing import List, Tuple, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoAlertPresentException, 
    TimeoutException,
    ElementClickInterceptedException,
    StaleElementReferenceException
)


class BeeflowUploader:
    """비플로우 프로모션 업로더"""
    
    # 재시도 설정
    MAX_LOGIN_RETRIES = 3
    MAX_CHANNEL_SELECT_RETRIES = 3
    MAX_FILE_UPLOAD_RETRIES = 2
    MAX_ALERT_WAIT_RETRIES = 3
    
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.driver = None
        self.wait = None
        
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
    
    def _is_calendar_overlay_present(self) -> bool:
        """캘린더 오버레이가 화면을 가리고 있는지 확인"""
        try:
            overlays = self.driver.find_elements(By.CSS_SELECTOR, ".vdatetime-overlay")
            return any(o.is_displayed() for o in overlays)
        except:
            return False
    
    def _close_calendar_overlay(self, max_attempts: int = 3) -> bool:
        """캘린더 오버레이 닫기 (여러 방법 시도)"""
        for attempt in range(max_attempts):
            if not self._is_calendar_overlay_present():
                return True
            
            print(f"      캘린더 오버레이 닫기 시도 {attempt + 1}/{max_attempts}")
            
            # 방법 1: Cancel 버튼
            try:
                cancel_btn = self.driver.find_element(
                    By.XPATH,
                    "//div[@class='vdatetime-popup__actions__button' and text()='Cancel']"
                )
                if cancel_btn.is_displayed():
                    self.driver.execute_script("arguments[0].click();", cancel_btn)
                    time.sleep(0.5)
                    if not self._is_calendar_overlay_present():
                        print("      ✓ Cancel 버튼으로 닫음")
                        return True
            except:
                pass
            
            # 방법 2: 오버레이 직접 클릭
            try:
                overlay = self.driver.find_element(By.CSS_SELECTOR, ".vdatetime-overlay")
                self.driver.execute_script("arguments[0].click();", overlay)
                time.sleep(0.5)
                if not self._is_calendar_overlay_present():
                    print("      ✓ 오버레이 클릭으로 닫음")
                    return True
            except:
                pass
            
            # 방법 3: ESC 키
            try:
                from selenium.webdriver.common.keys import Keys
                self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                time.sleep(0.5)
                if not self._is_calendar_overlay_present():
                    print("      ✓ ESC 키로 닫음")
                    return True
            except:
                pass
        
        print("      ✗ 오버레이 닫기 실패")
        return False
    
    def _is_channel_selected(self, channel_name: str) -> bool:
        """채널이 선택되었는지 확인"""
        try:
            selected_tags = self.driver.find_elements(By.CSS_SELECTOR, ".multiselect__tag span")
            for tag in selected_tags:
                if channel_name.lower() in tag.text.lower():
                    return True
            return False
        except:
            return False
    
    def _wait_for_alert(self, timeout: float = 1.0) -> Optional[str]:
        """알럿 대기 및 텍스트 반환"""
        try:
            time.sleep(timeout)
            alert = self.driver.switch_to.alert
            return alert.text.strip()
        except NoAlertPresentException:
            return None
    
    def login(self) -> bool:
        """비플로우 로그인 (재시도 포함)"""
        for attempt in range(self.MAX_LOGIN_RETRIES):
            try:
                print(f"  [로그인] 시도 {attempt + 1}/{self.MAX_LOGIN_RETRIES}...")
                self.driver.get("https://b-flow.co.kr")
                
                # 로그인 버튼 클릭
                login_btn = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '로그인')]"))
                )
                self.driver.execute_script("arguments[0].click();", login_btn)
                
                # 이메일 입력
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
                
                # 로그인 성공 확인
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "nav, .br-gnb, .navbar"))
                )
                
                print("  ✓ 로그인 완료")
                return True
                
            except Exception as e:
                print(f"  ✗ 로그인 시도 {attempt + 1} 실패: {e}")
                if attempt < self.MAX_LOGIN_RETRIES - 1:
                    time.sleep(2)
                    continue
                else:
                    print("  ✗ 최대 재시도 횟수 초과 - 로그인 실패")
                    return False
        
        return False
    
    def select_date_in_calendar(self, target_date: datetime, is_end_time: bool = False) -> bool:
        """vdatetime 캘린더에서 날짜 + 시간 선택 (재시도 포함)"""
        max_attempts = 2
        
        for attempt in range(max_attempts):
            try:
                if attempt > 0:
                    print(f"      날짜 선택 재시도 {attempt + 1}/{max_attempts}")
                
                time.sleep(1)
                
                # 1. 연도 확인 및 선택
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
                    print(f"      경고: 연도 선택 중 오류 ({e})")
                    pass
                
                # 2. 월 선택
                try:
                    max_month_attempts = 24
                    for month_attempt in range(max_month_attempts):
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
                    print(f"      경고: 월 선택 중 오류 ({e})")
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
                    print(f"      경고: 일 선택 중 오류 ({e})")
                    pass
                
                # 4. OK 버튼 클릭 (날짜 확인)
                try:
                    ok_btn = self.driver.find_element(By.XPATH, "//div[@class='vdatetime-popup__actions__button' and text()='Ok']")
                    self.driver.execute_script("arguments[0].click();", ok_btn)
                    time.sleep(1)
                except Exception as e:
                    print(f"      경고: OK 버튼(날짜) 클릭 중 오류 ({e})")
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
                    print(f"      경고: 시간 선택 중 오류 ({e})")
                    pass
                
                # 6. OK 버튼 클릭 (캘린더 닫기)
                try:
                    ok_btn = self.driver.find_element(By.XPATH, "//div[@class='vdatetime-popup__actions__button' and text()='Ok']")
                    self.driver.execute_script("arguments[0].click();", ok_btn)
                    time.sleep(0.5)
                except Exception as e:
                    print(f"      경고: OK 버튼(시간) 클릭 중 오류 ({e})")
                    pass
                
                return True
                
            except Exception as e:
                print(f"      캘린더 선택 실패 (시도 {attempt + 1}): {e}")
                if attempt < max_attempts - 1:
                    time.sleep(1)
                    continue
                else:
                    return False
        
        return False
    
    def select_channel_from_multiselect(self, channel_name: str) -> bool:
        """multiselect에서 채널 선택 (재시도 포함)"""
        
        for attempt in range(self.MAX_CHANNEL_SELECT_RETRIES):
            try:
                if attempt > 0:
                    print(f"    채널 선택 재시도 {attempt + 1}/{self.MAX_CHANNEL_SELECT_RETRIES}")
                
                # 오버레이 확인 및 닫기
                if self._is_calendar_overlay_present():
                    print("    ⚠️ 캘린더 오버레이 감지 - 닫기 시도")
                    if not self._close_calendar_overlay():
                        print("    ✗ 오버레이 닫기 실패")
                        if attempt < self.MAX_CHANNEL_SELECT_RETRIES - 1:
                            continue
                        return False
                
                # 채널명 매핑
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
                
                # multiselect 찾기 및 클릭
                multiselect = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".multiselect.br-select, .multiselect"))
                )
                
                self.driver.execute_script("arguments[0].scrollIntoView(true);", multiselect)
                time.sleep(0.5)
                
                # JavaScript로 강제 클릭
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
                
                print(f"    ✗ 채널 '{channel_name}' 찾을 수 없음")
                
                if attempt < self.MAX_CHANNEL_SELECT_RETRIES - 1:
                    time.sleep(1)
                    continue
                
                return False
                
            except (TimeoutException, ElementClickInterceptedException, StaleElementReferenceException) as e:
                print(f"    ⚠️ 채널 선택 중 일시적 오류 (시도 {attempt + 1}): {type(e).__name__}")
                if attempt < self.MAX_CHANNEL_SELECT_RETRIES - 1:
                    time.sleep(2)
                    continue
                else:
                    print(f"    ✗ 채널 선택 실패 (최대 재시도 초과)")
                    return False
            except Exception as e:
                print(f"    ✗ 채널 선택 실패: {e}")
                return False
        
        return False
    
    def upload_promotion(self, file_path: str, channel_name: str, start_date: datetime, 
                        end_date: datetime, promotion_type: str = "product") -> bool:
        """
        프로모션 업로드 (재시도 로직 포함)

        Args:
            file_path: 엑셀 파일 경로
            channel_name: 채널명
            start_date: 시작일
            end_date: 종료일
            promotion_type: "product" 또는 "brand"

        Returns:
            bool: 업로드 + 저장까지 정상 완료되면 True, 실패하면 False
        """
        filename = os.path.basename(file_path)
        promotion_name = filename.replace('.xlsx', '').replace('_', ' ')

        print(f"  ▷ 파일: {filename}")
        print(f"    - 채널: {channel_name}")
        print(f"    - 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
        print(f"    - 타입: {promotion_type}")

        # 알럿/모달 텍스트 키워드
        excel_keywords = ["엑셀 양식", "양식이 맞지", "양식이 올바르지", "엑셀 형식", "엑셀형식"]
        fail_keywords = ["실패", "에러", "오류", "잘못된", "불러올 수 없습니다"]

        for main_attempt in range(self.MAX_FILE_UPLOAD_RETRIES):
            try:
                if main_attempt > 0:
                    print(f"\n    ═══ 전체 업로드 재시도 {main_attempt + 1}/{self.MAX_FILE_UPLOAD_RETRIES} ═══")
                    time.sleep(2)
                
                # 페이지 접속
                self.driver.get("https://b-flow.co.kr/distribution/promotion/create#/")
                
                # 프로모션명 입력
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
                    if not self.select_date_in_calendar(start_date, is_end_time=False):
                        print("    ✗ 시작일 설정 실패")
                        if main_attempt < self.MAX_FILE_UPLOAD_RETRIES - 1:
                            continue
                        return False
                    
                    # 오버레이 닫기 확인
                    self._close_calendar_overlay()

                # 종료일 설정
                date_inputs = self.driver.find_elements(By.CSS_SELECTOR, ".vdatetime input.form-control")
                if len(date_inputs) > 1:
                    self.driver.execute_script("arguments[0].click();", date_inputs[1])
                    if not self.select_date_in_calendar(end_date, is_end_time=True):
                        print("    ✗ 종료일 설정 실패")
                        if main_attempt < self.MAX_FILE_UPLOAD_RETRIES - 1:
                            continue
                        return False
                    
                    # 오버레이 닫기 확인
                    self._close_calendar_overlay()

                # 채널 선택
                selected = self.select_channel_from_multiselect(channel_name)
                if not selected:
                    print(f"    ✗ 채널 선택 실패: {channel_name}")
                    if main_attempt < self.MAX_FILE_UPLOAD_RETRIES - 1:
                        continue
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
                    if main_attempt < self.MAX_FILE_UPLOAD_RETRIES - 1:
                        continue
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
                    if main_attempt < self.MAX_FILE_UPLOAD_RETRIES - 1:
                        continue
                    return False

                # 모달 업로드 버튼 클릭
                time.sleep(0.5)
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
                    if main_attempt < self.MAX_FILE_UPLOAD_RETRIES - 1:
                        continue
                    return False

                # 알럿 처리 (재시도 포함)
                had_any_alert_error = False

                # 1차 알럿
                for alert_attempt in range(self.MAX_ALERT_WAIT_RETRIES):
                    alert_text = self._wait_for_alert(timeout=0.7 + alert_attempt * 0.3)
                    if alert_text:
                        print(f"    [알럿-1] {alert_text}")
                        self.driver.switch_to.alert.accept()
                        time.sleep(0.5)

                        if any(k in alert_text for k in excel_keywords):
                            print(f"    ✗ 엑셀 양식 관련 오류(알럿-1)")
                            had_any_alert_error = True
                            break
                        elif any(k in alert_text for k in fail_keywords):
                            print(f"    ✗ 업로드 관련 오류(알럿-1)")
                            had_any_alert_error = True
                            break
                        else:
                            print("    ✓ 알럿-1 확인")
                            break
                    elif alert_attempt == self.MAX_ALERT_WAIT_RETRIES - 1:
                        print("    (1차 알럿 없음)")
                        break

                if had_any_alert_error:
                    if main_attempt < self.MAX_FILE_UPLOAD_RETRIES - 1:
                        continue
                    return False

                # 2차 알럿
                for alert_attempt in range(self.MAX_ALERT_WAIT_RETRIES):
                    alert_text = self._wait_for_alert(timeout=0.7 + alert_attempt * 0.3)
                    if alert_text:
                        print(f"    [알럿-2] {alert_text}")
                        self.driver.switch_to.alert.accept()
                        time.sleep(0.5)

                        if any(k in alert_text for k in excel_keywords):
                            print(f"    ✗ 엑셀 양식 관련 오류(알럿-2)")
                            had_any_alert_error = True
                            break
                        elif any(k in alert_text for k in fail_keywords):
                            print(f"    ✗ 업로드 관련 오류(알럿-2)")
                            had_any_alert_error = True
                            break
                        else:
                            print("    ✓ 알럿-2 확인")
                            break
                    elif alert_attempt == self.MAX_ALERT_WAIT_RETRIES - 1:
                        print("    (2차 알럿 없음)")
                        break

                if had_any_alert_error:
                    if main_attempt < self.MAX_FILE_UPLOAD_RETRIES - 1:
                        continue
                    return False

                # 결과 모달 검사
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
                        if main_attempt < self.MAX_FILE_UPLOAD_RETRIES - 1:
                            had_any_alert_error = True
                            break
                        return False
                    if any(k in text for k in fail_keywords):
                        print(f"    ✗ 업로드 관련 오류(모달)")
                        if main_attempt < self.MAX_FILE_UPLOAD_RETRIES - 1:
                            had_any_alert_error = True
                            break
                        return False

                    # 에러 키워드가 없으면 닫기
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
                
                if had_any_alert_error:
                    continue

                # 남은 닫기 버튼 정리
                try:
                    close_btns = self.driver.find_elements(By.XPATH, "//button[contains(text(), '닫기')]")
                    for btn in close_btns:
                        if btn.is_displayed():
                            self.driver.execute_script("arguments[0].click();", btn)
                            break
                    time.sleep(0.3)
                except Exception:
                    pass

                # 저장 버튼 클릭
                save_btns = self.driver.find_elements(By.XPATH, "//button[contains(text(), '저장')]")
                for btn in save_btns:
                    if btn.is_displayed() and btn.is_enabled():
                        self.driver.execute_script("arguments[0].click();", btn)
                        break
                time.sleep(0.7)

                # 중복 리스트 모달 확인 버튼 처리
                try:
                    confirm_btns = self.driver.find_elements(By.CSS_SELECTOR, ".br-btn-purple")
                    for btn in confirm_btns:
                        if btn.is_displayed() and btn.is_enabled() and "확인" in btn.text:
                            self.driver.execute_script("arguments[0].click();", btn)
                            time.sleep(0.5)
                            break
                except Exception:
                    pass

                # JavaScript Alert 처리
                try:
                    time.sleep(0.5)
                    alert = self.driver.switch_to.alert
                    alert.accept()
                    time.sleep(0.3)
                except Exception:
                    pass

                print("    ✅ 업로드 + 저장 완료")

                # 다음 업로드를 위해 새 페이지로 이동
                self.driver.get("https://b-flow.co.kr/distribution/promotion/create#/")

                return True

            except Exception as e:
                print(f"    ✗ 예외 발생 (시도 {main_attempt + 1}): {e}")
                
                if main_attempt < self.MAX_FILE_UPLOAD_RETRIES - 1:
                    try:
                        self.driver.save_screenshot(f"error_{filename}_attempt{main_attempt + 1}.png")
                        print(f"    (스크린샷 저장: error_{filename}_attempt{main_attempt + 1}.png)")
                    except Exception:
                        pass
                    continue
                else:
                    try:
                        self.driver.save_screenshot(f"error_{filename}_final.png")
                        print(f"    (스크린샷 저장: error_{filename}_final.png)")
                    except Exception:
                        pass
                    return False
        
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
        
        # 로그인 재시도 포함
        if not uploader.login():
            print("\n❌ 로그인 실패로 업로드를 중단합니다.")
            return
        
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
                
                # 날짜 범위
                date_range = parts[0]
                dates = date_range.split('-')
                if len(dates) != 2:
                    raise ValueError(f"날짜 구간 형식이 잘못되었습니다: {date_range}")
                
                start_date = datetime.strptime('20' + dates[0], '%Y%m%d')
                end_date = datetime.strptime('20' + dates[1], '%Y%m%d')
                
                # 프로모션 타입
                raw_type = parts[1]
                if "브랜드" in raw_type:
                    promotion_type = "brand"
                else:
                    promotion_type = "product"
                
                # 채널명
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


if __name__ == "__main__":
    from pathlib import Path

    # 하드코딩된 로그인 정보
    BEEFLOW_EMAIL = "jsj@brich.co.kr"
    BEEFLOW_PASSWORD = "young124@"

    print("=" * 60)
    print("비플로우 업로더 단독 테스트 모드")
    print("=" * 60)

    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent
    output_dir = project_root / "outputs"

    print(f"- 프로젝트 루트: {project_root}")
    print(f"- 출력 디렉토리: {output_dir}")

    if not output_dir.exists():
        print(f"✗ 출력 디렉토리가 없습니다: {output_dir}")
        raise SystemExit(1)

    all_files = sorted(output_dir.glob("*.xlsx"))

    if not all_files:
        print("✗ 업로드할 엑셀 파일( *.xlsx )이 없습니다.")
        raise SystemExit(1)

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