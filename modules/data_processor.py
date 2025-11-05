"""
데이터 처리 모듈
K~R열 데이터 + 채널 매핑 → product_promotion_upload 형식으로 변환
"""

import pandas as pd
from typing import Dict

def process_promotion_data(df_input: pd.DataFrame, channel_mappings: Dict) -> pd.DataFrame:
    """
    프로모션 데이터 처리 및 확장
    
    Args:
        df_input: K~R열 DataFrame
        channel_mappings: {상품번호: {채널명: 채널상품번호}}
    
    Returns:
        product_promotion_upload 형식의 DataFrame (시작일, 종료일, 채널명 포함)
    """
    output_rows = []
    
    for _, row in df_input.iterrows():
        product_id = int(row['상품번호'])
        channel_info = row['채널']
        
        # 채널 매핑 정보 가져오기
        if product_id not in channel_mappings:
            print(f"  경고: 상품 {product_id} 채널 정보 없음")
            continue
        
        product_channels = channel_mappings[product_id]
        
        # 채널 정보 파싱
        target_channels = parse_channel_info(channel_info, product_channels)
        
        # 각 채널별로 행 생성
        for channel_name, channel_product_id in target_channels.items():
            output_row = create_output_row(row, channel_name, channel_product_id)
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


def parse_channel_info(channel_str: str, available_channels: Dict) -> Dict[str, str]:
    """
    채널 정보 파싱
    
    Args:
        channel_str: P열 값 ("*전 채널", "SSG", "쿠팡,11번가" 등)
        available_channels: 해당 상품이 등록된 채널 {채널명: 채널상품번호}
    
    Returns:
        {채널명: 채널상품번호}
    """
    result = {}
    
    if not channel_str or pd.isna(channel_str):
        return result
    
    channel_str = str(channel_str).strip()
    
    if channel_str == "*전 채널":
        # 모든 등록된 채널
        result = available_channels.copy()
    else:
        # 특정 채널(들)
        requested_channels = [ch.strip() for ch in channel_str.split(',')]
        
        for req_ch in requested_channels:
            # 채널명 매칭 (대소문자 무시, 공백 제거)
            req_ch_normalized = req_ch.lower().replace(' ', '')
            
            for avail_ch, ch_id in available_channels.items():
                avail_ch_normalized = avail_ch.lower().replace(' ', '')
                
                if req_ch_normalized in avail_ch_normalized or avail_ch_normalized in req_ch_normalized:
                    result[avail_ch] = ch_id
                    break
    
    return result


def create_output_row(input_row: pd.Series, channel_name: str, channel_product_id: str) -> list:
    """
    출력 행 생성
    
    Args:
        input_row: K~R열의 한 행
        channel_name: 채널명
        channel_product_id: 채널별 상품번호
    
    Returns:
        [시작일, 종료일, 채널명, 상품번호, 내부할인타입, 내부할인, ...]
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
        # 0.17 → 17로 변환 (1보다 작으면 100을 곱함)
        if discount_value < 1:
            discount_value = discount_value * 100
    elif discount_type == 'W':  # 원화
        # 그대로 사용
        pass
    elif discount_type == 'A':  # 절대값 (원화)
        # 그대로 사용
        pass
    else:
        # 알 수 없는 타입은 그대로 사용
        pass
    
    # 날짜 정보
    start_date = input_row.get('시작일')
    end_date = input_row.get('종료일')
    
    # 출력 행 (시작일, 종료일, 채널명 포함)
    row = [
        start_date,              # 시작일
        end_date,                # 종료일
        channel_name,            # 채널명
        channel_product_id,      # 상품번호
        discount_type,           # 내부할인타입
        discount_value,          # 내부할인
        '',                      # 연동할인타입 (선택)
        '',                      # 연동할인 (선택)
        '',                      # 외부할인타입 (선택)
        '',                      # 외부할인가 (선택)
        '',                      # 채널분담율 (선택)
        '',                      # 브리치분담율 (선택)
        ''                       # 입점사분담율 (선택)
    ]
    
    return row


if __name__ == "__main__":
    # 테스트
    import pandas as pd
    
    # 샘플 입력 데이터
    df_test = pd.DataFrame({
        '시작일': [pd.Timestamp('2025-11-01')],
        '종료일': [pd.Timestamp('2025-12-05')],
        '상품번호': [986269048],
        '내부할인타입': ['P'],
        '내부할인': [0.17],
        '채널': ['*전 채널'],
        '추가설명': ['포레스트핏'],
        '설정일': [None]
    })
    
    # 샘플 채널 매핑
    mappings = {
        986269048: {
            'SSG': '1000614610607',
            '쿠팡': '200012345678',
            '지마켓(상품번호)': '123456789'
        }
    }
    
    # 처리
    df_output = process_promotion_data(df_test, mappings)
    
    print("출력 결과:")
    print(df_output)