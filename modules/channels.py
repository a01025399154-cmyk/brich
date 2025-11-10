"""
채널 매핑 모듈 (리팩토링)
드롭다운 값을 채널 리스트로 변환
CHANNEL_MASTER 기반 일원화
"""

from typing import Dict, Optional
import pandas as pd
import config


def _get_dropdown_mapping(promo_type: str) -> Dict[str, any]:
    """
    프로모션 타입별 드롭다운 매핑 동적 생성
    
    Args:
        promo_type: "product" 또는 "brand"
    
    Returns:
        드롭다운 문자열 → 표준 채널명 매핑
    """
    enabled_channels = config.get_enabled_channels(promo_type)
    
    mapping = {
        "*전 채널": "ALL",
        "*전 채널 (gs제외)": "ALL_EXCEPT_GS",
        "*전 채널 (퀸잇제외)": "ALL_EXCEPT_QUEENIT",
    }
    
    # 개별 채널 추가
    for std in enabled_channels:
        info = config.CHANNEL_MASTER[std]
        dropdown_name = info["dropdown_name"]
        mapping[dropdown_name] = [std]
    
    # 특수 조합 (지마켓/옥션)
    if promo_type == "product":
        if "지마켓" in enabled_channels and "옥션" in enabled_channels:
            mapping["지마켓/옥션"] = ["지마켓", "옥션"]
    
    return mapping


def parse_channel_dropdown(
    channel_str: str, 
    available_channels: Optional[Dict[str, str]] = None,
    promo_type: str = "brand"
) -> Dict[str, str]:
    """
    채널 드롭다운 값을 파싱하여 채널 리스트로 변환
    
    Args:
        channel_str: 드롭다운 값 (예: "*전 채널", "SSG", "지마켓/옥션", "SSG, CJ몰")
        available_channels: 상품인 경우 조회된 채널 정보 {표준_채널명: 채널상품번호}
                           브랜드인 경우 None
        promo_type: "product" 또는 "brand" (드롭다운 매핑 결정용)
    
    Returns:
        {표준_채널명: 채널ID 또는 ""} 딕셔너리
    """
    result: Dict[str, str] = {}

    if not channel_str or pd.isna(channel_str):
        return result

    channel_str = str(channel_str).strip()
    
    # 프로모션 타입 추론 (하위 호환성)
    if available_channels is not None:
        promo_type = "product"
    
    # 동적 드롭다운 매핑 생성
    DROPDOWN_MAPPING = _get_dropdown_mapping(promo_type)
    enabled_channels = config.get_enabled_channels(promo_type)

    # 콤마로 여러 채널이 들어있는 케이스
    if "," in channel_str:
        parts = [p.strip() for p in channel_str.split(",") if p.strip()]
        merged: Dict[str, str] = {}
        for part in parts:
            sub = parse_channel_dropdown(part, available_channels, promo_type)
            merged.update(sub)
        return merged

    # 드롭다운 매핑 확인
    if channel_str not in DROPDOWN_MAPPING:
        print(f"    ⚠️  알 수 없는 드롭다운 값: '{channel_str}'")
        return result

    mapping_value = DROPDOWN_MAPPING[channel_str]

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
        # 전체 채널 → 드롭다운 활성화된 채널만
        if mapping_value == "ALL":
            return {ch: "" for ch in enabled_channels}

        # GS 제외
        if mapping_value == "ALL_EXCEPT_GS":
            return {
                ch: "" for ch in enabled_channels
                if ch != "GS Shop"
            }

        # 퀸잇 제외
        if mapping_value == "ALL_EXCEPT_QUEENIT":
            return {
                ch: "" for ch in enabled_channels
                if ch != "퀸잇"
            }

        # 특정 채널(들)
        target_channels = mapping_value  # 리스트
        result = {}
        for ch in target_channels:
            standard_ch = config.get_standard_channel_name(ch)
            # 활성화된 채널인지 확인
            if standard_ch in enabled_channels:
                result[standard_ch] = ""
        return result