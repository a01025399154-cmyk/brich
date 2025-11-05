"""
엑셀 파일 생성 모듈
product_promotion_upload.xlsx 생성
"""

import pandas as pd
import os
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment

def generate_upload_file(df: pd.DataFrame, output_dir: str) -> str:
    """
    product_promotion_upload.xlsx 파일 생성
    
    Args:
        df: 출력 데이터 DataFrame
        output_dir: 출력 디렉토리
    
    Returns:
        생성된 파일 경로
    """
    # 파일명 생성
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"product_promotion_upload_{timestamp}.xlsx"
    filepath = os.path.join(output_dir, filename)
    
    # 엑셀 파일 생성
    df.to_excel(filepath, index=False, engine='openpyxl')
    
    # 포맷팅
    wb = load_workbook(filepath)
    ws = wb.active
    
    # 헤더 스타일
    header_font = Font(bold=True)
    for cell in ws[1]:
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')
    
    # 컬럼 너비 자동 조정
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    # 저장
    wb.save(filepath)
    
    return filepath


if __name__ == "__main__":
    # 테스트
    df_test = pd.DataFrame({
        '상품번호': ['1000614610607', '200012345678'],
        '내부할인타입': ['P', 'P'],
        '내부할인': [17, 16],
        '연동할인타입': ['', ''],
        '연동할인': ['', ''],
        '외부할인타입': ['', ''],
        '외부할인가': ['', ''],
        '채널분담율': ['', ''],
        '브리치분담율': ['', ''],
        '입점사분담율': ['', '']
    })
    
    output_file = generate_upload_file(df_test, '/home/claude')
    print(f"테스트 파일 생성: {output_file}")