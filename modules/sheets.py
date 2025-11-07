"""
구글 시트 읽기/쓰기 모듈
상품 프로모션과 브랜드 프로모션 지원
"""

import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional


def get_sheet_list(sheet_url: str, credentials_path: str) -> list:
    """
    구글 스프레드시트의 모든 시트 목록 가져오기
    
    Args:
        sheet_url: 구글 시트 URL
        credentials_path: 서비스 계정 JSON 파일 경로
    
    Returns:
        list: 시트 이름 리스트
    """
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
    client = gspread.authorize(creds)
    
    sheet_id = sheet_url.split('/d/')[1].split('/')[0]
    spreadsheet = client.open_by_key(sheet_id)
    
    worksheets = spreadsheet.worksheets()
    sheet_names = [ws.title for ws in worksheets]
    
    return sheet_names


def select_sheet_interactive(sheet_names: list) -> str:
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


def read_sheet(sheet_url: str, credentials_path: str, column_range: str, 
               column_mapping: dict, start_row: int = 4, 
               sheet_name: Optional[str] = None, interactive: bool = True) -> pd.DataFrame:
    """
    구글 시트에서 데이터 읽기 (상품/브랜드 공통)
    
    Args:
        sheet_url: 구글 시트 URL
        credentials_path: 서비스 계정 JSON 파일 경로
        column_range: 읽을 컬럼 범위 (예: "K:R", "A:I")
        column_mapping: 컬럼 매핑 딕셔너리
        start_row: 데이터 시작 행 (기본 4)
        sheet_name: 읽을 시트 이름
        interactive: 시트 선택 인터랙티브 모드
    
    Returns:
        DataFrame: 읽은 데이터
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
    
    # 시트 선택
    if sheet_name is None:
        if interactive:
            sheet_names = [ws.title for ws in spreadsheet.worksheets()]
            selected_name = select_sheet_interactive(sheet_names)
            worksheet = spreadsheet.worksheet(selected_name)
        else:
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
    
    # 데이터 가져오기
    columns = column_range.split(":")
    start_col = columns[0]
    end_col = columns[1] if len(columns) > 1 else columns[0]
    data_range = f"{start_col}{start_row}:{end_col}"
    data = worksheet.get(data_range)
    
    # DataFrame 생성 (행마다 컬럼 개수 맞추기)
    num_cols = len(column_mapping)
    padded_data = [row + [''] * (num_cols - len(row)) if len(row) < num_cols else row[:num_cols] for row in data]
    df = pd.DataFrame(padded_data, columns=list(column_mapping.values()))
    
    # 빈 문자열을 NaN으로 변환
    df = df.replace('', np.nan)
    df = df.replace(' ', np.nan)
    # 주의: '-'는 날짜 형식에 사용되므로 제외
    
    # 첫 번째 컬럼 (상품번호 또는 브랜드번호)과 시작일이 있는 행만 유효
    first_col = list(column_mapping.values())[2]  # 3번째 컬럼 (번호 컬럼)
    df = df[df[first_col].notna() & df['시작일'].notna()]
    
    # 번호 컬럼을 숫자로 변환
    df[first_col] = pd.to_numeric(df[first_col], errors='coerce')
    
    # 할인 값 처리
    def parse_discount_value(val):
        if pd.isna(val):
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        
        val_str = str(val).strip()
        if not val_str or val_str == '':
            return 0.0
        
        if '%' in val_str:
            val_str = val_str.replace('%', '').strip()
        if '원' in val_str:
            val_str = val_str.replace('원', '').strip()
        val_str = val_str.replace(',', '')
        
        try:
            return float(val_str)
        except:
            return 0.0
    
    # 할인 컬럼 처리 (상품: 내부할인, 브랜드: 할인)
    for col in df.columns:
        if '할인' in col and '타입' not in col:
            df[col] = df[col].apply(parse_discount_value)
    
    # 날짜 변환
    for col in ['시작일', '종료일', '설정일']:
        if col in df.columns:
            # 빈 값 마스크 생성 (문자열 변환 전)
            mask_empty = df[col].isna() | (df[col] == '') | (df[col].astype(str).str.strip() == 'nan')
            # 빈 값이 아닌 것만 날짜로 변환
            df.loc[~mask_empty, col] = pd.to_datetime(df[col][~mask_empty], format='mixed', errors='coerce')
            df.loc[mask_empty, col] = pd.NaT
    
    # NaN 제거
    df = df[df[first_col].notna()]
    
    # 디버깅: 설정일 분포 확인
    total_rows = len(df)
    na_count = df['설정일'].isna().sum()
    print(f"  디버그: 전체 {total_rows}개 행 중 설정일 없음 {na_count}개")
    
    return df


def update_setting_dates(sheet_url: str, credentials_path: str, 
                         ids: list, id_column: str, setting_column: str,
                         sheet_name: Optional[str] = None):
    """
    구글 시트의 설정일 컬럼에 오늘 날짜 기입
    
    Args:
        sheet_url: 구글 시트 URL
        credentials_path: 서비스 계정 JSON 파일 경로
        ids: 업데이트할 ID 리스트 (상품번호 또는 브랜드번호)
        id_column: ID 컬럼 (예: "M", "C")
        setting_column: 설정일 컬럼 (예: "R", "I")
        sheet_name: 시트 이름
    """
    if not ids:
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
    
    # 전체 데이터 가져오기
    all_data = worksheet.get(f'{id_column}4:{setting_column}')
    
    now = datetime.now()
    today = f"{now.year}. {now.month}. {now.day}"
    update_count = 0
    
    # 상품/브랜드 번호를 문자열로 변환
    ids_str = [str(pid) for pid in ids]
    
    # 업데이트할 행 찾기
    updates = []
    id_col_index = ord(id_column) - ord('A')
    setting_col_index = ord(setting_column) - ord('A')
    offset = setting_col_index - id_col_index
    
    for idx, row in enumerate(all_data, start=4):
        if len(row) > 0:
            row_id = str(row[0]).strip()
            
            if row_id in ids_str:
                cell_address = f'{setting_column}{idx}'
                updates.append({
                    'range': cell_address,
                    'values': [[today]]
                })
                update_count += 1
    
    # 일괄 업데이트
    if updates:
        worksheet.batch_update(updates)
        print(f"✓ {update_count}개 항목의 설정일 업데이트 완료 ({today})")
    else:
        print(f"⚠️  업데이트할 항목을 찾지 못했습니다")