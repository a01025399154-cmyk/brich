"""
엑셀 파일 생성 모듈
xlsxwriter 사용 - Laravel Excel 완벽 호환
"""

import pandas as pd
import os
from datetime import datetime
import xlsxwriter
from typing import List


def generate_upload_files(df: pd.DataFrame, output_dir: str, file_prefix: str = "상품") -> List[str]:
    """
    채널별로 분리된 업로드 파일들 생성 (xlsxwriter 사용)
    
    Args:
        df: 출력 데이터 DataFrame (시작일, 종료일, 채널명 포함)
        output_dir: 출력 디렉토리
        file_prefix: 파일명 prefix ("상품" 또는 "브랜드")
    
    Returns:
        생성된 파일 경로 리스트
    """
    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    
    # (시작일, 종료일, 채널명)으로 그룹화
    grouped = df.groupby(['시작일', '종료일', '채널명'])
    generated_files = []
    
    for (start_date, end_date, channel_name), group_df in grouped:
        # 파일명 생성
        start_str = start_date.strftime('%y%m%d') if pd.notna(start_date) else '000000'
        end_str = end_date.strftime('%y%m%d') if pd.notna(end_date) else '000000'
        item_count = len(group_df)
        
        filename = f"{start_str}-{end_str}_{file_prefix}_{channel_name}_{item_count}.xlsx"
        filepath = os.path.join(output_dir, filename)
        
        # 컬럼 선택
        columns_to_save = [col for col in group_df.columns if col not in ['시작일', '종료일', '채널명']]
        df_to_save = group_df[columns_to_save].copy()
        
        # 데이터 타입 변환
        number_col = '상품번호' if '상품번호' in df_to_save.columns else '브랜드번호'
        
        # 상품번호는 숫자, 브랜드번호는 문자열
        if number_col == '상품번호' and number_col in df_to_save.columns:
            df_to_save[number_col] = df_to_save[number_col].apply(
                lambda x: int(float(x)) if pd.notna(x) else None
            )
        elif number_col == '브랜드번호' and number_col in df_to_save.columns:
            df_to_save[number_col] = df_to_save[number_col].apply(
                lambda x: str(int(float(x))) if pd.notna(x) else ''
            )
        
        # 할인 값 정수 변환
        discount_value_cols = ['내부할인', '연동할인', '외부할인가', '할인', '할인2']
        for col in discount_value_cols:
            if col in df_to_save.columns:
                df_to_save[col] = df_to_save[col].apply(
                    lambda x: int(float(x)) if pd.notna(x) and str(x) != '' else 0
                )
        
        # 분담율 정수 변환
        rate_cols = ['채널분담율', '브리치분담율', '입점사분담율']
        for col in rate_cols:
            if col in df_to_save.columns:
                df_to_save[col] = df_to_save[col].apply(
                    lambda x: int(float(x)) if pd.notna(x) and str(x) != '' else 0
                )
        
        # xlsxwriter로 파일 생성
        workbook = xlsxwriter.Workbook(filepath, {
            'strings_to_numbers': False,
            'strings_to_urls': False,
            'strings_to_formulas': False,
            'constant_memory': False  # sharedStrings 사용
        })
        worksheet = workbook.add_worksheet()
        
        # 포맷 정의
        text_format = workbook.add_format({'num_format': '@'})  # 텍스트
        number_format = workbook.add_format({'num_format': '0'})  # 숫자
        
        # 헤더 작성
        for col_idx, col_name in enumerate(columns_to_save):
            worksheet.write_string(0, col_idx, col_name, text_format)
        
        # 데이터 작성
        for row_idx, (_, row_data) in enumerate(df_to_save.iterrows(), start=1):
            for col_idx, col_name in enumerate(columns_to_save):
                value = row_data[col_name]
                
                if pd.isna(value):
                    continue
                
                # A열 (상품번호/브랜드번호)
                if col_idx == 0:
                    if file_prefix == "브랜드":
                        # 브랜드번호는 문자열
                        worksheet.write_string(row_idx, col_idx, str(value), text_format)
                    else:
                        # 상품번호는 숫자
                        worksheet.write_number(row_idx, col_idx, int(value), number_format)
                
                # 타입 컬럼 (내부할인타입, 연동할인타입 등)
                elif '타입' in col_name:
                    worksheet.write_string(row_idx, col_idx, str(value), text_format)
                
                # 할인 값 컬럼
                elif col_name in discount_value_cols:
                    worksheet.write_number(row_idx, col_idx, int(value), number_format)
                
                # 분담율 컬럼
                elif col_name in rate_cols:
                    worksheet.write_number(row_idx, col_idx, int(value), number_format)
                
                # 기타 (문자열로 처리)
                else:
                    if isinstance(value, (int, float)):
                        worksheet.write_number(row_idx, col_idx, value, number_format)
                    else:
                        worksheet.write_string(row_idx, col_idx, str(value), text_format)
        
        # 컬럼 너비 자동 조정
        for col_idx, col_name in enumerate(columns_to_save):
            max_length = len(col_name)
            for row_idx in range(len(df_to_save)):
                try:
                    cell_value = str(df_to_save.iloc[row_idx, col_idx])
                    if len(cell_value) > max_length:
                        max_length = len(cell_value)
                except:
                    pass
            
            adjusted_width = min(max_length + 2, 50)
            worksheet.set_column(col_idx, col_idx, adjusted_width)
        
        workbook.close()
        
        generated_files.append(filepath)
        print(f"  ✓ 생성: {filename}")
    
    return generated_files


if __name__ == "__main__":
    # 테스트 - 상품 프로모션
    df_test_product = pd.DataFrame({
        '시작일': [pd.Timestamp('2025-11-01')] * 2,
        '종료일': [pd.Timestamp('2025-12-05')] * 2,
        '채널명': ['SSG', 'SSG'],
        '상품번호': [1000614610607, 1000614610608],
        '내부할인타입': ['P', 'P'],
        '내부할인': [17, 17],
        '연동할인타입': ['', ''],
        '연동할인': [0, 0],
        '외부할인타입': ['', ''],
        '외부할인가': [0, 0],
        '채널분담율': [0, 0],
        '브리치분담율': [0, 0],
        '입점사분담율': [100, 100]
    })
    
    output_files = generate_upload_files(df_test_product, '/home/claude/test_output', '상품')
    print(f"\n상품 테스트 완료: {len(output_files)}개 파일 생성")
    
    # 테스트 - 브랜드 프로모션
    df_test_brand = pd.DataFrame({
        '시작일': [pd.Timestamp('2025-10-01')] * 2,
        '종료일': [pd.Timestamp('2025-10-31')] * 2,
        '채널명': ['SSG', 'SSG'],
        '브랜드번호': [1838, 3197],
        '할인타입': ['P', 'P'],
        '할인': [15, 15],
        '채널분담율': [0, 0],
        '브리치분담율': [0, 0],
        '입점사분담율': [100, 100]
    })
    
    output_files = generate_upload_files(df_test_brand, '/home/claude/test_output', '브랜드')
    print(f"\n브랜드 테스트 완료: {len(output_files)}개 파일 생성")