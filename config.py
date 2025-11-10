"""
프로모션 자동화 설정
"""

# 구글 시트 설정
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1Ca-AXLDXIpyb_N_9AvI_2fT5g-jMEDYlv233mbkRdVs/edit?gid=737496399#gid=737496399"
GOOGLE_CREDENTIALS_PATH = "inner-sale-979c1e8ed412.json"

# 비플로우 내부 API (상품용)
BEEFLOW_API_BASE_URL = "http://192.168.0.10:10645"

# 비플로우 웹 로그인 정보
BEEFLOW_EMAIL = "jsj@brich.co.kr"
BEEFLOW_PASSWORD = "young124@"

# 출력 디렉토리
OUTPUT_DIR = "outputs"

# ==================== 채널 마스터 (단일 진실 소스) ====================
CHANNEL_MASTER = {
    # 표준명: 채널 메타데이터
    "SSG": {
        "dropdown_name": "SSG",
        "api_key": "ssg",
        "html_name": "SSG",
        "uploader_name": "ssg",
        "enabled_product": True,
        "enabled_brand": True,
    },
    "지마켓": {
        "dropdown_name": "지마켓",
        "api_key": "gmarket",
        "html_name": "지마켓",
        "uploader_name": "gmarket",
        "enabled_product": True,
        "enabled_brand": False,
    },
    "옥션": {
        "dropdown_name": "옥션",
        "api_key": "auction",
        "html_name": "옥션",
        "uploader_name": "auction",
        "enabled_product": True,
        "enabled_brand": False,
    },
    "11번가": {
        "dropdown_name": "11번가",
        "api_key": "11st",
        "html_name": "11번가",
        "uploader_name": "11st",
        "enabled_product": True,
        "enabled_brand": True,
    },
    "쿠팡": {
        "dropdown_name": "쿠팡",
        "api_key": "coupang",
        "html_name": "쿠팡",
        "uploader_name": "coupang",
        "enabled_product": True,
        "enabled_brand": True,
    },
    "위메프": {
        "dropdown_name": "위메프",
        "api_key": "wemakeprice",
        "html_name": "위메프",
        "uploader_name": "wemakeprice",
        "enabled_product": False,
        "enabled_brand": False,
    },
    "GS Shop": {
        "dropdown_name": "GS샵",
        "api_key": "gsshop",
        "html_name": "GS Shop",
        "uploader_name": "gsshop",
        "enabled_product": True,
        "enabled_brand": True,
    },
    "롯데ON": {
        "dropdown_name": "롯데온",
        "api_key": "lotte",
        "html_name": "롯데ON",
        "uploader_name": "lotte",
        "enabled_product": True,
        "enabled_brand": True,
    },
    "AK몰": {
        "dropdown_name": "AK몰",
        "api_key": "akmall",
        "html_name": "AK몰",
        "uploader_name": "akmall",
        "enabled_product": False,
        "enabled_brand": False,
    },
    "CJ몰": {
        "dropdown_name": "CJ몰",
        "api_key": "cjmall",
        "html_name": "CJ몰",
        "uploader_name": "cjmall",
        "enabled_product": True,
        "enabled_brand": True,
    },
    "Halfclub": {
        "dropdown_name": "하프클럽",
        "api_key": "newhalfclub",
        "html_name": "Halfclub",
        "uploader_name": "newhalfclub",
        "enabled_product": True,
        "enabled_brand": True,
    },
    "롯데i몰": {
        "dropdown_name": "롯데i몰",
        "api_key": "lotteimall",
        "html_name": "롯데i몰",
        "uploader_name": "lotteimall",
        "enabled_product": True,
        "enabled_brand": True,
    },
    "네이버스마트스토어": {
        "dropdown_name": "네이버스마트스토어",
        "api_key": "naversmartstore",
        "html_name": "네이버스마트스토어",
        "uploader_name": "naversmartstore",
        "enabled_product": False,
        "enabled_brand": False,
    },
    "글로벌 지마켓": {
        "dropdown_name": "글로벌 지마켓",
        "api_key": "globalgmarket",
        "html_name": "글로벌 지마켓",
        "uploader_name": "globalgmarket",
        "enabled_product": False,
        "enabled_brand": False,
    },
    "글로벌 옥션": {
        "dropdown_name": "글로벌 옥션",
        "api_key": "globalauction",
        "html_name": "글로벌 옥션",
        "uploader_name": "globalauction",
        "enabled_product": False,
        "enabled_brand": False,
    },
    "카페24": {
        "dropdown_name": "카페24",
        "api_key": "cafe24",
        "html_name": "카페24",
        "uploader_name": "cafe24",
        "enabled_product": False,
        "enabled_brand": False,
    },
    "화해": {
        "dropdown_name": "화해",
        "api_key": "hwahae",
        "html_name": "화해",
        "uploader_name": "hwahae",
        "enabled_product": False,
        "enabled_brand": False,
    },
    "무신사": {
        "dropdown_name": "무신사",
        "api_key": "musinsa",
        "html_name": "무신사",
        "uploader_name": "musinsa",
        "enabled_product": False,
        "enabled_brand": False,
    },
    "알리익스프레스": {
        "dropdown_name": "알리익스프레스",
        "api_key": "aliexpress",
        "html_name": "알리익스프레스",
        "uploader_name": "aliexpress",
        "enabled_product": False,
        "enabled_brand": False,
    },
    "큐텐": {
        "dropdown_name": "큐텐",
        "api_key": "qoo10",
        "html_name": "큐텐",
        "uploader_name": "qoo10",
        "enabled_product": False,
        "enabled_brand": False,
    },
    "쉬인": {
        "dropdown_name": "쉬인",
        "api_key": "shein",
        "html_name": "쉬인",
        "uploader_name": "shein",
        "enabled_product": False,
        "enabled_brand": False,
    },
    "카카오 선물하기": {
        "dropdown_name": "카카오 선물하기",
        "api_key": "kakaotalkgift",
        "html_name": "카카오 선물하기",
        "uploader_name": "kakaotalkgift",
        "enabled_product": False,
        "enabled_brand": False,
    },
    "카카오 쇼핑하기": {
        "dropdown_name": "카카오쇼핑",
        "api_key": "kakaotalkshopping",
        "html_name": "카카오 쇼핑하기",
        "uploader_name": "kakaotalkshopping",
        "enabled_product": True,
        "enabled_brand": False,
    },
    "글로벌 네이버스마트스토어": {
        "dropdown_name": "글로벌 네이버스마트스토어",
        "api_key": "globalnaversmartstore",
        "html_name": "글로벌 네이버스마트스토어",
        "uploader_name": "globalnaversmartstore",
        "enabled_product": False,
        "enabled_brand": False,
    },
    "카카오스타일": {
        "dropdown_name": "카카오스타일",
        "api_key": "kakaostyle",
        "html_name": "카카오스타일",
        "uploader_name": "kakaostyle",
        "enabled_product": True,
        "enabled_brand": True,
    },
    "사방넷": {
        "dropdown_name": "사방넷",
        "api_key": "sabangnet",
        "html_name": "사방넷",
        "uploader_name": "sabangnet",
        "enabled_product": False,
        "enabled_brand": False,
    },
    "Hmall": {
        "dropdown_name": "Hmall",
        "api_key": "hmall",
        "html_name": "Hmall",
        "uploader_name": "hmall",
        "enabled_product": False,
        "enabled_brand": False,
    },
    "네이버플러스스토어": {
        "dropdown_name": "네이버플러스스토어",
        "api_key": "naverplusstore",
        "html_name": "네이버플러스스토어",
        "uploader_name": "naverplusstore",
        "enabled_product": False,
        "enabled_brand": False,
    },
    "퀸잇": {
        "dropdown_name": "퀸잇",
        "api_key": "queenit",
        "html_name": "퀸잇",
        "uploader_name": "queenit",
        "enabled_product": True,
        "enabled_brand": True,
    },
    "홈앤쇼핑": {
        "dropdown_name": "홈앤쇼핑",
        "api_key": "hnsmall",
        "html_name": "홈앤쇼핑",
        "uploader_name": "hnsmall",
        "enabled_product": True,
        "enabled_brand": False,
    },
    "로켓그로스": {
        "dropdown_name": "로켓그로스",
        "api_key": "rocketgrowth",
        "html_name": "로켓그로스",
        "uploader_name": "rocketgrowth",
        "enabled_product": False,
        "enabled_brand": False,
    },
    "테무": {
        "dropdown_name": "테무",
        "api_key": "temu",
        "html_name": "테무",
        "uploader_name": "temu",
        "enabled_product": False,
        "enabled_brand": False,
    },
}


