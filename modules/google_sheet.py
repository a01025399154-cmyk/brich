"""
구글 시트 읽기 모듈 (개선 버전)
discount.xlsx의 K~R열 데이터를 읽어옴
시트 선택 인터랙티브 기능 추가
"""

import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import numpy as np
from datetime import datetime

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


def clean_date_value(val):
    """
    날짜 컬럼의 값을 정리
    빈 문자열, 공백, "-", "None" 등을 NaN으로 변환
    """
    if pd.isna(val):
        return np.nan
    
    if not isinstance(val, str):
        return val
    
    # 문자열인 경우 정리
    val_stripped = val.strip()
    
    # 빈 값으로 간주할 패턴들
    if val_stripped in ['', '-', 'None', 'null', 'N/A', 'NA']:
        return np.nan
    
    return val_stripped


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
        if interactive:
            # 인터랙티브 모드: 항상 사용자가 선택
            sheet_names = [ws.title for ws in spreadsheet.worksheets()]
            selected_name = select_sheet_interactive(sheet_names)
            worksheet = spreadsheet.worksheet(selected_name)
        else:
            # 자동 모드: gid 또는 첫 번째 시트 사용
            if 'gid=' in sheet_url:
                try:
                    gid = sheet_url.split('gid=')[1].split('&')[0].split('#')[0]
                    worksheet = spreadsheet.get_worksheet_by_id(int(gid))
                    print(f"✓ URL의 gid로 시트 선택: {worksheet.title}")
                except:
                    worksheet = spreadsheet.get_worksheet(0)
                    print(f"✓ 첫 번째 시트 사용: {worksheet.title}")
            else:
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
    
    # 빈 문자열을 NaN으로 변환 (모든 컬럼에 대해)
    df = df.replace('', np.nan)
    df = df.replace(' ', np.nan)
    df = df.replace('-', np.nan)
    
    # 데이터 전처리 - 필수 컬럼들이 모두 비어있지 않은 행만 선택
    # 상품번호와 시작일이 모두 있는 행만 유효한 데이터로 간주
    df = df[
        df['상품번호'].notna() & 
        df['시작일'].notna()
    ]
    
    # 데이터 타입 변환
    df['상품번호'] = pd.to_numeric(df['상품번호'], errors='coerce')
    df['내부할인'] = pd.to_numeric(df['내부할인'], errors='coerce')
    
    # 날짜 변환 전에 빈 값 정리 (핵심 수정 부분)
    # 이미 위에서 빈 문자열은 NaN으로 변환했으므로 clean_date_value 불필요
    
    # 날짜 변환 - 다양한 포맷 시도
    for col in ['시작일', '종료일', '설정일']:
        # 먼저 문자열로 변환 후 공백 제거
        df[col] = df[col].astype(str).str.strip()
        # 'nan' 문자열을 NaN으로 변환
        df[col] = df[col].replace('nan', pd.NA)
        df[col] = df[col].replace('NaT', pd.NA)
        # 날짜 변환
        df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # NaN 제거
    df = df[df['상품번호'].notna()]
    
    # 디버깅: 설정일 분포 확인
    total_rows = len(df)
    na_count = df['설정일'].isna().sum()
    print(f"  디버그: 전체 {total_rows}개 행 중 설정일 없음 {na_count}개")
    if na_count > 0 and na_count <= 10:
        na_products = df[df['설정일'].isna()]['상품번호'].tolist()
        print(f"  설정일 없는 상품번호: {na_products}")
    elif na_count > 10:
        print(f"  ⚠️ 설정일 없는 행이 {na_count}개로 너무 많습니다!")
        # 샘플 5개만 출력
        na_sample = df[df['설정일'].isna()].head(5)
        print(f"  샘플 5개:")
        for idx, row in na_sample.iterrows():
            print(f"    상품번호: {row['상품번호']}, 시작일: {row['시작일']}, 설정일 원본: {repr(row.get('설정일'))}")
    
    return df


def update_setting_dates(sheet_url: str, credentials_path: str, product_ids: list, sheet_name: str = None):
    """
    구글 시트의 설정일 컬럼에 오늘 날짜 기입
    
    Args:
        sheet_url: 구글 시트 URL
        credentials_path: 서비스 계정 JSON 파일 경로
        product_ids: 업데이트할 상품번호 리스트
        sheet_name: 시트 이름 (None이면 URL의 gid 사용)
    """
    if not product_ids:
        return
    
    print(f"\n📝 구글 시트 설정일 업데이트 중...")
    
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
    
    # 시트 선택
    if sheet_name:
        worksheet = spreadsheet.worksheet(sheet_name)
    elif 'gid=' in sheet_url:
        gid = sheet_url.split('gid=')[1].split('&')[0].split('#')[0]
        worksheet = spreadsheet.get_worksheet_by_id(int(gid))
    else:
        worksheet = spreadsheet.get_worksheet(0)
    
    # 전체 데이터 가져오기 (M열: 상품번호, R열: 설정일)
    # K=10, L=11, M=12, N=13, O=14, P=15, Q=16, R=17 (0-based index)
    all_data = worksheet.get('M4:R')
    
    today = datetime.now().strftime('%Y-%m-%d')
    update_count = 0
    
    # 상품번호를 문자열로 변환 (비교를 위해)
    product_ids_str = [str(pid) for pid in product_ids]
    
    # 업데이트할 행 찾기
    updates = []
    for idx, row in enumerate(all_data, start=4):  # 4행부터 시작
        if len(row) > 0:
            product_id = str(row[0]).strip()  # M열 (상품번호)
            
            if product_id in product_ids_str:
                # R열 (설정일) 위치: 행번호, 18열 (R=18)
                cell_address = f'R{idx}'
                updates.append({
                    'range': cell_address,
                    'values': [[today]]
                })
                update_count += 1
    
    # 일괄 업데이트
    if updates:
        worksheet.batch_update(updates)
        print(f"✓ {update_count}개 상품의 설정일 업데이트 완료 ({today})")
    else:
        print(f"⚠️  업데이트할 상품을 찾지 못했습니다")


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