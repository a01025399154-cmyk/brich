"""
비플로우 상품 조회 모듈
로그인 → 상품조회 → 채널별 상품번호 추출
"""

import requests
from bs4 import BeautifulSoup
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
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.logged_in = False
    
    def login(self):
        """비플로우 로그인"""
        if self.logged_in:
            return True
        
        print(f"  로그인 시도: {self.username}")
        
        # 로그인 페이지 접속
        login_url = "https://b-flow.co.kr/login"
        response = self.session.get(login_url)
        
        # 로그인 폼 데이터
        login_data = {
            'username': self.username,
            'password': self.password
        }
        
        # 로그인 POST 요청
        response = self.session.post(login_url, data=login_data)
        
        if response.status_code == 200:
            self.logged_in = True
            print("  ✓ 로그인 성공")
            return True
        else:
            print(f"  ✗ 로그인 실패: {response.status_code}")
            return False
    
    def query_products(self, product_ids: List[int]) -> Dict[int, Dict[str, str]]:
        """
        상품 조회 및 채널별 상품번호 추출
        
        Args:
            product_ids: 조회할 상품번호 리스트
        
        Returns:
            {
                상품번호: {
                    "지마켓": "채널상품번호",
                    "옥션": "채널상품번호",
                    ...
                }
            }
        """
        if not self.logged_in:
            self.login()
        
        channel_mappings = {}
        total = len(product_ids)
        
        for idx, product_id in enumerate(product_ids, 1):
            print(f"  [{idx}/{total}] 상품 {product_id} 조회 중...")
            
            try:
                mapping = self._query_single_product(product_id)
                channel_mappings[product_id] = mapping
                print(f"    ✓ {len(mapping)}개 채널 발견")
                
                # 요청 간격 (서버 부하 방지)
                time.sleep(0.5)
                
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
        # 상품조회 페이지
        search_url = "https://b-flow.co.kr/products/new"
        
        # 검색 파라미터
        params = {
            'product_id': product_id
        }
        
        response = self.session.get(search_url, params=params)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # HTML 테이블에서 채널 정보 추출
        channel_mapping = self._parse_product_table(soup)
        
        return channel_mapping
    
    def _parse_product_table(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        상품 페이지 HTML에서 채널별 상품번호 추출
        
        비플로우 페이지 구조에 맞춰 파싱
        - 연동정보 섹션에서 채널별 정보 추출
        - 테이블 또는 div 리스트 형식
        
        Args:
            soup: BeautifulSoup 객체
        
        Returns:
            {채널명: 채널상품번호}
        """
        mapping = {}
        
        # 방법 1: 테이블에서 추출
        table = soup.find('table', class_='data-table')
        if table:
            rows = table.find_all('tr')
            for row in rows[1:]:  # 헤더 제외
                cols = row.find_all('td')
                if len(cols) >= 2:
                    channel_name = cols[0].text.strip()
                    channel_id = cols[1].text.strip()
                    
                    if channel_id and channel_id not in ['-', '', 'None', 'null']:
                        # 채널명 정규화
                        channel_name = self._normalize_channel_name(channel_name)
                        mapping[channel_name] = channel_id
            
            if mapping:
                return mapping
        
        # 방법 2: div 리스트에서 추출 (Vue.js 앱인 경우)
        # <div class="channel-item">
        #   <span class="channel-name">SSG</span>
        #   <span class="channel-id">1000614610607</span>
        # </div>
        channel_items = soup.find_all('div', class_='channel-item')
        for item in channel_items:
            name_elem = item.find('span', class_='channel-name')
            id_elem = item.find('span', class_='channel-id')
            
            if name_elem and id_elem:
                channel_name = name_elem.text.strip()
                channel_id = id_elem.text.strip()
                
                if channel_id and channel_id not in ['-', '', 'None', 'null']:
                    channel_name = self._normalize_channel_name(channel_name)
                    mapping[channel_name] = channel_id
        
        return mapping
    
    def _normalize_channel_name(self, name: str) -> str:
        """
        채널명 정규화
        
        비플로우 페이지의 채널명을 discount.xlsx 형식에 맞춤
        
        Args:
            name: 비플로우 채널명
        
        Returns:
            정규화된 채널명
        """
        # 채널명 매핑 테이블
        name_mapping = {
            'gmarket': '지마켓(상품번호)',
            '지마켓': '지마켓(상품번호)',
            'auction': '옥션(상품번호)',
            '옥션': '옥션(상품번호)',
            '11st': '11번가',
            '11번가': '11번가',
            'coupang': '쿠팡',
            '쿠팡': '쿠팡',
            'ssg': 'SSG',
            'gsshop': 'GS샵',
            'gs샵': 'GS샵',
            'lotteon': '롯데ON',
            '롯데on': '롯데ON',
            'cjmall': 'CJ몰',
            'cj몰': 'CJ몰',
            'halfclub': '하프클럽(신규)',
            '하프클럽': '하프클럽(신규)',
            'lotteimall': '롯데아이몰',
            '롯데아이몰': '롯데아이몰',
            '카카오쇼핑하기': '카카오쇼핑하기',
            '카카오스타일': '카카오스타일',
            '퀸잇': '퀸잇',
            '홈앤쇼핑': '홈앤쇼핑'
        }
        
        name_lower = name.lower().strip()
        return name_mapping.get(name_lower, name)


if __name__ == "__main__":
    # 테스트
    client = BeeflowClient("a01025399154@brich.co.kr", "2rlqmadl@!")
    
    # 테스트 상품
    test_products = [986269048]
    
    mappings = client.query_products(test_products)
    
    print("\n결과:")
    for product_id, channels in mappings.items():
        print(f"상품 {product_id}:")
        for ch, ch_id in channels.items():
            print(f"  {ch}: {ch_id}")