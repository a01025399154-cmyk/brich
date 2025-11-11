"""
데이터 처리 모듈 (리팩토링)
상품 프로모션과 브랜드 프로모션 데이터 처리
CHANNEL_MASTER 기반 채널 파싱
"""

import sys
from pathlib import Path
# 프로젝트 루트를 Python 경로에 추가
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
from typing import Dict
from modules.channels import parse_channel_dropdown


def process_product_promotion(df_input: pd.DataFrame, channel_mappings: Dict) -> pd.DataFrame:
    """
    상품 프로모션 데이터 처리
    
    Args:
        df_input: K~R열 DataFrame
        channel_mappings: {상품번호: {채널명: 채널상품번호}}
    
    Returns:
        product_promotion_upload 형식의 DataFrame
    """
    output_rows = []
    
    # 설정일이 없는 상품만 처리
    df_to_process = df_input[df_input["설정일"].isna()].copy()
    
    print(f"  디버그: df_input 전체 {len(df_input)}개, 설정일 없음 {len(df_to_process)}개")
    
    for _, row in df_to_process.iterrows():
        product_id = int(row['상품번호'])
        channel_info = row['채널']
        
        # ⭐ 디버깅 로그 추가
        print(f"\n  [디버그] 상품 {product_id}")
        print(f"    채널 값: '{channel_info}'")
        
        # 채널 매핑 정보 확인
        if product_id not in channel_mappings:
            print(f"    ✗ 채널 매핑 정보 없음")
            continue
        
        product_channels = channel_mappings[product_id]
        print(f"    ✓ API 채널: {list(product_channels.keys())}")
        
        # 채널 정보 파싱 (상품 프로모션)
        target_channels = parse_channel_dropdown(
            channel_info, 
            available_channels=product_channels,
            promo_type="product"  # ✅ 명시적 타입 지정
        )
        print(f"    → 파싱 결과: {list(target_channels.keys()) if target_channels else '없음'}")
        
        # 각 채널별로 행 생성
        for channel_name, channel_product_id in target_channels.items():
            output_row = _create_product_row(row, channel_name, product_id)
            output_rows.append(output_row)
    
    # DataFrame 생성
    df_output = pd.DataFrame(output_rows, columns=[
        '시작일',
        '종료일',
        '채널명',
        '상품번호',
        '내부할인타입',
        '내부할인',
        '연동할인타입',
        '연동할인',
        '외부할인타입',
        '외부할인가',
        '채널분담율',
        '브리치분담율',
        '입점사분담율'
    ])
    
    return df_output


def process_brand_promotion(df_input: pd.DataFrame) -> pd.DataFrame:
    """
    브랜드 프로모션 데이터 처리
    
    Args:
        df_input: A~I열 DataFrame
    
    Returns:
        brand_promotion_upload 형식의 DataFrame
    """
    output_rows = []
    
    # 설정일이 없는 브랜드만 처리
    df_to_process = df_input[df_input["설정일"].isna()].copy()
    
    print(f"  디버그: df_input 전체 {len(df_input)}개, 설정일 없음 {len(df_to_process)}개")
    
    for _, row in df_to_process.iterrows():
        brand_id = int(row['브랜드번호'])
        channel_info = row['채널']
        
        # 채널 정보 파싱 (브랜드 프로모션 - API 조회 없음)
        target_channels = parse_channel_dropdown(
            channel_info, 
            available_channels=None,
            promo_type="brand"  # ✅ 명시적 타입 지정
        )
        
        # 각 채널별로 행 생성
        for channel_name in target_channels.keys():
            output_row = _create_brand_row(row, channel_name, brand_id)
            output_rows.append(output_row)
    
    # DataFrame 생성
    df_output = pd.DataFrame(output_rows, columns=[
        '시작일',
        '종료일',
        '채널명',
        '브랜드번호',
        '할인타입',
        '할인',
        '채널분담율',
        '브리치분담율',
        '입점사분담율'
    ])
    
    return df_output


