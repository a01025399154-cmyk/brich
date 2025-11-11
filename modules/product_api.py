"""
상품 채널 조회 API 모듈 (리팩토링)
비플로우 내부 API를 사용하여 상품별 채널 정보 조회
CHANNEL_MASTER 기반으로 채널명 변환
"""

import sys
from pathlib import Path
# 프로젝트 루트를 Python 경로에 추가
sys.path.append(str(Path(__file__).parent.parent))

import time
from typing import Dict, List, Optional
import requests
import config


class ProductAPIClient:
    """상품 채널 정보 조회 클라이언트"""
    
    def __init__(self, api_base_url: str, timeout: int = 5):
        """
        Args:
            api_base_url: 내부 API 베이스 URL (예: "http://192.168.0.10:10645")
            timeout: API 요청 타임아웃 (초)
        """
        if not api_base_url:
            raise ValueError("api_base_url은 필수입니다.")

        self.api_base_url = api_base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def query_products(self, product_ids: List[int]) -> Dict[int, Dict[str, str]]:
        """
        여러 상품에 대해 채널별 상품번호 조회

        Args:
            product_ids: BRICH 상품번호 리스트

        Returns:
            {
                상품번호: {
                    "표준_채널명": "채널상품번호",
                    ...
                }
            }
        """
        results: Dict[int, Dict[str, str]] = {}
        total = len(product_ids)

        for idx, product_id in enumerate(product_ids, 1):
            print(f"  [API] [{idx}/{total}] 상품 {product_id} 조회 중...")

            try:
                mapping = self._query_single_product(product_id)
                results[product_id] = mapping

                if mapping:
                    print(f"    ✓ {len(mapping)}개 채널 발견")
                else:
                    print("    ✗ 채널 정보 없음")

                time.sleep(0.05)

            except Exception as e:
                print(f"    ✗ 오류: {e}")
                results[product_id] = {}

        return results

    def _query_single_product(self, product_id: int) -> Dict[str, str]:
        """
        내부 API를 사용한 단일 상품 조회

        Args:
            product_id: BRICH 상품번호

        Returns:
            {표준_채널명: 채널상품번호}
        """
        url = f"{self.api_base_url}/api/v1/product/{product_id}/channel-product-id"

        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"    ✗ API 요청 실패: {e}")
            return {}

        try:
            data = resp.json()
        except ValueError:
            print("    ✗ API 응답 JSON 파싱 실패")
            return {}

        if str(data.get("code")) != "200":
            print(
                f"    ✗ API 응답 코드 비정상: code={data.get('code')} / message={data.get('message')}"
            )
            return {}

        product = data.get("product") or {}
        channel_ids = product.get("channelProductIds") or {}

        mapping: Dict[str, str] = {}

        for api_key, channel_id in channel_ids.items():
            ch_id = (channel_id or "").strip()
            if not ch_id or ch_id in ["-", "None", "null", "없음"]:
                continue

            # API 키를 표준 채널명으로 변환 (CHANNEL_MASTER 사용)
            standard_name = self._api_key_to_standard(api_key)
            if standard_name:
                mapping[standard_name] = ch_id

        return mapping

    def _api_key_to_standard(self, api_key: str) -> Optional[str]:
        """
        API 채널 키 → 표준 채널명 변환 (CHANNEL_MASTER 기반)
        
        Args:
            api_key: API 채널 키 (예: "ssg", "gmarket", "coupang")
        
        Returns:
            표준 채널명 (매칭 실패시 None)
        """
        if not api_key:
            return None

        # CHANNEL_MASTER에서 api_key로 검색
        for standard, info in config.CHANNEL_MASTER.items():
            if api_key.strip().lower() == info["api_key"].lower():
                return standard
        
        return None


if __name__ == "__main__":
    # 테스트
    client = ProductAPIClient("http://192.168.0.10:10645")
    
    test_products = [986269048]
    results = client.query_products(test_products)
    
    print("\n=== 조회 결과 ===")
    for product_id, channels in results.items():
        print(f"상품 {product_id}:")
        for ch_name, ch_id in channels.items():
            print(f"  - {ch_name}: {ch_id}")