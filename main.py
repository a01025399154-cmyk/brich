#!/usr/bin/env python3
"""
프로모션 자동화 메인 스크립트
구글 시트 K~R열 읽기 → 비플로우 조회 (내부 API) → product_promotion_upload.xlsx 생성
"""

import os
import sys
from datetime import datetime

from modules.google_sheet import read_discount_sheet
from modules.bflow import BeeflowClient
from modules.data_processor import process_promotion_data
from modules.excel_generator import generate_upload_file

# 설정
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1Ca-AXLDXIpyb_N_9AvI_2fT5g-jMEDYlv233mbkRdVs/edit?gid=737496399#gid=737496399"
GOOGLE_CREDENTIALS_PATH = "inner-sale-979c1e8ed412.json"

# 🔹 비플로우 내부 API 베이스 URL (로그인/셀레니움 사용 안 함)
BEEFLOW_API_BASE_URL = "http://192.168.0.10:10645"

OUTPUT_DIR = "outputs"


def main():
    print("=" * 60)
    print("프로모션 자동화 시작")
    print("=" * 60)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    beeflow = None

    try:
        # Step 1: 구글 시트 읽기 (K~R열)
        print("[1/4] 구글 시트 데이터 읽기...")
        df_input = read_discount_sheet(GOOGLE_SHEET_URL, GOOGLE_CREDENTIALS_PATH)
        print(f"✓ {len(df_input)}개 행 읽음\n")

        # Step 2: 비플로우 채널 정보 조회 (내부 API)
        print("[2/4] 비플로우 상품 조회 (내부 API)...")
        beeflow = BeeflowClient(api_base_url=BEEFLOW_API_BASE_URL)

        # 처리 필요한 상품 추출 (설정일이 없는 것)
        products_to_query = df_input[df_input["설정일"].isna()]["상품번호"].unique()
        print(f"조회 필요 상품: {len(products_to_query)}개")

        # 채널 매핑 조회
        channel_mappings = beeflow.query_products(products_to_query)
        print(f"✓ 채널 매핑 완료\n")

        # Step 3: 데이터 변환 및 확장
        print("[3/4] 데이터 변환...")
        df_output = process_promotion_data(df_input, channel_mappings)
        print(f"✓ {len(df_output)}개 행 생성\n")

        # Step 4: 엑셀 파일 생성
        print("[4/4] 엑셀 파일 생성...")
        output_file = generate_upload_file(df_output, OUTPUT_DIR)
        print(f"✓ 파일 생성 완료: {output_file}\n")

        print("=" * 60)
        print("✅ 작업 완료")
        print("=" * 60)
        print(f"출력 파일: {output_file}")
        print(f"총 행 수: {len(df_output)}")
        print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ 오류 발생")
        print("=" * 60)
        print(f"오류 내용: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        # API 전용 BeeflowClient는 종료할 리소스가 없지만,
        # 혹시 close()가 구현되어 있으면 안전하게 호출
        if beeflow and hasattr(beeflow, "close"):
            try:
                beeflow.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
