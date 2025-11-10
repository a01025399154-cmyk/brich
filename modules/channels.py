"""
채널 매핑 모듈
드롭다운 값을 채널 리스트로 변환
표준 채널명 기반 매칭
"""

from typing import Dict, Optional
import pandas as pd
import config


# 드롭다운 값 → 표준 채널명 매핑
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
    "카카오쇼핑": ["카카오 쇼핑하기"],
    "퀸잇": ["퀸잇"],
    "홈앤쇼핑": ["홈앤쇼핑"],
    "*전 채널 (gs제외)": "ALL_EXCEPT_GS",
    "*전 채널 (퀸잇제외)": "ALL_EXCEPT_QUEENIT"
}


def parse_channel_dropdown(channel_str: str, available_channels: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    채널 드롭다운 값을 파싱하여 채널 리스트로 변환
    표준 채널명 기반으로 매칭

    Args:
        channel_str: 드롭다운 값 (예: "*전 채널", "SSG", "지마켓/옥션", "SSG, CJ몰")
        available_channels: 상품인 경우 조회된 채널 정보 {표준_채널명: 채널상품번호}
                           브랜드인 경우 None (모든 채널 사용 가능)

    Returns:
        {표준_채널명: 채널ID 또는 ""} 딕셔너리
    """
    result: Dict[str, str] = {}

    if not channel_str or pd.isna(channel_str):
        return result

    channel_str = str(channel_str).strip()

    # 콤마로 여러 채널이 들어있는 케이스
    if "," in channel_str:
        parts = [p.strip() for p in channel_str.split(",") if p.strip()]
        merged: Dict[str, str] = {}
        for part in parts:
            sub = parse_channel_dropdown(part, available_channels)
            merged.update(sub)
        return merged

    # 드롭다운 매핑 확인
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
            return {
                k: v for k, v in available_channels.items()
                if k != "GS Shop"
            }

        # 퀸잇 제외
        if mapping_value == "ALL_EXCEPT_QUEENIT":
            return {
                k: v for k, v in available_channels.items()
                if k != "퀸잇"
            }

        # 특정 채널(들) - 표준명으로 매칭
        target_channels = mapping_value  # 리스트

        for target in target_channels:
            # 타겟을 표준명으로 변환
            target_standard = config.get_standard_channel_name(target)

            # available_channels에서 표준명으로 검색
            if target_standard in available_channels:
                result[target_standard] = available_channels[target_standard]

        return result

    # === 브랜드 프로모션 (available_channels 없음) ===
    else:
        # 전체 채널
        if mapping_value == "ALL":
            return {ch: "" for ch in config.CHANNEL_NORMALIZATION.keys()}

        # GS 제외
        if mapping_value == "ALL_EXCEPT_GS":
            return {
                ch: "" for ch in config.CHANNEL_NORMALIZATION.keys()
                if ch != "GS Shop"
            }

        # 퀸잇 제외
        if mapping_value == "ALL_EXCEPT_QUEENIT":
            return {
                ch: "" for ch in config.CHANNEL_NORMALIZATION.keys()
                if ch != "퀸잇"
            }

        # 특정 채널(들)
        target_channels = mapping_value  # 리스트
        result = {}
        for ch in target_channels:
            standard_ch = config.get_standard_channel_name(ch)
            result[standard_ch] = ""
        return result