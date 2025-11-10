"""
비플로우 상품 채널 정보 스크래핑 모듈 (리팩토링)
CHANNEL_MASTER 기반 채널 순서 및 변환
"""

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
        """
        Args:
            driver: 이미 로그인된 Selenium WebDriver (선택사항)
            batch_size: 한 번에 검색할 상품 개수 (기본값: 20)
            headless: 브라우저를 헤드리스 모드로 실행할지 여부
        """
        self.driver = driver
        self.should_close_driver = False
        self.batch_size = batch_size
        self.headless = headless

        # CHANNEL_MASTER에서 html_name 순서대로 CHANNEL_ORDER 생성
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
        """
        비플로우 로그인
        BASE_URL에서 로그인하고, 이후 모든 작업도 이 페이지에서 수행
        """
        print("  [웹 스크래퍼] 로그인 중...")
        self.driver.get(self.BASE_URL)
        
        try:
            # 로그인 버튼 클릭
            login_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".navbar-right .btn-login"))
            )
            login_btn.click()
            time.sleep(2)
            
            # 이메일 입력
            email_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input#user_email"))
            )
            email_input.clear()
            email_input.send_keys(email)
            
            # 비밀번호 입력
            pw_input = self.driver.find_element(By.CSS_SELECTOR, "input#user_password")
            pw_input.clear()
            pw_input.send_keys(password)
            
            # 로그인 실행
            submit_btn = self.driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
            submit_btn.click()
            time.sleep(3)
            
            # 로그인 성공 확인
            current_url = self.driver.current_url
            print(f"  ✓ 로그인 완료")
            print(f"  현재 URL: {current_url}")
            
        except Exception as e:
            print(f"  ✗ 로그인 실패: {e}")
            raise
    
    def scrape_products(self, product_ids: List[int]) -> Dict[int, Dict[str, str]]:
        """
        여러 상품의 채널 정보를 배치로 스크래핑
        
        Args:
            product_ids: BRICH 상품번호 리스트
        
        Returns:
            {상품번호: {표준_채널명: 채널상품번호}} 딕셔너리
        """
        results = {pid: {} for pid in product_ids}
        
        # 배치로 나누어 처리
        for i in range(0, len(product_ids), self.batch_size):
            batch = product_ids[i:i + self.batch_size]
            batch_results = self._scrape_batch(batch)
            results.update(batch_results)
        
        return results
    
    def _scrape_batch(self, product_ids: List[int]) -> Dict[int, Dict[str, str]]:
        """
        배치 단위로 상품 검색 및 스크래핑
        
        Args:
            product_ids: 배치 상품번호 리스트
        
        Returns:
            {상품번호: {표준_채널명: 채널상품번호}} 딕셔너리
        """
        print(f"  [웹 스크래핑] 배치 [{product_ids[0]}-{product_ids[-1]}/{len(product_ids)}] 처리 중...")
        
        try:
            # 검색 타입 선택
            self._select_search_type("상품번호")
            
            # 상품번호 입력 (띄어쓰기로 구분)
            search_input = self.driver.find_element(
                By.CSS_SELECTOR, ".br-text-wrapper input[type='text']"
            )
            search_input.clear()
            search_query = " ".join(str(pid) for pid in product_ids)
            search_input.send_keys(search_query)
            search_input.send_keys(Keys.RETURN)
            
            time.sleep(3)
            
            print(f"    검색 후 URL: {self.driver.current_url}")
            
            # 테이블 파싱
            results = self._parse_table_rows(product_ids)
            
            success_count = sum(1 for channels in results.values() if channels)
            print(f"    ✓ 배치 완료: {success_count}/{len(product_ids)}개 성공")
            
            return results
            
        except Exception as e:
            print(f"    ✗ 배치 처리 실패: {e}")
            return {pid: {} for pid in product_ids}
    
    def _select_search_type(self, search_type: str):
        """
        검색 타입 드롭다운 선택 (예: "상품번호")
        
        Args:
            search_type: 검색 타입 (상품명, 상품번호 등)
        """
        try:
            # 드롭다운 클릭
            dropdown = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".form-text-group .multiselect"))
            )
            dropdown.click()
            
            # 옵션 선택
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
            print(f"    → 기본값으로 계속 진행")
    
    def _parse_table_rows(self, expected_product_ids: List[int]) -> Dict[int, Dict[str, str]]:
        """
        동적으로 렌더링된 테이블의 모든 행을 파싱
        
        Args:
            expected_product_ids: 검색한 상품번호 리스트
        
        Returns:
            {상품번호: {표준_채널명: 채널상품번호}} 딕셔너리
        """
        results = {pid: {} for pid in expected_product_ids}
        
        try:
            rows = self.driver.find_elements(By.CSS_SELECTOR, "tbody tr")
            
            if not rows:
                print("    ⚠️ 검색 결과 없음")
                return results
            
            print(f"    발견된 상품 행: {len(rows)}개")
            
            for row_idx, row in enumerate(rows):
                try:
                    # 각 행에서 상품번호와 채널 정보 추출
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
        테이블 한 행에서 상품번호와 채널 정보 추출
        
        Returns:
            (상품번호, {표준_채널명: 채널상품번호})
        """
        cells = row.find_elements(By.TAG_NAME, "td")
        
        if len(cells) < 60:
            return None, {}
        
        # 상품번호 추출 - 10번째 컬럼
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
        channel_start_idx = 57
        
        for idx, html_channel_name in enumerate(self.CHANNEL_ORDER):
            cell_index = channel_start_idx + idx
            
            if cell_index >= len(cells):
                break
            
            cell = cells[cell_index]
            
            try:
                # 연동 성공 확인
                if "연동 성공" not in cell.text:
                    continue
                
                # 셀 텍스트를 줄바꿈으로 분리
                lines = cell.text.split('\n')
                
                # 8자 이상 숫자인 줄 찾기
                for line in lines:
                    line = line.strip()
                    # 순수 숫자만 (공백/하이픈 제거)
                    clean = line.replace(' ', '').replace('-', '')
                    
                    if clean.isdigit() and len(clean) >= 8:
                        # HTML 채널명 → 표준 채널명 변환
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
    # 테스트
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