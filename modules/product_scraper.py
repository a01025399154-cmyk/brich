"""
비플로우 상품 채널 정보 스크래핑 모듈 (최종 버전)

주요 기능:
- 비플로우 웹사이트에서 상품의 외부 채널 연동 정보 추출
- 배치 검색으로 여러 상품을 한 번에 처리
- 32개 외부 채널 지원 (지마켓, 옥션, 네이버스마트스토어 등)

사용 방법:
    scraper = ProductWebScraper(headless=False)
    scraper.login(email, password)
    results = scraper.scrape_products([상품번호1, 상품번호2, ...])
    scraper.close()

주의사항:
- 구식 시스템이므로 각 단계마다 충분한 대기시간 필요
- 페이지는 https://b-flow.co.kr/products/new#/ 에서만 작업
"""

import time
from typing import Dict, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class ProductWebScraper:
    """비플로우 웹페이지에서 상품 채널 정보 스크래핑"""
    
    BASE_URL = "https://b-flow.co.kr/products/new#/"
    
    # 채널 순서 (HTML 테이블 컬럼 순서와 동일)
    CHANNEL_ORDER = [
        "SSG", "지마켓", "옥션", "11번가", "쿠팡", "위메프", "GS Shop", "롯데ON",
        "AK몰", "CJ몰", "Halfclub", "롯데i몰", "네이버스마트스토어", "글로벌 지마켓",
        "글로벌 옥션", "카페24", "화해", "무신사", "알리익스프레스", "큐텐", "쉬인",
        "카카오 선물하기", "카카오 쇼핑하기", "글로벌 네이버스마트스토어", "카카오스타일",
        "사방넷", "Hmall", "네이버플러스스토어", "퀸잇", "홈앤쇼핑", "로켓그로스", "테무"
    ]
    
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

        # CHANNEL_ORDER를 인스턴스 속성으로도 보장
        if hasattr(self, "CHANNEL_ORDER"):
            # 클래스 속성이 있으면 그 값을 인스턴스로 복사
            self.CHANNEL_ORDER = type(self).CHANNEL_ORDER
        else:
            # 혹시 모를 상황 대비 (인덴트 깨짐 등)
            self.CHANNEL_ORDER = [
                "SSG", "지마켓", "옥션", "11번가", "쿠팡", "위메프", "GS Shop", "롯데ON",
                "AK몰", "CJ몰", "Halfclub", "롯데i몰", "네이버스마트스토어", "글로벌 지마켓",
                "글로벌 옥션", "카페24", "화해", "무신사", "알리익스프레스", "큐텐", "쉬인",
                "카카오 선물하기", "카카오 쇼핑하기", "글로벌 네이버스마트스토어", "카카오스타일",
                "사방넷", "Hmall", "네이버플러스스토어", "퀸잇", "홈앤쇼핑", "로켓그로스", "테무"
            ]

        if self.driver is None:
            self.should_close_driver = True
            self._init_driver()
        else:
            # 외부에서 전달된 드라이버를 쓰는 경우에도 wait 세팅
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
        """
        여러 상품의 채널 정보 스크래핑 (배치 검색 사용)
        BASE_URL에서 벗어나지 않고 모든 작업 수행
        
        Args:
            product_ids: BRICH 상품번호 리스트
        
        Returns:
            {상품번호: {채널명: 채널상품번호}} 딕셔너리
        """
        results = {}
        total = len(product_ids)
        
        # 배치 단위로 처리
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
                # 개별 처리로 폴백
                for product_id in batch:
                    try:
                        channels = self._scrape_single_search(product_id)
                        results[product_id] = channels
                    except Exception:
                        results[product_id] = {}
        
        return results
    
    def _scrape_batch(self, product_ids: List[int]) -> Dict[int, Dict[str, str]]:
        """
        여러 상품을 한 번에 검색 (BASE_URL에서 동적 검색)
        
        Args:
            product_ids: 상품번호 리스트
        
        Returns:
            {상품번호: {채널명: 채널상품번호}} 딕셔너리
        """
        try:
            # 1. 검색 타입이 '상품번호'인지 확인 및 설정
            self._select_search_type("상품번호")
            
            # 2. 검색어 입력창에 여러 상품번호를 띄어쓰기로 구분하여 입력
            search_query = " ".join(str(pid) for pid in product_ids)
            
            search_input = self.driver.find_element(
                By.CSS_SELECTOR, ".br-text-wrapper input[type='text']"
            )
            search_input.clear()
            search_input.send_keys(search_query)
            time.sleep(0.5)
            
            # 3. 검색 버튼 클릭
            search_btn = self.driver.find_element(
                By.XPATH, "//button[contains(@class, 'br-btn-purple')]//span[text()='검색']"
            )
            self.driver.execute_script("arguments[0].click();", search_btn)
            
            # 4. 검색 결과가 동적으로 렌더링될 때까지 대기
            time.sleep(3)
            
            # 테이블이 업데이트될 때까지 대기
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "tbody tr"))
                )
            except Exception:
                print("    ⚠️ 검색 결과 로딩 타임아웃")
                return {pid: {} for pid in product_ids}
            
            # 5. 현재 페이지(BASE_URL)에서 나타난 테이블 결과 파싱
            print(f"    검색 후 URL: {self.driver.current_url}")
            return self._parse_table_rows(product_ids)
            
        except Exception as e:
            print(f"    ✗ 배치 검색 실패: {e}")
            import traceback
            traceback.print_exc()
            return {pid: {} for pid in product_ids}
    
    def _select_search_type(self, search_type: str = "상품번호"):
        """
        검색 타입 선택 (상품번호, 상품명 등)
        구식 시스템이므로 각 단계마다 충분한 대기시간 필요
        
        Args:
            search_type: 선택할 검색 타입 (기본값: "상품번호")
        """
        try:
            # 1. multiselect 요소 찾기
            time.sleep(1)  # 페이지 안정화 대기
            
            multiselect_wrapper = self.wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    ".form-text-group .multiselect.br-select"
                ))
            )
            
            # 2. 요소를 화면 중앙으로 스크롤
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
                multiselect_wrapper
            )
            time.sleep(1.5)
            
            # 3. wrapper 클릭하여 드롭다운 열기
            try:
                multiselect_wrapper.click()
            except Exception:
                # 일반 클릭 실패 시 JavaScript 클릭
                self.driver.execute_script("arguments[0].click();", multiselect_wrapper)
            
            time.sleep(2)  # 구식 시스템 - 드롭다운 열릴 때까지 대기
            
            # 4. 드롭다운이 열렸는지 확인
            dropdown = multiselect_wrapper.find_element(By.CSS_SELECTOR, ".multiselect__content-wrapper")
            style = dropdown.get_attribute("style")
            
            if "display: none" in style or "display:none" in style:
                # 추가 시도: input 직접 클릭
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
            
            # 5. 옵션 선택
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
            {상품번호: {채널명: 채널상품번호}} 딕셔너리
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
    
    def _parse_single_row(self, row) -> tuple[int, Dict[str, str]]:
        """
        테이블 한 행에서 상품번호와 채널 정보 추출
        
        HTML 구조:
        - 0: 체크박스
        - 1: 관리 버튼
        - 2: 승인 상태
        - 3: 판매 상태
        - 4: 전송상태
        - 5: 딜상품
        - 6: 행사상품 여부
        - 7: 멀티팩 여부
        - 8: 이미지
        - 9: 상품명
        - 10: 상품번호 ← 여기!
        
        Args:
            row: 테이블 행 WebElement
        
        Returns:
            (상품번호, {채널명: 채널상품번호})
        """
        cells = row.find_elements(By.TAG_NAME, "td")
        
        if len(cells) < 40:
            return None, {}
        
        # 상품번호 추출 - 10번째 컬럼 (0-based index)
        product_id = None
        
        try:
            # 10번째 셀의 div 내부 텍스트 확인
            divs = cells[10].find_elements(By.TAG_NAME, "div")
            for div in divs:
                div_text = div.text.strip()
                if div_text and div_text.isdigit() and len(div_text) >= 8:
                    product_id = int(div_text)
                    break
            
            # div에서 못 찾으면 직접 텍스트 확인
            if not product_id:
                text = cells[10].text.strip()
                if text and text.isdigit() and len(text) >= 8:
                    product_id = int(text)
        except (ValueError, IndexError):
            pass
        
        if not product_id:
            return None, {}
        
        # 채널 정보 추출 
        # 관리(8) + 상품(8) + 판매(2) + 가격(4) + 업무(2) + 채널할인(33) = 57
        # 연동정보는 57번째부터 시작
        channels = {}
        channel_start_idx = 57
        
        for idx, channel_name in enumerate(self.CHANNEL_ORDER):
            cell_index = channel_start_idx + idx
            
            if cell_index >= len(cells):
                break
            
            cell = cells[cell_index]
            
            try:
                # 연동 성공 라벨 확인
                success_labels = cell.find_elements(
                    By.CSS_SELECTOR, 
                    "span.br-label-green"
                )
                
                is_connected = any("연동 성공" in label.text for label in success_labels)
                
                if is_connected:
                    # 채널 상품번호 추출
                    channel_id_divs = cell.find_elements(By.TAG_NAME, "div")
                    
                    for div in channel_id_divs:
                        channel_id = div.text.strip()
                        if channel_id and channel_id.isdigit():
                            channels[channel_name] = channel_id
                            break
            
            except Exception:
                continue
        
        return product_id, channels
    
    def _scrape_single_search(self, product_id: int) -> Dict[str, str]:
        """
        단일 상품 검색 (폴백용 - BASE_URL에서 검색)
        
        Args:
            product_id: BRICH 상품번호
        
        Returns:
            {채널명: 채널상품번호} 딕셔너리
        """
        try:
            print(f"    [개별 검색] 상품 {product_id}...")
            
            # 검색 타입 설정
            self._select_search_type("상품번호")
            
            # 검색어 입력
            search_input = self.driver.find_element(
                By.CSS_SELECTOR, ".br-text-wrapper input[type='text']"
            )
            search_input.clear()
            search_input.send_keys(str(product_id))
            time.sleep(0.5)
            
            # 검색 버튼 클릭
            search_btn = self.driver.find_element(
                By.XPATH, "//button[contains(@class, 'br-btn-purple')]//span[text()='검색']"
            )
            self.driver.execute_script("arguments[0].click();", search_btn)
            
            # 결과 대기
            time.sleep(3)
            
            # 테이블에서 첫 번째 행 파싱
            rows = self.driver.find_elements(By.CSS_SELECTOR, "tbody tr")
            
            if not rows:
                return {}
            
            _, channels = self._parse_single_row(rows[0])
            return channels
            
        except Exception as e:
            print(f"    ✗ 개별 검색 실패: {e}")
            return {}
    
    def close(self):
        """드라이버 종료"""
        if self.should_close_driver and self.driver:
            self.driver.quit()


