"""
하이브리드 상품 채널 정보 조회 모듈
API 우선, 실패 시 웹 스크래핑으로 백업
"""

from typing import Dict, List
from modules.product_api import ProductAPIClient
from modules.product_scraper import ProductWebScraper


class HybridProductClient:
    """API와 웹 스크래핑을 결합한 상품 정보 조회 클라이언트"""
    
    def __init__(self, api_base_url: str, email: str = None, password: str = None):
        """
        Args:
            api_base_url: 내부 API 베이스 URL
            email: 비플로우 이메일 (웹 스크래핑용, 선택사항)
            password: 비플로우 비밀번호 (웹 스크래핑용, 선택사항)
        """
        self.api_client = ProductAPIClient(api_base_url)
        self.scraper = None
        self.email = email
        self.password = password
    
    def query_products(self, product_ids: List[int]) -> Dict[int, Dict[str, str]]:
        """
        여러 상품에 대해 채널별 상품번호 조회
        1차: API 시도
        2차: API 실패 시 웹 스크래핑
        
        Args:
            product_ids: BRICH 상품번호 리스트
        
        Returns:
            {상품번호: {채널명: 채널상품번호}} 딕셔너리
        """
        print("\n[1단계] API를 통한 상품 조회 시도...")
        api_results = self.api_client.query_products(product_ids)
        
        # API 실패한 상품들 확인
        failed_products = [
            pid for pid, channels in api_results.items() 
            if not channels  # 채널 정보가 없는 경우
        ]
        
        if not failed_products:
            print("✓ 모든 상품 API 조회 성공\n")
            return api_results
        
        print(f"\n⚠️  API 실패 상품: {len(failed_products)}개")
        print("  상품 번호:", failed_products)
        
        # 웹 스크래핑 사용 여부 확인
        if not self.email or not self.password:
            print("  ✗ 웹 스크래핑 인증 정보 없음 - API 결과만 반환")
            return api_results
        
        use_scraper = input("\n웹 스크래핑으로 재시도하시겠습니까? (y/n): ").strip().lower()
        
        if use_scraper not in ['y', 'yes']:
            print("  웹 스크래핑 건너뜀")
            return api_results
        
        # 웹 스크래핑 시도
        print("\n[2단계] 웹 스크래핑을 통한 재조회 시작...")
        
        try:
            if self.scraper is None:
                self.scraper = ProductWebScraper()
                self.scraper.login(self.email, self.password)
            
            scraper_results = self.scraper.scrape_products(failed_products)
            
            # 결과 병합
            for product_id, channels in scraper_results.items():
                if channels:  # 웹 스크래핑으로 정보를 찾은 경우
                    api_results[product_id] = channels
                    print(f"  ✓ 상품 {product_id}: 웹 스크래핑 성공 ({len(channels)}개 채널)")
            
            print("\n✓ 하이브리드 조회 완료\n")
            
        except Exception as e:
            print(f"\n✗ 웹 스크래핑 실패: {e}")
            print("  API 결과만 반환\n")
        
        return api_results
    
    def close(self):
        """리소스 정리"""
        if self.scraper:
            self.scraper.close()


if __name__ == "__main__":
    # 테스트
    import config
    
    client = HybridProductClient(
        api_base_url=config.BEEFLOW_API_BASE_URL,
        email=config.BEEFLOW_EMAIL,
        password=config.BEEFLOW_PASSWORD
    )
    
    try:
        # API가 실패할 수 있는 상품들로 테스트
        test_products = [986269048, 2103835824, 999999999]  # 마지막은 존재하지 않는 상품
        results = client.query_products(test_products)
        
        print("\n=== 최종 조회 결과 ===")
        for product_id, channels in results.items():
            print(f"상품 {product_id}:")
            if channels:
                for ch_name, ch_id in channels.items():
                    print(f"  - {ch_name}: {ch_id}")
            else:
                print("  (채널 정보 없음)")
    
    finally:
        client.close()