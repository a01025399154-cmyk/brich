"""
구글 시트 읽기 모듈
discount.xlsx의 K~R열 데이터를 읽어옴
"""

import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# K~R열 컬럼명 매핑
COLUMN_MAPPING = {
    'K': '시작일',
    'L': '종료일', 
    'M': '상품번호',
    'N': '내부할인타입',
    'O': '내부할인',
    'P': '채널',
    'Q': '추가설명',
    'R': '설정일'
}

def read_discount_sheet(sheet_url, credentials_path):
    """
    구글 시트에서 K~R열 데이터 읽기
    
    Args:
        sheet_url: 구글 시트 URL
        credentials_path: 서비스 계정 JSON 파일 경로
    
    Returns:
        DataFrame: K~R열 데이터
    """
    # 인증
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
    client = gspread.authorize(creds)
    
    # 시트 열기
    sheet_id = sheet_url.split('/d/')[1].split('/')[0]
    spreadsheet = client.open_by_key(sheet_id)
    
    # gid로 특정 시트 탭 가져오기
    # gid=737496399 -> [11월]내부 할인[삭제금지]
    try:
        # URL에서 gid 추출
        if 'gid=' in sheet_url:
            gid = sheet_url.split('gid=')[1].split('&')[0].split('#')[0]
            worksheet = spreadsheet.get_worksheet_by_id(int(gid))
        else:
            # gid가 없으면 첫 번째 시트
            worksheet = spreadsheet.get_worksheet(0)
    except:
        # 시트명으로 직접 찾기
        worksheet = spreadsheet.worksheet('[11월]내부 할인[삭제금지]')
    
    # K~R열 데이터 가져오기 (K=11, R=18)
    # 3행부터 읽기 (1행: 대분류, 2행: 설명, 3행: 필드명)
    data = worksheet.get('K4:R')  # 4행부터 끝까지
    
    # DataFrame 생성
    df = pd.DataFrame(data, columns=list(COLUMN_MAPPING.values()))
    
    # 데이터 전처리
    # 빈 행 제거
    df = df[df['상품번호'].notna() & (df['상품번호'] != '')]
    
    # 데이터 타입 변환
    df['상품번호'] = pd.to_numeric(df['상품번호'], errors='coerce')
    df['내부할인'] = pd.to_numeric(df['내부할인'], errors='coerce')
    
    # 날짜 변환
    df['시작일'] = pd.to_datetime(df['시작일'], errors='coerce')
    df['종료일'] = pd.to_datetime(df['종료일'], errors='coerce')
    df['설정일'] = pd.to_datetime(df['설정일'], errors='coerce')
    
    # NaN 제거
    df = df[df['상품번호'].notna()]
    
    return df


if __name__ == "__main__":
    # 테스트
    df = read_discount_sheet(
        "https://docs.google.com/spreadsheets/d/1Ca-AXLDXIpyb_N_9AvI_2fT5g-jMEDYlv233mbkRdVs/edit",
        "/mnt/user-data/uploads/inner-sale-979c1e8ed412.json"
    )
    print(f"읽은 행 수: {len(df)}")
    print("\n첫 5행:")
    print(df.head())
    print("\n컬럼 정보:")
    print(df.dtypes)