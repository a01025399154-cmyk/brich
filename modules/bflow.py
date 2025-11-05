"""
비플로우 상품 조회 모듈 (API 전용 버전)

- 내부망 API:
  http://192.168.0.10:10645/api/v1/product/{BRICH상품번호}/channel-product-id

- 응답 예시:
{
  "code": "200",
  "message": "OK",
  "id": "669050054",
  "productId": 3656118,
  "product": {
    "name": "(노컷진81탄) 여성 밴딩 기모 절개 와이드 청바지",
    "channelProductIds": {
      "ssg": "1000748151038",
      "kakaostyle": "167002952",
      "cjmall": "2073484697",
      "lotteimall": "3141447053",
      "gmarket": "4583583341",
      "kakaotalkshopping": "639887874",
      "hnsmall": "69647131",
      "auction": "F389700832"
    }
  }
}

- 반환 형식:
  {
    3656118: {
      "SSG": "1000748151038",
      "카카오스타일": "167002952",
      "CJ몰": "2073484697",
      ...
    },
    ...
  }

※ Selenium / 로그인 전혀 사용하지 않음
"""

import time
from typing import Dict, List, Optional

import requests


class BeeflowClient:
    def __init__(self, api_base_url: str, timeout: int = 5):
        """
        Args:
            api_base_url: 내부 API 베이스 URL
                예) "http://192.168.0.10:10645"
            timeout: API 요청 타임아웃 (초)
        """
        if not api_base_url:
            raise ValueError("api_base_url은 필수입니다.")

        self.api_base_url = api_base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

        # 필요하면 여기서 공통 헤더 추가 가능:
        # self.session.headers.update({"Authorization": "Bearer xxx"})

    # ─────────────────────────────────────────────────────────
    # 외부에서 쓰는 메인 함수
    # ─────────────────────────────────────────────────────────
    def query_products(self, product_ids: List[int]) -> Dict[int, Dict[str, str]]:
        """
        여러 상품(BRICH 상품번호)에 대해 채널별 상품번호 조회

        Args:
            product_ids: BRICH 상품번호 리스트

        Returns:
            {
                상품번호: {
                    "지마켓(상품번호)": "채널상품번호",
                    "옥션(상품번호)": "채널상품번호",
                    ...
                }
            }
        """
        results: Dict[int, Dict[str, str]] = {}
        total = len(product_ids)

        for idx, product_id in enumerate(product_ids, 1):
            print(f"  [API] [{idx}/{total}] 상품 {product_id} 조회 중...")

            try:
                mapping = self._query_single_product_api(product_id)
                results[product_id] = mapping

                if mapping:
                    print(f"    ✓ {len(mapping)}개 채널 발견")
                else:
                    print("    ✗ 채널 정보 없음")

                # 너무 빠른 폭격 방지 (서버 상황에 맞춰 조절)
                time.sleep(0.05)

            except Exception as e:
                print(f"    ✗ 오류: {e}")
                results[product_id] = {}

        return results

    # ─────────────────────────────────────────────────────────
    # 단일 상품 API 조회
    # ─────────────────────────────────────────────────────────
    def _query_single_product_api(self, product_id: int) -> Dict[str, str]:
        """
        내부 API를 사용한 단일 상품 조회

        Args:
            product_id: BRICH 상품번호

        Returns:
            {채널명(엑셀용): 채널상품번호}
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

            normalized = self._normalize_channel_api_key(api_key)
            if normalized:
                mapping[normalized] = ch_id

        return mapping

    # ─────────────────────────────────────────────────────────
    # 채널 키 → 엑셀 컬럼명 매핑
    # ─────────────────────────────────────────────────────────
    def _normalize_channel_api_key(self, key: str) -> Optional[str]:
        """
        API의 channelProductIds 키 → discount.xlsx용 채널명으로 매핑

        Args:
            key: 예) "ssg", "gmarket", "auction", "kakaotalkshopping" ...

        Returns:
            엑셀 컬럼명 (예: "지마켓(상품번호)")
        """
        if not key:
            return None

        k = key.strip().lower()

        # 🔴 실제 API에서 떨어지는 key 보고 한 번 더 정교하게 맞추는 걸 추천
        mapping = {
            "ssg": "SSG",
            "gmarket": "지마켓(상품번호)",
            "auction": "옥션(상품번호)",
            "11st": "11번가",
            "coupang": "쿠팡",
            "wemakeprice": "위메프",
            "gsshop": "GS샵",
            "cjmall": "CJ몰",
            "lotteon": "롯데ON",
            "lotteimall": "롯데아이몰",
            "halfclub": "하프클럽(신규)",
            "naversmartstore": "네이버스마트스토어",
            "globalgmarket": "글로벌 지마켓",
            "globalauction": "글로벌 옥션",
            "cafe24": "카페24",
            "hwahae": "화해",
            "musinsa": "무신사",
            "aliexpress": "알리익스프레스",
            "qoo10": "큐텐",
            "shein": "쉬인",
            "kakaogift": "카카오 선물하기",
            "kakaotalkshopping": "카카오쇼핑하기",
            "kakaostyle": "카카오스타일",
            "globalnaversmartstore": "글로벌 네이버스마트스토어",
            "sabangenet": "사방넷",  # 실제 키 보고 수정
            "hnsmall": "H몰",
            "naverplusstore": "네이버플러스스토어",
            "queenit": "퀸잇",
            "homeandshopping": "홈앤쇼핑",
            "rocketgross": "로켓그로스",
            "temu": "테무",
        }

        return mapping.get(k)


# ─────────────────────────────────────────────────────────
# 단독 실행 테스트
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    # 내부망에서만 동작
    client = BeeflowClient(
        api_base_url="http://192.168.0.10:10645",
        timeout=5,
    )

    # 예시: BRICH 상품번호 리스트
    test_products = [3656118, 986269048]

    mappings = client.query_products(test_products)

    print("\n=== 최종 결과 ===")
    for product_id, channels in mappings.items():
        print(f"\n상품 {product_id}:")
        if not channels:
            print("  (채널 정보 없음)")
            continue

        for ch, ch_id in channels.items():
            print(f"  {ch}: {ch_id}")