if __name__ == "__main__":
    """
    실제 스크래핑 실행 (추천 배치 크기 사용)

    환경변수:
    - BFLOW_EMAIL: 비플로우 로그인 이메일
    - BFLOW_PASSWORD: 비플로우 로그인 비밀번호
    """
    import os
    import time

    # 로그인 정보
    email = os.getenv("BFLOW_EMAIL", "jsj@brich.co.kr")
    password = os.getenv("BFLOW_PASSWORD", "young124@")

    # product.html 에서 추출한 상품번호 100개
    product_ids = [
        16089817, 103661731, 120020994, 143165393, 159524784, 178079519, 194307326, 216925277, 233415740, 249611675,
        268068218, 281586726, 290474007, 298044805, 316501348, 330033654, 346360149, 364685620, 484781978, 503074681,
        519564504, 535891015, 564933621, 581391188, 599716659, 616042642, 632533105, 646631888, 662991295, 677590253,
        680704091, 695882828, 712373291, 726603146, 759288520, 777745079, 793940502, 867539568, 881802207, 897997758,
        914488093, 932911356, 947379754, 963739529, 977837928, 994196695, 1012751542, 1074447138, 1090805889, 1141916078,
        1164697869, 1181032172, 1199357515, 1212868983, 1229194966, 1247782581, 1263978004, 1280337907, 1312293860, 1319864146,
        1328784195, 1336223537, 1342302831, 1360726990, 1376955309, 1399704332, 1490349927, 1528876036, 1547333091, 1563790658,
        1578052897, 1594247808, 1611986348, 1634604299, 1651094250, 1667289673, 1685746216, 1702204311, 1707642554, 1724001817,
        1742557176, 1747711652, 1764038147, 1782364130, 1864193485, 1912085371, 1928575194, 1942673593, 1959032856, 1977588103,
        1993947494, 2010142405, 2017362401, 2033721664, 2050179375, 2064318094, 2090564880, 2106759935, 2129410654, 2145868349,
    ]

    # 추천 배치 크기
    BATCH_SIZE = 20

    print("\n==============================")
    print(" 비플로우 상품 채널 정보 스크래핑 시작")
    print("==============================")
    print(f"- 대상 상품 수: {len(product_ids)}개")
    print(f"- 배치 크기: {BATCH_SIZE}\n")

    scraper = ProductWebScraper(headless=True, batch_size=BATCH_SIZE)

    try:
        scraper.login(email, password)

        start = time.time()
        results = scraper.scrape_products(product_ids)
        elapsed = time.time() - start

        # 요약
        success = sum(1 for v in results.values() if v)
        print("\n==============================")
        print(" 스크래핑 완료")
        print("==============================")
        print(f"- 채널 정보가 1개 이상 있는 상품 수: {success}/{len(product_ids)}")
        print(f"- 총 소요 시간: {elapsed:.1f}초\n")

        # 상세 로그 (필요하면 주석 해제)
        for pid in product_ids:
            channels = results.get(pid, {})
            print(f"상품 {pid}:")
            if channels:
                for ch_name, ch_id in channels.items():
                    print(f"  - {ch_name}: {ch_id}")
            else:
                print("  (채널 정보 없음)")

    finally:
        scraper.close()
