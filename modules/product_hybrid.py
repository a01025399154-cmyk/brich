"""
하이브리드 상품 채널 정보 조회 모듈 (리팩토링)
API 우선, 실패 시 웹 스크래핑으로 백업
CHANNEL_MASTER 기반 채널명 정규화
"""

from typing import Dict, List
from modules.product_api import ProductAPIClient
from modules.product_scraper import ProductWebScraper
import config


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
    
    def _normalize_channel_dict(self, channels: Dict[str, str]) -> Dict[str, str]:
        """
        채널 딕셔너리의 키를 표준 채널명으로 정규화
        (이미 product_api와 product_scraper에서 정규화되므로 검증용)
        
        Args:
            channels: {채널명: 채널상품번호}
        
        Returns:
            {표준_채널명: 채널상품번호}
        """
        normalized = {}
        for ch_name, ch_id in channels.items():
            standard_name = config.get_standard_channel_name(ch_name)
            normalized[standard_name] = ch_id
        
        return normalized
    
    def query_products(self, product_ids: List[int]) -> Dict[int, Dict[str, str]]:
        """
        여러 상품에 대해 채널별 상품번호 조회
        1차: API 시도
        2차: API 실패 시 웹 스크래핑 (자동)
        
        모든 채널명을 표준명으로 정규화하여 반환
        (product_api와 product_scraper에서 이미 정규화 수행)
        
        Args:
            product_ids: BRICH 상품번호 리스트
        
        Returns:
            {상품번호: {표준_채널명: 채널상품번호}} 딕셔너리
        """
        print("\n[1단계] API를 통한 상품 조회 시도...")
        api_results = self.api_client.query_products(product_ids)
        
        # API 결과는 이미 표준명으로 반환됨 (product_api에서 처리)
        # 추가 정규화는 검증 목적으로만 수행
        api_results = {
            pid: self._normalize_channel_dict(channels)
            for pid, channels in api_results.items()
        }
        
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
        
        # 웹 스크래핑 인증 정보 없으면 여기까지만
        if not self.email or not self.password:
            print("  ✗ 웹 스크래핑 인증 정보 없음 - API 결과만 반환")
            return api_results
        
        print("\n[2단계] 웹 스크래핑을 통한 재조회 자동 수행...")

        try:
            if self.scraper is None:
                self.scraper = ProductWebScraper(
                    batch_size=20,
                    headless=True,
                )
                self.scraper.login(self.email, self.password)
            
            scraper_results = self.scraper.scrape_products(failed_products)
            
            # 스크래핑 결과도 이미 표준명으로 반환됨 (product_scraper에서 처리)
            # 추가 정규화는 검증 목적으로만 수행
            scraper_results = {
                pid: self._normalize_channel_dict(channels)
                for pid, channels in scraper_results.items()
            }
            
            # 결과 병합
            for product_id, channels in scraper_results.items():
                if channels:  # 웹 스크래핑으로 정보를 찾은 경우
                    api_results[product_id] = channels
                    print(f"  ✓ 상품 {product_id}: 웹 스크래핑 성공 ({len(channels)}개 채널)")
                else:
                    print(f"  ○ 상품 {product_id}: 웹 스크래핑에서도 채널 정보 없음")
            
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
        
        print("\n=== 최종 조회 결과 (정규화됨) ===")
        for product_id, channels in results.items():
            print(f"상품 {product_id}:")
            if channels:
                for ch_name, ch_id in channels.items():
                    print(f"  - {ch_name}: {ch_id}")
            else:
                print("  (채널 정보 없음)")
    
    finally:
        client.close()