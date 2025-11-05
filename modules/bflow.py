"""
비플로우 상품 조회 모듈 (Selenium 사용)
로그인 → 상품조회 → 채널별 상품번호 추출
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
from typing import Dict, List

class BeeflowClient:
    def __init__(self, username, password):
        """
        Args:
            username: 비플로우 로그인 ID
            password: 비플로우 비밀번호
        """
        self.username = username
        self.password = password
        self.driver = None
        self.logged_in = False
    
    def _init_driver(self):
        """Chrome 드라이버 초기화"""
        if self.driver:
            return
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # 백그라운드 실행
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
    
    def login(self):
        """비플로우 로그인"""
        if self.logged_in:
            return True
        
        self._init_driver()
        
        print(f"  로그인 시도: {self.username}")
        
        try:
            # 메인 페이지 접속
            self.driver.get('https://b-flow.co.kr/')
            time.sleep(2)
            
            # 로그인 버튼 클릭 (헤더의 로그인 버튼)
            try:
                login_btn = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.login-btn'))
                )
                login_btn.click()
                time.sleep(1)
            except:
                print("  ✗ 로그인 버튼을 찾을 수 없음")
                return False
            
            # 로그인 모달이 나타날 때까지 대기
            try:
                modal = self.wait.until(
                    EC.presence_of_element_located((By.ID, 'login-modal'))
                )
                time.sleep(1)
            except:
                print("  ✗ 로그인 모달이 나타나지 않음")
                return False
            
            # 모달 내부의 이메일/비밀번호 입력
            try:
                email_input = modal.find_element(By.CSS_SELECTOR, 'input[name="email"]')
                password_input = modal.find_element(By.CSS_SELECTOR, 'input[name="password"]')
                
                email_input.clear()
                email_input.send_keys(self.username)
                
                password_input.clear()
                password_input.send_keys(self.password)
                
                time.sleep(1)
                
            except Exception as e:
                print(f"  ✗ 입력 필드 오류: {str(e)}")
                return False
            
            # 로그인 버튼 클릭 (모달 내부)
            try:
                modal_login_btn = modal.find_element(By.CSS_SELECTOR, 'button.login-btn')
                modal_login_btn.click()
                
                # 로그인 완료 대기
                time.sleep(3)
                
                # 로그인 성공 확인 (URL 변경 또는 모달 사라짐)
                try:
                    # 모달이 사라졌는지 확인
                    self.driver.find_element(By.ID, 'login-modal')
                    # 모달이 여전히 있으면 로그인 실패
                    print("  ✗ 로그인 실패 (모달이 사라지지 않음)")
                    return False
                except:
                    # 모달이 없으면 로그인 성공
                    self.logged_in = True
                    print("  ✓ 로그인 성공")
                    return True
                    
            except Exception as e:
                print(f"  ✗ 로그인 버튼 클릭 오류: {str(e)}")
                return False
                
        except Exception as e:
            print(f"  ✗ 로그인 오류: {str(e)}")
            return False
    
    def query_products(self, product_ids: List[int]) -> Dict[int, Dict[str, str]]:
        """
        상품 조회 및 채널별 상품번호 추출
        
        Args:
            product_ids: 조회할 상품번호 리스트
        
        Returns:
            {
                상품번호: {
                    "지마켓(상품번호)": "채널상품번호",
                    "옥션(상품번호)": "채널상품번호",
                    ...
                }
            }
        """
        if not self.logged_in:
            self.login()
        
        if not self.logged_in:
            print("  ✗ 로그인 실패로 조회 불가")
            return {}
        
        channel_mappings = {}
        total = len(product_ids)
        
        for idx, product_id in enumerate(product_ids, 1):
            print(f"  [{idx}/{total}] 상품 {product_id} 조회 중...")
            
            try:
                mapping = self._query_single_product(product_id)
                channel_mappings[product_id] = mapping
                
                if mapping:
                    print(f"    ✓ {len(mapping)}개 채널 발견")
                else:
                    print(f"    ✗ 채널 정보 없음")
                
                # 요청 간격
                time.sleep(1)
                
            except Exception as e:
                print(f"    ✗ 오류: {str(e)}")
                channel_mappings[product_id] = {}
        
        return channel_mappings
    
    def _query_single_product(self, product_id: int) -> Dict[str, str]:
        """
        단일 상품 조회
        
        Args:
            product_id: 상품번호
        
        Returns:
            {채널명: 채널상품번호}
        """
        try:
            # 상품조회 페이지로 이동
            url = "https://b-flow.co.kr/products/new"
            self.driver.get(url)
            time.sleep(2)
            
            # 1. 검색어 타입 선택 (상품번호)
            # 첫 번째 multiselect 찾기 (검색어 타입)
            try:
                search_type_select = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, '.form-text-group .multiselect'))
                )
                search_type_select.click()
                time.sleep(0.5)
                
                # "상품번호" 옵션 선택
                product_num_option = self.driver.find_element(
                    By.XPATH, 
                    "//span[contains(text(), '상품번호')]"
                )
                product_num_option.click()
                time.sleep(0.5)
                
            except Exception as e:
                print(f"    검색 타입 선택 실패: {str(e)}")
                return {}
            
            # 2. 상품번호 입력
            try:
                search_input = self.driver.find_element(
                    By.CSS_SELECTOR, 
                    '.form-text-group input.br-text'
                )
                search_input.clear()
                search_input.send_keys(str(product_id))
                time.sleep(0.5)
                
            except Exception as e:
                print(f"    상품번호 입력 실패: {str(e)}")
                return {}
            
            # 3. 검색 버튼 클릭
            try:
                search_button = self.driver.find_element(
                    By.XPATH,
                    "//button[contains(@class, 'br-btn-purple') and contains(., '검색')]"
                )
                search_button.click()
                time.sleep(3)  # 검색 결과 로딩 대기
                
            except Exception as e:
                print(f"    검색 버튼 클릭 실패: {str(e)}")
                return {}
            
            # 4. 테이블에서 채널 정보 추출
            channel_mapping = self._parse_product_table()
            
            return channel_mapping
            
        except Exception as e:
            print(f"    상품 조회 실패: {str(e)}")
            return {}
    
    def _parse_product_table(self) -> Dict[str, str]:
        """
        상품 테이블에서 채널별 상품번호 추출
        
        HTML 구조:
        - 테이블의 "연동정보" 섹션에 각 채널별로 td가 있음
        - 각 td 안에 채널 상품번호가 있음
        
        Returns:
            {채널명: 채널상품번호}
        """
        mapping = {}
        
        try:
            # 테이블 찾기
            table = self.driver.find_element(By.CSS_SELECTOR, 'table.data-table')
            
            # 헤더에서 채널명 추출
            headers = []
            header_row = table.find_element(By.XPATH, ".//thead/tr[last()]")
            header_cells = header_row.find_elements(By.TAG_NAME, 'th')
            
            # "연동정보" 섹션 시작 위치 찾기
            channel_start_idx = None
            for idx, cell in enumerate(header_cells):
                text = cell.text.strip()
                headers.append(text)
                
                # "SSG"가 연동정보 섹션의 첫 번째
                if text == 'SSG' and channel_start_idx is None:
                    channel_start_idx = idx
            
            if channel_start_idx is None:
                print("    ✗ 연동정보 섹션을 찾을 수 없음")
                return {}
            
            # 데이터 행 찾기
            tbody = table.find_element(By.TAG_NAME, 'tbody')
            data_rows = tbody.find_elements(By.TAG_NAME, 'tr')
            
            if not data_rows:
                print("    ✗ 데이터 행이 없음")
                return {}
            
            # 첫 번째 행의 데이터 추출
            first_row = data_rows[0]
            data_cells = first_row.find_elements(By.TAG_NAME, 'td')
            
            # 연동정보 섹션의 각 셀 파싱
            for idx in range(channel_start_idx, len(data_cells)):
                if idx >= len(headers):
                    break
                    
                channel_name = headers[idx]
                cell = data_cells[idx]
                
                try:
                    # 셀 내부의 div에서 상품번호 추출
                    # 구조: <div><div>1000739965959</div> ...</div>
                    number_div = cell.find_element(By.XPATH, ".//div/div[1]")
                    channel_id = number_div.text.strip()
                    
                    if channel_id and channel_id not in ['-', '', 'None', 'null', '없음']:
                        # 채널명 정규화
                        normalized_name = self._normalize_channel_name(channel_name)
                        if normalized_name:
                            mapping[normalized_name] = channel_id
                            
                except:
                    # 이 채널은 연동되지 않았음
                    continue
            
            return mapping
            
        except Exception as e:
            print(f"    테이블 파싱 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _normalize_channel_name(self, name: str) -> str:
        """
        채널명 정규화
        
        Args:
            name: 비플로우 채널명 (HTML 헤더)
        
        Returns:
            정규화된 채널명 (discount.xlsx 형식)
        """
        if not name:
            return None
        
        name_clean = name.strip()
        
        # 채널명 매핑 (HTML 헤더 → discount.xlsx 컬럼명)
        mapping = {
            'SSG': 'SSG',
            '지마켓': '지마켓(상품번호)',
            '옥션': '옥션(상품번호)',
            '11번가': '11번가',
            '쿠팡': '쿠팡',
            '위메프': '위메프',
            'GS Shop': 'GS샵',
            'GS샵': 'GS샵',
            '롯데ON': '롯데ON',
            'AK몰': 'AK몰',
            'CJ몰': 'CJ몰',
            'Halfclub': '하프클럽(신규)',
            '롯데i몰': '롯데아이몰',
            '네이버스마트스토어': '네이버스마트스토어',
            '지마켓 글로벌': '글로벌 지마켓',
            '옥션 글로벌': '글로벌 옥션',
            '카페24': '카페24',
            '화해': '화해',
            '무신사': '무신사',
            '알리익스프레스': '알리익스프레스',
            '큐텐': '큐텐',
            '쉬인': '쉬인',
            '카카오 선물하기': '카카오 선물하기',
            '카카오 쇼핑하기': '카카오쇼핑하기',
            '글로벌 네이버스마트스토어': '글로벌 네이버스마트스토어',
            '카카오스타일': '카카오스타일',
            '사방넷': '사방넷',
            'Hmall': 'H몰',
            'H몰': 'H몰',
            '네이버플러스스토어': '네이버플러스스토어',
            '퀸잇': '퀸잇',
            '홈앤쇼핑': '홈앤쇼핑',
            '로켓그로스': '로켓그로스',
            '테무': '테무',
        }
        
        # 정확한 매칭
        if name_clean in mapping:
            return mapping[name_clean]
        
        # 부분 매칭 (대소문자 무시)
        name_lower = name_clean.lower()
        for key, value in mapping.items():
            if key.lower() in name_lower or name_lower in key.lower():
                return value
        
        return None
    
    def close(self):
        """브라우저 종료"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def __del__(self):
        """소멸자"""
        self.close()


if __name__ == "__main__":
    # 테스트
    client = BeeflowClient("a01025399154@brich.co.kr", "2rlqmadl@!")
    
    try:
        # 로그인
        if client.login():
            # 테스트 상품
            test_products = [986269048]
            
            mappings = client.query_products(test_products)
            
            print("\n결과:")
            for product_id, channels in mappings.items():
                print(f"상품 {product_id}:")
                for ch, ch_id in channels.items():
                    print(f"  {ch}: {ch_id}")
    finally:
        client.close()