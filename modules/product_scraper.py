"""
비플로우 상품 채널 정보 스크래핑 모듈
✅ 원본 코드 기반 - 채널 부분만 CHANNEL_MASTER 연동
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import time
from typing import Dict, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import config


class ProductWebScraper:
    """비플로우 웹페이지에서 상품 채널 정보 스크래핑"""
    
    BASE_URL = "https://b-flow.co.kr/products/new#/"
    
    def __init__(
        self,
        driver: webdriver.Chrome = None,
        batch_size: int = 20,
        headless: bool = True,
    ):
        self.driver = driver
        self.should_close_driver = False
        self.batch_size = batch_size
        self.headless = headless

        # ✅ CHANNEL_MASTER에서 html_name 순서대로 CHANNEL_ORDER 생성
        self.CHANNEL_ORDER = [
            info["html_name"] 
            for standard, info in config.CHANNEL_MASTER.items()
        ]

        if self.driver is None:
            self.should_close_driver = True
            self._init_driver()
        else:
            self.wait = WebDriverWait(self.driver, 20)

    def _init_driver(self):
        """Chrome 드라이버 초기화"""
        options = webdriver.ChromeOptions()

        if self.headless:
            options.add_argument("--headless=new")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")

        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 20)
    
    def login(self, email: str, password: str):
        """비플로우 로그인 (원본 로직 유지)"""
        print("  [웹 스크래퍼] 로그인 중...")
        self.driver.get(self.BASE_URL)
        
        try:
            # 로그인 버튼 클릭
            login_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '로그인')]"))
            )
            self.driver.execute_script("arguments[0].click();", login_btn)
            
            # 이메일 입력
            email_input = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='email']"))
            )
            email_input.send_keys(email)
            
            # 비밀번호 입력
            password_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            password_input.send_keys(password)
            
            # 로그인 실행
            submit_btn = self.driver.find_element(
                By.CSS_SELECTOR, ".modal .login-btn, .v--modal .login-btn"
            )
            self.driver.execute_script("arguments[0].click();", submit_btn)
            
            # 로그인 완료 대기
            time.sleep(3)
            
            # 현재 URL 확인 및 필요시 BASE_URL로 이동
            current_url = self.driver.current_url
            if "products/new" not in current_url:
                print(f"  현재 URL: {current_url}")
                print(f"  → {self.BASE_URL}로 이동")
                self.driver.get(self.BASE_URL)
                time.sleep(2)
            
            # 검색 폼이 로드될 때까지 대기
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".search-form"))
            )
            
            print("  ✓ 로그인 완료")
            print(f"  현재 URL: {self.driver.current_url}")
            
        except Exception as e:
            print(f"  ✗ 로그인 실패: {e}")
            raise
    
    def scrape_products(self, product_ids: List[int]) -> Dict[int, Dict[str, str]]:
        """여러 상품의 채널 정보 스크래핑"""
        results = {}
        total = len(product_ids)
        
        for batch_start in range(0, total, self.batch_size):
            batch_end = min(batch_start + self.batch_size, total)
            batch = product_ids[batch_start:batch_end]
            
            print(f"  [웹 스크래핑] 배치 [{batch_start+1}-{batch_end}/{total}] 처리 중...")
            
            try:
                batch_results = self._scrape_batch(batch)
                results.update(batch_results)
                
                success_count = sum(1 for v in batch_results.values() if v)
                print(f"    ✓ 배치 완료: {success_count}/{len(batch)}개 성공")
                
            except Exception as e:
                print(f"    ✗ 배치 처리 실패: {e}")
                for product_id in batch:
                    results[product_id] = {}
        
        return results
    
    def _scrape_batch(self, product_ids: List[int]) -> Dict[int, Dict[str, str]]:
        """배치 검색 (원본 로직 유지)"""
        try:
            self._select_search_type("상품번호")
            
            search_query = " ".join(str(pid) for pid in product_ids)
            
            search_input = self.driver.find_element(
                By.CSS_SELECTOR, ".br-text-wrapper input[type='text']"
            )
            search_input.clear()
            search_input.send_keys(search_query)
            time.sleep(0.5)
            
            search_btn = self.driver.find_element(
                By.XPATH, "//button[contains(@class, 'br-btn-purple')]//span[text()='검색']"
            )
            self.driver.execute_script("arguments[0].click();", search_btn)
            
            time.sleep(3)
            
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "tbody tr"))
                )
            except Exception:
                print("    ⚠️ 검색 결과 로딩 타임아웃")
                return {pid: {} for pid in product_ids}
            
            return self._parse_table_rows(product_ids)
            
        except Exception as e:
            print(f"    ✗ 배치 검색 실패: {e}")
            return {pid: {} for pid in product_ids}
    
    def _select_search_type(self, search_type: str = "상품번호"):
        """검색 타입 선택 (원본 로직 유지)"""
        try:
            time.sleep(1)
            
            multiselect_wrapper = self.wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    ".form-text-group .multiselect.br-select"
                ))
            )
            
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
                multiselect_wrapper
            )
            time.sleep(1.5)
            
            try:
                multiselect_wrapper.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", multiselect_wrapper)
            
            time.sleep(2)
            
            dropdown = multiselect_wrapper.find_element(By.CSS_SELECTOR, ".multiselect__content-wrapper")
            style = dropdown.get_attribute("style")
            
            if "display: none" in style or "display:none" in style:
                input_elem = multiselect_wrapper.find_element(By.CSS_SELECTOR, "input.multiselect__input")
                try:
                    input_elem.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", input_elem)
                
                time.sleep(2)
                style = dropdown.get_attribute("style")
                
                if "display: none" in style:
                    print(f"    ⚠️ 드롭다운 열기 실패 - 기본값 사용")
                    return
            
            time.sleep(1)
            option_xpath = f"//div[contains(@class, 'form-text-group')]//span[contains(@class, 'multiselect__option')]/span[text()='{search_type}']"
            
            option = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, option_xpath))
            )
            
            try:
                option.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", option)
            
            time.sleep(1.5)
            print(f"    ✓ 검색 타입 '{search_type}' 선택 완료")
            
        except Exception as e:
            print(f"    ⚠️ 검색 타입 선택 실패: {type(e).__name__}")
    
    def _parse_table_rows(self, expected_product_ids: List[int]) -> Dict[int, Dict[str, str]]:
        """테이블 파싱 (원본 로직 유지)"""
        results = {pid: {} for pid in expected_product_ids}
        
        try:
            rows = self.driver.find_elements(By.CSS_SELECTOR, "tbody tr")
            
            if not rows:
                print("    ⚠️ 검색 결과 없음")
                return results
            
            print(f"    발견된 상품 행: {len(rows)}개")
            
            for row_idx, row in enumerate(rows):
                try:
                    product_id, channels = self._parse_single_row(row)
                    
                    if product_id and product_id in expected_product_ids:
                        results[product_id] = channels
                        if channels:
                            print(f"    ✓ 상품 {product_id}: {len(channels)}개 채널")
                        else:
                            print(f"    ○ 상품 {product_id}: 채널 정보 없음")
                    
                except Exception as e:
                    print(f"    ⚠️ 행 {row_idx} 파싱 실패: {e}")
                    continue
            
            return results
            
        except Exception as e:
            print(f"    ✗ 테이블 파싱 실패: {e}")
            return results
    
    def _parse_single_row(self, row) -> tuple:
        """
        테이블 한 행 파싱 - ✅ 채널명만 CHANNEL_MASTER 기반으로 변환
        """
        cells = row.find_elements(By.TAG_NAME, "td")
        
        if len(cells) < 60:
            return None, {}
        
        # 상품번호 추출
        product_id = None
        try:
            text = cells[10].text.strip()
            if text and text.isdigit() and len(text) >= 8:
                product_id = int(text)
        except:
            pass
        
        if not product_id:
            return None, {}
        
        # 채널 정보 추출
        channels = {}
        channel_start_idx = 58
        
        for idx, html_channel_name in enumerate(self.CHANNEL_ORDER):
            cell_index = channel_start_idx + idx
            
            if cell_index >= len(cells):
                break
            
            cell = cells[cell_index]
            
            try:
                if "연동 성공" not in cell.text:
                    continue
                
                lines = cell.text.split('\n')
                
                for line in lines:
                    line = line.strip()
                    clean = line.replace(' ', '').replace('-', '')
                    
                    if clean.isdigit() and len(clean) >= 8:
                        # ✅ HTML 채널명 → 표준 채널명 변환
                        standard_name = config.get_standard_channel_name(html_channel_name)
                        channels[standard_name] = clean
                        break
            except:
                continue
        
        return product_id, channels
    
    def close(self):
        """리소스 정리"""
        if self.should_close_driver and self.driver:
            try:
                self.driver.quit()
            except:
                pass


if __name__ == "__main__":
    scraper = ProductWebScraper(headless=False)
    
    try:
        scraper.login("jsj@brich.co.kr", "young124@")
        
        test_products = [986269048, 2103835824]
        results = scraper.scrape_products(test_products)
        
        print("\n=== 스크래핑 결과 (표준명) ===")
        for product_id, channels in results.items():
            print(f"상품 {product_id}:")
            if channels:
                for ch_name, ch_id in channels.items():
                    print(f"  - {ch_name}: {ch_id}")
            else:
                print("  (채널 정보 없음)")
    
    finally:
        scraper.close()