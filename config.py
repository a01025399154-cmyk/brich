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

# ==================== 통합 채널 매핑 ====================
# 표준 채널명: [API 키, 웹 스크래핑 채널명, 드롭다운 값들...]
# 실제로 존재하는 값만 사용
CHANNEL_NORMALIZATION = {
    # 표준명: [API 키, 스크래핑 HTML 헤더명, 드롭다운명]
    "SSG": ["ssg", "SSG"],
    "지마켓": ["gmarket", "지마켓"],
    "옥션": ["auction", "옥션"],
    "11번가": ["11st", "11번가"],
    "쿠팡": ["coupang", "쿠팡"],
    "위메프": ["wemakeprice", "위메프"],
    "GS Shop": ["gsshop", "GS샵"],  # 웹은 "GS샵", 드롭다운은 "GS샵"
    "롯데ON": ["lotte", "롯데ON"],
    "AK몰": ["akmall", "AK몰"],
    "CJ몰": ["cjmall", "CJ몰"],
    "Halfclub": ["newhalfclub", "Halfclub", "하프클럽", "하프클럽(신규)"],
    "롯데i몰": ["lotteimall", "롯데i몰"],
    "네이버스마트스토어": ["naversmartstore", "네이버스마트스토어"],
    "글로벌 지마켓": ["globalgmarket", "글로벌 지마켓"],
    "글로벌 옥션": ["globalauction", "글로벌 옥션"],
    "카페24": ["cafe24", "카페24"],
    "화해": ["hwahae", "화해"],
    "무신사": ["musinsa", "무신사"],
    "알리익스프레스": ["aliexpress", "알리익스프레스"],
    "큐텐": ["qoo10", "큐텐"],
    "쉬인": ["shein", "쉬인"],
    "카카오 선물하기": ["kakaotalkgift", "카카오 선물하기"],
    "카카오 쇼핑하기": ["kakaotalkshopping", "카카오 쇼핑하기", "카카오쇼핑"],
    "글로벌 네이버스마트스토어": ["globalnaversmartstore", "글로벌 네이버스마트스토어"],
    "카카오스타일": ["kakaostyle", "카카오스타일"],
    "사방넷": ["sabangnet", "사방넷"],
    "Hmall": ["hmall", "Hmall", "H몰"],
    "네이버플러스스토어": ["naverplusstore", "네이버플러스스토어"],
    "퀸잇": ["queenit", "퀸잇"],
    "홈앤쇼핑": ["hnsmall", "홈앤쇼핑"],
    "로켓그로스": ["rocketgrowth", "로켓그로스"],
    "테무": ["temu", "테무"],
}


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
    
    # 대소문자 무시, 공백 제거하여 매칭
    normalized = channel_name.strip().lower().replace(" ", "")
    
    for standard, aliases in CHANNEL_NORMALIZATION.items():
        for alias in aliases:
            if normalized == alias.lower().replace(" ", ""):
                return standard
    
    # 매칭 실패시 원본 반환
    return channel_name


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