# ==================== 헬퍼 함수 ====================

def get_enabled_channels(promo_type: str) -> list:
    """
    프로모션 타입별 활성화된 채널 목록 (표준명)
    
    Args:
        promo_type: "product" 또는 "brand"
    
    Returns:
        활성화된 채널의 표준명 리스트
    """
    key = f"enabled_{promo_type}"
    return [std for std, info in CHANNEL_MASTER.items() if info.get(key, False)]


def get_standard_channel_name(channel_name: str) -> str:
    """
    채널명을 표준 채널명으로 변환
    
    Args:
        channel_name: API 키, 스크래핑 결과, 드롭다운 값 등
    
    Returns:
        표준 채널명 (매칭 실패시 원본 반환)
    """
    if not channel_name:
        return channel_name
    
    # 정규화 (대소문자 무시, 공백 제거)
    normalized = channel_name.strip().lower().replace(" ", "")
    
    # CHANNEL_MASTER에서 검색
    for standard, info in CHANNEL_MASTER.items():
        # 표준명 자체 확인
        if normalized == standard.lower().replace(" ", ""):
            return standard
        
        # 각 필드 확인
        for field in ["dropdown_name", "api_key", "html_name", "uploader_name"]:
            value = info.get(field, "")
            if value and normalized == value.lower().replace(" ", ""):
                return standard
    
    # 매칭 실패시 원본 반환
    return channel_name


# 하위 호환성을 위한 별칭
CHANNEL_NORMALIZATION = {std: [info["api_key"], info["html_name"]] for std, info in CHANNEL_MASTER.items()}


# 프로모션 타입별 컬럼 매핑
PRODUCT_COLUMNS = {
    'K': '시작일',
    'L': '종료일', 
    'M': '상품번호',
    'N': '내부할인타입',
    'O': '내부할인',
    'P': '채널',
    'Q': '추가설명',
    'R': '설정일'
}

BRAND_COLUMNS = {
    'A': '시작일',
    'B': '종료일', 
    'C': '브랜드번호',
    'D': '할인타입',
    'E': '할인',
    'F': '할인2',
    'G': '추가설명',
    'H': '채널',
    'I': '설정일'
}