"""
구글 시트 읽기 모듈 (개선 버전)
discount.xlsx의 K~R열 데이터를 읽어옴
시트 선택 인터랙티브 기능 추가
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


def get_sheet_list(sheet_url, credentials_path):
    """
    구글 스프레드시트의 모든 시트 목록 가져오기
    
    Args:
        sheet_url: 구글 시트 URL
        credentials_path: 서비스 계정 JSON 파일 경로
    
    Returns:
        list: 시트 이름 리스트
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
    
    # 모든 시트 이름 가져오기
    worksheets = spreadsheet.worksheets()
    sheet_names = [ws.title for ws in worksheets]
    
    return sheet_names


def select_sheet_interactive(sheet_names):
    """
    사용자가 시트를 선택할 수 있도록 인터랙티브 메뉴 제공
    
    Args:
        sheet_names: 시트 이름 리스트
    
    Returns:
        str: 선택된 시트 이름
    """
    print("\n" + "=" * 60)
    print("📋 사용 가능한 시트 목록")
    print("=" * 60)
    
    for idx, name in enumerate(sheet_names, 1):
        print(f"{idx}. {name}")
    
    print("=" * 60)
    
    while True:
        try:
            choice = input(f"\n시트 번호를 선택하세요 (1-{len(sheet_names)}): ").strip()
            
            if not choice:
                print("❌ 번호를 입력해주세요.")
                continue
            
            choice_num = int(choice)
            
            if 1 <= choice_num <= len(sheet_names):
                selected_sheet = sheet_names[choice_num - 1]
                print(f"\n✅ '{selected_sheet}' 시트를 선택했습니다.\n")
                return selected_sheet
            else:
                print(f"❌ 1부터 {len(sheet_names)} 사이의 숫자를 입력해주세요.")
                
        except ValueError:
            print("❌ 올바른 숫자를 입력해주세요.")
        except KeyboardInterrupt:
            print("\n\n❌ 취소되었습니다.")
            exit(1)


def read_discount_sheet(sheet_url, credentials_path, sheet_name=None, interactive=True):
    """
    구글 시트에서 K~R열 데이터 읽기
    
    Args:
        sheet_url: 구글 시트 URL
        credentials_path: 서비스 계정 JSON 파일 경로
        sheet_name: 읽을 시트 이름 (None이면 자동 선택)
        interactive: True면 사용자에게 시트 선택을 물어봄
    
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
    
    # 시트 선택 로직
    if sheet_name is None:
        # gid가 URL에 있으면 해당 시트 사용
        if 'gid=' in sheet_url:
            try:
                gid = sheet_url.split('gid=')[1].split('&')[0].split('#')[0]
                worksheet = spreadsheet.get_worksheet_by_id(int(gid))
                print(f"✓ URL의 gid로 시트 선택: {worksheet.title}")
            except:
                # gid로 찾기 실패하면 인터랙티브 선택
                if interactive:
                    sheet_names = [ws.title for ws in spreadsheet.worksheets()]
                    selected_name = select_sheet_interactive(sheet_names)
                    worksheet = spreadsheet.worksheet(selected_name)
                else:
                    # 기본값: 첫 번째 시트
                    worksheet = spreadsheet.get_worksheet(0)
                    print(f"✓ 첫 번째 시트 사용: {worksheet.title}")
        else:
            # URL에 gid가 없으면 인터랙티브 선택
            if interactive:
                sheet_names = [ws.title for ws in spreadsheet.worksheets()]
                selected_name = select_sheet_interactive(sheet_names)
                worksheet = spreadsheet.worksheet(selected_name)
            else:
                # 기본값: 첫 번째 시트
                worksheet = spreadsheet.get_worksheet(0)
                print(f"✓ 첫 번째 시트 사용: {worksheet.title}")
    else:
        # 시트 이름이 명시적으로 주어진 경우
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            print(f"✓ 지정된 시트 사용: {sheet_name}")
        except:
            print(f"⚠️  시트 '{sheet_name}'을 찾을 수 없습니다.")
            if interactive:
                sheet_names = [ws.title for ws in spreadsheet.worksheets()]
                selected_name = select_sheet_interactive(sheet_names)
                worksheet = spreadsheet.worksheet(selected_name)
            else:
                raise ValueError(f"시트 '{sheet_name}'을 찾을 수 없습니다.")
    
    # K~R열 데이터 가져오기 (4행부터 끝까지)
    data = worksheet.get('K4:R')
    
    # DataFrame 생성
    df = pd.DataFrame(data, columns=list(COLUMN_MAPPING.values()))
    
    # 데이터 전처리
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
    SHEET_URL = "https://docs.google.com/spreadsheets/d/1Ca-AXLDXIpyb_N_9AvI_2fT5g-jMEDYlv233mbkRdVs/edit?gid=737496399#gid=737496399"
    CREDENTIALS_PATH = "/Users/brich/Desktop/brich/inner-sale-979c1e8ed412.json"
    
    print("시트 목록 가져오기 테스트:")
    sheet_names = get_sheet_list(SHEET_URL, CREDENTIALS_PATH)
    print(f"총 {len(sheet_names)}개 시트 발견")
    
    print("\n인터랙티브 시트 선택 테스트:")
    df = read_discount_sheet(SHEET_URL, CREDENTIALS_PATH, interactive=True)
    print(f"\n읽은 데이터: {len(df)}개 행")
    print(df.head())