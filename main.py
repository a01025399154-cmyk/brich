#!/usr/bin/env python3
"""
프로모션 자동화 메인 스크립트 (개선 버전)
구글 시트 K~R열 읽기 (시트 선택 가능) → 비플로우 조회 (내부 API) → 채널별 엑셀 파일 생성
"""

import os
import sys
from datetime import datetime

from modules.google_sheet import read_discount_sheet, get_sheet_list
from modules.bflow import BeeflowClient
from modules.data_processor import process_promotion_data
from modules.excel_generator import generate_upload_files

# 설정
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1Ca-AXLDXIpyb_N_9AvI_2fT5g-jMEDYlv233mbkRdVs/edit?gid=737496399#gid=737496399"
GOOGLE_CREDENTIALS_PATH = "inner-sale-979c1e8ed412.json"

# 비플로우 내부 API 베이스 URL
BEEFLOW_API_BASE_URL = "http://192.168.0.10:10645"

OUTPUT_DIR = "outputs"


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("프로모션 자동화 시작")
    print("=" * 60)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    beeflow = None

    try:
        # Step 0: 시트 선택 (인터랙티브)
        print("[0/4] 구글 시트 선택...")
        
        # 사용자에게 시트 목록 보여주고 선택하도록 함
        # interactive=True로 설정하면 자동으로 선택 메뉴가 나타남
        
        # Step 1: 구글 시트 읽기 (K~R열)
        print("\n[1/4] 구글 시트 데이터 읽기...")
        df_input = read_discount_sheet(
            GOOGLE_SHEET_URL, 
            GOOGLE_CREDENTIALS_PATH,
            interactive=True  # 인터랙티브 시트 선택 활성화
        )
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

        # Step 4: 채널별 엑셀 파일 생성
        print("[4/4] 채널별 엑셀 파일 생성...")
        output_files = generate_upload_files(df_output, OUTPUT_DIR)
        print(f"✓ {len(output_files)}개 파일 생성 완료\n")

        print("=" * 60)
        print("✅ 작업 완료")
        print("=" * 60)
        print(f"출력 디렉토리: {OUTPUT_DIR}")
        print(f"생성된 파일 수: {len(output_files)}")
        print(f"총 행 수: {len(df_output)}")
        print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n생성된 파일 목록:")
        for file_path in output_files:
            filename = os.path.basename(file_path)
            print(f"  - {filename}")

    except KeyboardInterrupt:
        print("\n\n❌ 사용자에 의해 중단되었습니다.")
        sys.exit(1)
        
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


def main_with_sheet_name(sheet_name=None):
    """
    특정 시트를 지정하여 실행 (자동화용)
    
    Args:
        sheet_name: 읽을 시트 이름 (None이면 URL의 gid 또는 첫 번째 시트)
    """
    print("=" * 60)
    print("프로모션 자동화 시작 (자동 모드)")
    print("=" * 60)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    beeflow = None

    try:
        # Step 1: 구글 시트 읽기 (K~R열)
        print("[1/4] 구글 시트 데이터 읽기...")
        df_input = read_discount_sheet(
            GOOGLE_SHEET_URL, 
            GOOGLE_CREDENTIALS_PATH,
            sheet_name=sheet_name,
            interactive=False  # 자동 모드
        )
        print(f"✓ {len(df_input)}개 행 읽음\n")

        # Step 2: 비플로우 채널 정보 조회 (내부 API)
        print("[2/4] 비플로우 상품 조회 (내부 API)...")
        beeflow = BeeflowClient(api_base_url=BEEFLOW_API_BASE_URL)

        products_to_query = df_input[df_input["설정일"].isna()]["상품번호"].unique()
        print(f"조회 필요 상품: {len(products_to_query)}개")

        channel_mappings = beeflow.query_products(products_to_query)
        print(f"✓ 채널 매핑 완료\n")

        # Step 3: 데이터 변환 및 확장
        print("[3/4] 데이터 변환...")
        df_output = process_promotion_data(df_input, channel_mappings)
        print(f"✓ {len(df_output)}개 행 생성\n")

        # Step 4: 채널별 엑셀 파일 생성
        print("[4/4] 채널별 엑셀 파일 생성...")
        output_files = generate_upload_files(df_output, OUTPUT_DIR)
        print(f"✓ {len(output_files)}개 파일 생성 완료\n")

        print("=" * 60)
        print("✅ 작업 완료")
        print("=" * 60)
        print(f"출력 디렉토리: {OUTPUT_DIR}")
        print(f"생성된 파일 수: {len(output_files)}")
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
        if beeflow and hasattr(beeflow, "close"):
            try:
                beeflow.close()
            except Exception:
                pass


if __name__ == "__main__":
    # 명령줄 인자가 있으면 해당 시트 이름으로 자동 실행
    if len(sys.argv) > 1:
        sheet_name = sys.argv[1]
        print(f"📋 지정된 시트: {sheet_name}\n")
        main_with_sheet_name(sheet_name)
    else:
        # 인자가 없으면 인터랙티브 모드
        main()