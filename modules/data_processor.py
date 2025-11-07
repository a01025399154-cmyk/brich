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
    
    # 설정일이 없는 상품만 처리 (조회 대상만)
    df_to_process = df_input[df_input["설정일"].isna()].copy()
    
    # 디버깅: 실제로 몇 개를 처리하는지 확인
    print(f"  디버그: df_input 전체 {len(df_input)}개, 설정일 없음 {len(df_to_process)}개")
    
    for _, row in df_to_process.iterrows():
        product_id = int(row['상품번호'])
        channel_info = row['채널']
        
        # 채널 매핑 정보 가져오기
        # 조회 대상 상품(설정일 없음)만 여기까지 왔으므로, 
        # 채널 정보가 없으면 실제 문제가 있는 것
        if product_id not in channel_mappings:
            print(f"  경고: 상품 {product_id} 채널 정보 없음 (API 조회 실패 또는 채널 미등록)")
            continue
        
        product_channels = channel_mappings[product_id]
        
        # 채널 정보 파싱
        target_channels = parse_channel_info(channel_info, product_channels)
        
        # 각 채널별로 행 생성 (비플로우 상품번호 전달)
        for channel_name, channel_product_id in target_channels.items():
            output_row = create_output_row(row, channel_name, product_id)  # product_id를 전달
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
    채널 정보 파싱 (드롭다운 값 기반)

    Args:
        channel_str: P열 드롭다운 값
        available_channels: 해당 상품이 등록된 채널 {채널명: 채널상품번호}

    Returns:
        {채널명: 채널상품번호}
    """
    result: Dict[str, str] = {}

    if not channel_str or pd.isna(channel_str):
        return result

    channel_str = str(channel_str).strip()

    # 🔹 0단계: 콤마(,)로 여러 채널이 들어있는 케이스 먼저 처리
    #   예) "SSG, CJ몰", "SSG, GS샵, CJ몰"
    if "," in channel_str:
        parts = [p.strip() for p in channel_str.split(",") if p.strip()]
        merged: Dict[str, str] = {}
        for part in parts:
            sub = parse_channel_info(part, available_channels)  # 재귀 호출 (단일 값 처리)
            # 같은 채널명이 중복되면 나중 것이 덮어씌워도 상관 없음
            merged.update(sub)
        return merged

    # 🔹 1단계: 단일 드롭다운 값에 대한 처리
    DROPDOWN_MAPPING = {
        "*전 채널": "ALL",
        "지마켓/옥션": ["지마켓", "옥션"],
        "11번가": ["11번가"],
        "쿠팡": ["쿠팡"],
        "SSG": ["SSG"],
        "GS샵": ["GS Shop"],
        "롯데온": ["롯데ON"],
        "CJ몰": ["CJ몰"],
        "하프클럽": ["Halfclub"],
        "롯데i몰": ["롯데i몰"],
        "카카오스타일": ["카카오스타일"],
        "퀸잇": ["퀸잇"],
        "홈앤쇼핑": ["홈앤쇼핑"],
        "*전 채널 (gs제외)": "ALL_EXCEPT_GS",
        "*전 채널 (퀸잇제외)": "ALL_EXCEPT_QUEENIT",
    }

    # 매핑 테이블에서 찾기
    if channel_str not in DROPDOWN_MAPPING:
        print(f"    ⚠️  알 수 없는 드롭다운 값: '{channel_str}'")
        return result

    mapping_value = DROPDOWN_MAPPING[channel_str]

    # 2. 전체 채널
    if mapping_value == "ALL":
        return available_channels.copy()

    # 3. GS 제외
    if mapping_value == "ALL_EXCEPT_GS":
        tmp = available_channels.copy()
        return {
            k: v
            for k, v in tmp.items()
            if "gs shop" not in k.lower() and "gsshop" not in k.lower()
        }

    # 4. 퀸잇 제외
    if mapping_value == "ALL_EXCEPT_QUEENIT":
        tmp = available_channels.copy()
        return {
            k: v
            for k, v in tmp.items()
            if "퀸잇" not in k and "queenit" not in k.lower()
        }

    # 5. 특정 채널(들)
    target_channels = mapping_value  # 리스트

    for target in target_channels:
        target_normalized = target.lower().replace(" ", "")

        for avail_ch, ch_id in available_channels.items():
            avail_normalized = avail_ch.lower().replace(" ", "")

            if (
                target_normalized == avail_normalized
                or target_normalized in avail_normalized
                or avail_normalized in target_normalized
            ):
                result[avail_ch] = ch_id
                break

    return result


def create_output_row(input_row: pd.Series, channel_name: str, beeflow_product_id: int) -> list:
    """
    출력 행 생성
    
    Args:
        input_row: K~R열의 한 행
        channel_name: 채널명
        beeflow_product_id: 비플로우 상품번호 (예: 412533475)
    
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
        # 퍼센트는 그대로 사용 (구글시트에서 이미 17로 입력됨)
        # 만약 0.17처럼 소수로 입력된 경우만 100 곱하기
        if 0 < discount_value < 1:
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
        beeflow_product_id,      # 상품번호 (비플로우 상품번호)
        discount_type,           # 내부할인타입
        discount_value,          # 내부할인
        discount_type,           # 연동할인타입 (내부할인타입과 동일)
        0,                       # 연동할인 (0 고정)
        discount_type,           # 외부할인타입 (내부할인타입과 동일)
        0,                       # 외부할인가 (0 고정)
        0,                       # 채널분담율 (0 고정)
        0,                       # 브리치분담율 (0 고정)
        100                      # 입점사분담율 (100 고정)
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