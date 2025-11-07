"""
채널 매핑 모듈
드롭다운 값을 채널 리스트로 변환
"""

from typing import Dict, List, Optional
import pandas as pd


# 드롭다운 값 → 채널 매핑
CHANNEL_DROPDOWN_MAPPING = {
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
    "카카오쇼핑": ["카카오쇼핑"],
    "퀸잇": ["퀸잇"],
    "홈앤쇼핑": ["홈앤쇼핑"],
    "*전 채널 (gs제외)": "ALL_EXCEPT_GS",
    "*전 채널 (퀸잇제외)": "ALL_EXCEPT_QUEENIT"
}


def parse_channel_dropdown(channel_str: str, available_channels: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    채널 드롭다운 값을 파싱하여 채널 리스트로 변환

    Args:
        channel_str: 드롭다운 값 (예: "*전 채널", "SSG", "지마켓/옥션", "SSG, CJ몰")
        available_channels: 상품인 경우 API에서 조회한 채널 정보 {채널명: 채널상품번호}
                           브랜드인 경우 None (모든 채널 사용 가능)

    Returns:
        {채널명: 채널ID 또는 ""} 딕셔너리
        브랜드인 경우 채널ID는 빈 문자열
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
            sub = parse_channel_dropdown(part, available_channels)  # 재귀 호출 (단일 값 처리)
            merged.update(sub)
        return merged

    # 🔹 1단계: 단일 드롭다운 값 처리
    if channel_str not in CHANNEL_DROPDOWN_MAPPING:
        print(f"    ⚠️  알 수 없는 드롭다운 값: '{channel_str}'")
        return result

    mapping_value = CHANNEL_DROPDOWN_MAPPING[channel_str]

    # === 상품 프로모션 (available_channels 있음) ===
    if available_channels is not None:
        # 전체 채널
        if mapping_value == "ALL":
            return available_channels.copy()

        # GS 제외
        if mapping_value == "ALL_EXCEPT_GS":
            tmp = available_channels.copy()
            return {
                k: v
                for k, v in tmp.items()
                if "gs shop" not in k.lower() and "gsshop" not in k.lower()
            }

        # 퀸잇 제외
        if mapping_value == "ALL_EXCEPT_QUEENIT":
            tmp = available_channels.copy()
            return {
                k: v
                for k, v in tmp.items()
                if "퀸잇" not in k and "queenit" not in k.lower()
            }

        # 특정 채널(들)
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

    # === 브랜드 프로모션 (available_channels 없음) ===
    else:
        # 전체 채널
        if mapping_value == "ALL":
            all_channels = [
                "SSG",
                "지마켓",
                "옥션",
                "11번가",
                "쿠팡",
                "GS Shop",
                "롯데ON",
                "CJ몰",
                "Halfclub",
                "롯데i몰",
                "카카오스타일",
                "퀸잇",
                "홈앤쇼핑",
            ]
            return {ch: "" for ch in all_channels}

        # GS 제외
        if mapping_value == "ALL_EXCEPT_GS":
            all_channels = [
                "SSG",
                "지마켓",
                "옥션",
                "11번가",
                "쿠팡",
                "롯데ON",
                "CJ몰",
                "Halfclub",
                "롯데i몰",
                "카카오스타일",
                "퀸잇",
                "홈앤쇼핑",
            ]
            return {ch: "" for ch in all_channels if ch not in ["GS Shop"]}

        # 퀸잇 제외
        if mapping_value == "ALL_EXCEPT_QUEENIT":
            all_channels = [
                "SSG",
                "지마켓",
                "옥션",
                "11번가",
                "쿠팡",
                "GS Shop",
                "롯데ON",
                "CJ몰",
                "Halfclub",
                "롯데i몰",
                "카카오스타일",
                "퀸잇",
                "홈앤쇼핑",
            ]
            return {ch: "" for ch in all_channels if ch != "퀸잇"}

        # 특정 채널(들)
        target_channels = mapping_value  # 리스트
        return {ch: "" for ch in target_channels}


if __name__ == "__main__":
    # 테스트
    
    # 브랜드 프로모션 테스트
    print("=== 브랜드 프로모션 테스트 ===")
    result1 = parse_channel_dropdown("*전 채널", None)
    print(f"*전 채널: {list(result1.keys())}")
    
    result2 = parse_channel_dropdown("지마켓/옥션", None)
    print(f"지마켓/옥션: {list(result2.keys())}")
    
    result3 = parse_channel_dropdown("SSG", None)
    print(f"SSG: {list(result3.keys())}")
    
    # 상품 프로모션 테스트
    print("\n=== 상품 프로모션 테스트 ===")
    available = {
        "SSG": "1000614610607",
        "쿠팡": "200012345678",
        "지마켓": "123456789",
        "GS Shop": "999999"
    }
    
    result4 = parse_channel_dropdown("*전 채널", available)
    print(f"*전 채널: {result4}")
    
    result5 = parse_channel_dropdown("*전 채널 (gs제외)", available)
    print(f"*전 채널 (gs제외): {result5}")
    
    result6 = parse_channel_dropdown("SSG", available)
    print(f"SSG: {result6}")