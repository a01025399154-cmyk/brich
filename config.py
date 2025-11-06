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