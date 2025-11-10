"""
웹 스크래핑 기반 상품 채널 정보 추출 모듈
API 실패 시 백업용으로 비플로우 상품 페이지에서 직접 정보 추출
"""

import time
from typing import Dict, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class ProductWebScraper:
    """비플로우 웹페이지에서 상품 채널 정보 스크래핑"""
    
    # 채널 순서 (HTML 테이블 컬럼 순서와 동일)
    CHANNEL_ORDER = [
        "SSG", "지마켓", "옥션", "11번가", "쿠팡", "위메프", "GS Shop", "롯데ON",
        "AK몰", "CJ몰", "Halfclub", "롯데i몰", "네이버스마트스토어", "글로벌 지마켓",
        "글로벌 옥션", "카페24", "화해", "무신사", "알리익스프레스", "큐텐", "쉬인",
        "카카오 선물하기", "카카오 쇼핑하기", "글로벌 네이버스마트스토어", "카카오스타일",
        "사방넷", "Hmall", "네이버플러스스토어", "퀸잇", "홈앤쇼핑", "로켓그로스", "테무"
    ]
    
    def __init__(self, driver: webdriver.Chrome = None):
        """
        Args:
            driver: 이미 로그인된 Selenium WebDriver (선택사항)
                   제공하지 않으면 새로 생성
        """
        self.driver = driver
        self.should_close_driver = False
        
        if self.driver is None:
            self.should_close_driver = True
            self._init_driver()
    
    def _init_driver(self):
        """Chrome 드라이버 초기화"""
        options = webdriver.ChromeOptions()
        # options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 20)  # 타임아웃 증가
    
    def login(self, email: str, password: str):
        """비플로우 로그인"""
        print("  [웹 스크래퍼] 로그인 중...")
        self.driver.get("https://b-flow.co.kr/products/new#/")
        
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
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "nav, .br-gnb, .navbar"))
            )
            
            print("  ✓ 로그인 완료")
            
        except Exception as e:
            print(f"  ✗ 로그인 실패: {e}")
            raise
    
    def scrape_product_channels(self, product_id: int) -> Dict[str, str]:
        """
        상품 페이지에서 채널 정보 스크래핑
        
        Args:
            product_id: BRICH 상품번호
        
        Returns:
            {채널명: 채널상품번호} 딕셔너리
        """
        try:
            # 검색 페이지로 이동 (최초 1회만)
            if self.driver.current_url != "https://b-flow.co.kr/products/new#/":
                self.driver.get("https://b-flow.co.kr/product/management/list")
                time.sleep(2)
            
            # 검색어 입력 필드 찾기 (상품번호 선택 후 입력)
            # 1. 검색 타입 선택 (상품번호)
            try:
                search_type_select = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".multiselect.br-select input"))
                )
                search_type_select.click()
                time.sleep(0.5)
                
                # 상품번호 옵션 선택
                product_num_option = self.driver.find_element(
                    By.XPATH, "//span[text()='상품번호']"
                )
                product_num_option.click()
                time.sleep(0.5)
            except Exception as e:
                print(f"    ⚠️ 검색 타입 선택 실패: {e}")
            
            # 2. 검색어 입력
            search_input = self.driver.find_element(
                By.CSS_SELECTOR, ".br-text-wrapper input[type='text']"
            )
            search_input.clear()
            search_input.send_keys(str(product_id))
            time.sleep(0.5)
            
            # 3. 검색 버튼 클릭
            search_btn = self.driver.find_element(
                By.XPATH, "//button[@class='br-btn br-btn-purple br-btn-medium-form']//span[text()='검색']"
            )
            self.driver.execute_script("arguments[0].click();", search_btn)
            
            # 검색 결과 로딩 대기
            time.sleep(3)
            
            # 테이블 로딩 대기
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "tbody tr"))
                )
            except Exception:
                print("    ⚠️ 테이블 로딩 타임아웃")
            
            # 테이블에서 상품 행 찾기
            rows = self.driver.find_elements(By.CSS_SELECTOR, "tbody tr")
            
            if not rows:
                print(f"    ✗ 상품 {product_id}를 찾을 수 없음")
                return {}
            
            # 첫 번째 행 (검색된 상품)
            row = rows[0]
            
            # 모든 td 요소 가져오기
            cells = row.find_elements(By.TAG_NAME, "td")
            
            print(f"    발견된 컬럼 수: {len(cells)}")
            
            channels = {}
            
            # HTML을 보면 "연동정보" 그룹에서 채널별로 td가 있음
            # SSG부터 시작하는 인덱스를 찾아야 함
            # 일반적으로 56번째 컬럼(0-indexed)부터 시작
            
            for idx, channel_name in enumerate(self.CHANNEL_ORDER):
                # 채널 정보가 시작되는 인덱스: 56 (HTML 구조 기준)
                cell_index = 56 + idx
                
                if cell_index >= len(cells):
                    break
                
                cell = cells[cell_index]
                
                try:
                    # HTML 구조: div 안에 채널 상품번호가 있고, 그 아래 "연동 성공" 라벨이 있음
                    # <div>1000617469196</div>
                    # <span class="br-label-green">연동 성공</span>
                    
                    # 연동 성공 라벨 확인
                    success_labels = cell.find_elements(
                        By.CSS_SELECTOR, 
                        "span.br-label-green"
                    )
                    
                    # "연동 성공" 텍스트가 있는지 확인
                    is_connected = any("연동 성공" in label.text for label in success_labels)
                    
                    if is_connected:
                        # 채널 상품번호 추출 (첫 번째 div의 텍스트)
                        channel_id_divs = cell.find_elements(By.TAG_NAME, "div")
                        
                        for div in channel_id_divs:
                            channel_id = div.text.strip()
                            # 숫자로만 이루어진 ID만 추출
                            if channel_id and channel_id.isdigit():
                                channels[channel_name] = channel_id
                                print(f"    ✓ {channel_name}: {channel_id}")
                                break
                
                except Exception as e:
                    # 개별 채널 파싱 실패는 무시하고 계속
                    continue
            
            return channels
            
        except Exception as e:
            print(f"    ✗ 상품 {product_id} 스크래핑 실패: {e}")
            return {}
    
    def scrape_products(self, product_ids: List[int]) -> Dict[int, Dict[str, str]]:
        """
        여러 상품의 채널 정보 스크래핑
        
        Args:
            product_ids: BRICH 상품번호 리스트
        
        Returns:
            {상품번호: {채널명: 채널상품번호}} 딕셔너리
        """
        results = {}
        total = len(product_ids)
        
        for idx, product_id in enumerate(product_ids, 1):
            print(f"  [웹 스크래핑] [{idx}/{total}] 상품 {product_id} 조회 중...")
            
            try:
                channels = self.scrape_product_channels(product_id)
                results[product_id] = channels
                
                if channels:
                    print(f"    ✓ {len(channels)}개 채널 발견")
                else:
                    print("    ✗ 채널 정보 없음")
                
                time.sleep(1)  # 서버 부하 방지
                
            except Exception as e:
                print(f"    ✗ 오류: {e}")
                results[product_id] = {}
        
        return results
    
    def close(self):
        """드라이버 종료"""
        if self.should_close_driver and self.driver:
            self.driver.quit()


if __name__ == "__main__":
    scraper = ProductWebScraper()
    
    try:
        scraper.login("jsj@brich.co.kr", "young124@")
        
        test_products = [2103835824]
        results = scraper.scrape_products(test_products)
        
        print("\n=== 스크래핑 결과 ===")
        for product_id, channels in results.items():
            print(f"상품 {product_id}:")
            for ch_name, ch_id in channels.items():
                print(f"  - {ch_name}: {ch_id}")
    
    finally:
        scraper.close()