def _create_product_row(input_row: pd.Series, channel_name: str, product_id: int) -> list:
    """
    상품 프로모션 출력 행 생성 (13개 컬럼)
    
    Args:
        input_row: K~R열의 한 행
        channel_name: 채널명
        product_id: 상품번호
    
    Returns:
        [시작일, 종료일, 채널명, 상품번호, ...]
    """
    # 할인 정보 추출
    discount_type = input_row.get('내부할인타입', '')
    discount_value_raw = input_row.get('내부할인', 0)
    
    # NaN 체크 및 기본값 설정
    if pd.isna(discount_value_raw):
        discount_value = 0
    else:
        discount_value = float(discount_value_raw)
    
    # 타입별 처리
    if discount_type == 'P':  # 퍼센트
        if 0 < discount_value < 1:
            discount_value = discount_value * 100
    
    # 날짜 정보
    start_date = input_row.get('시작일')
    end_date = input_row.get('종료일')
    
    # 출력 행 (13개 컬럼)
    row = [
        start_date,              # 시작일
        end_date,                # 종료일
        channel_name,            # 채널명
        product_id,              # 상품번호
        discount_type,           # 내부할인타입
        discount_value,          # 내부할인
        discount_type,           # 연동할인타입
        0,                       # 연동할인
        discount_type,           # 외부할인타입
        0,                       # 외부할인가
        0,                       # 채널분담율
        0,                       # 브리치분담율
        100                      # 입점사분담율
    ]
    
    return row


def _create_brand_row(input_row: pd.Series, channel_name: str, brand_id: int) -> list:
    """
    브랜드 프로모션 출력 행 생성 (9개 컬럼)
    
    Args:
        input_row: A~I열의 한 행
        channel_name: 채널명
        brand_id: 브랜드번호
    
    Returns:
        [시작일, 종료일, 채널명, 브랜드번호, ...]
    """
    # 할인 정보 추출
    discount_type = input_row.get('할인타입', '')
    discount_value_raw = input_row.get('할인', 0)
    
    # NaN 체크 및 기본값 설정
    if pd.isna(discount_value_raw):
        discount_value = 0
    else:
        discount_value = float(discount_value_raw)
    
    # 타입별 처리
    if discount_type == 'P':  # 퍼센트
        if 0 < discount_value < 1:
            discount_value = discount_value * 100
    
    # 날짜 정보
    start_date = input_row.get('시작일')
    end_date = input_row.get('종료일')
    
    # 출력 행 (9개 컬럼)
    row = [
        start_date,              # 시작일
        end_date,                # 종료일
        channel_name,            # 채널명
        brand_id,                # 브랜드번호
        discount_type,           # 할인타입
        discount_value,          # 할인
        0,                       # 채널분담율
        0,                       # 브리치분담율
        100                      # 입점사분담율
    ]
    
    return row


if __name__ == "__main__":
    # 테스트
    
    # 상품 프로모션 테스트
    print("=== 상품 프로모션 테스트 ===")
    df_test_product = pd.DataFrame({
        '시작일': [pd.Timestamp('2025-11-01')],
        '종료일': [pd.Timestamp('2025-12-05')],
        '상품번호': [986269048],
        '내부할인타입': ['P'],
        '내부할인': [17],
        '채널': ['*전 채널'],
        '추가설명': ['테스트'],
        '설정일': [None]
    })
    
    mappings = {
        986269048: {
            'SSG': '1000614610607',
            '쿠팡': '200012345678'
        }
    }
    
    df_output_product = process_product_promotion(df_test_product, mappings)
    print(df_output_product)
    
    # 브랜드 프로모션 테스트
    print("\n=== 브랜드 프로모션 테스트 ===")
    df_test_brand = pd.DataFrame({
        '시작일': [pd.Timestamp('2025-10-01')],
        '종료일': [pd.Timestamp('2025-10-31')],
        '브랜드번호': [1838],
        '할인타입': ['P'],
        '할인': [15],
        '할인2': [0],
        '추가설명': ['허니제이'],
        '채널': ['SSG'],
        '설정일': [None]
    })
    
    df_output_brand = process_brand_promotion(df_test_brand)
    print(df_output_brand)
    print(f"\n✅ 브랜드 행 수: {len(df_output_brand)} (예상: 1, SSG만)")