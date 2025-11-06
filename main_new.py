#!/usr/bin/env python3
"""
프로모션 자동화 메인 스크립트
상품 프로모션과 브랜드 프로모션 지원
"""

import os
import sys
from datetime import datetime

import config
from modules.sheets import read_sheet, update_setting_dates
from modules.product_api import ProductAPIClient
from modules.processor import process_product_promotion, process_brand_promotion
from modules.excel import generate_upload_files
from modules.uploader import upload_promotions


def main():
    """메인 실행 함수 - 인터랙티브 모드"""
    print("=" * 60)
    print("프로모션 자동화")
    print("=" * 60)
    print("1. 상품 프로모션")
    print("2. 브랜드 프로모션")
    print("=" * 60)
    
    while True:
        choice = input("\n선택 (1-2): ").strip()
        
        if choice == "1":
            print("\n✅ 상품 프로모션을 선택했습니다.\n")
            run_product_promotion()
            break
        elif choice == "2":
            print("\n✅ 브랜드 프로모션을 선택했습니다.\n")
            run_brand_promotion()
            break
        else:
            print("❌ 1 또는 2를 입력해주세요.")


def run_product_promotion():
    """상품 프로모션 실행"""
    print("=" * 60)
    print("상품 프로모션 자동화 시작")
    print("=" * 60)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    api_client = None
    selected_sheet_name = None

    try:
        # Step 1: 구글 시트 읽기 (K~R열)
        print("[1/5] 구글 시트 데이터 읽기 (K~R열)...")
        df_input = read_sheet(
            config.GOOGLE_SHEET_URL,
            config.GOOGLE_CREDENTIALS_PATH,
            column_range="K:R",
            column_mapping=config.PRODUCT_COLUMNS,
            interactive=True
        )
        
        # 선택된 시트 이름 저장
        if 'gid=' in config.GOOGLE_SHEET_URL:
            import gspread
            from google.oauth2.service_account import Credentials
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = Credentials.from_service_account_file(config.GOOGLE_CREDENTIALS_PATH, scopes=scopes)
            client = gspread.authorize(creds)
            sheet_id = config.GOOGLE_SHEET_URL.split('/d/')[1].split('/')[0]
            spreadsheet = client.open_by_key(sheet_id)
            gid = config.GOOGLE_SHEET_URL.split('gid=')[1].split('&')[0].split('#')[0]
            worksheet = spreadsheet.get_worksheet_by_id(int(gid))
            selected_sheet_name = worksheet.title
        
        print(f"✓ {len(df_input)}개 행 읽음\n")

        # Step 2: 비플로우 채널 정보 조회 (내부 API)
        print("[2/5] 비플로우 상품 조회 (내부 API)...")
        api_client = ProductAPIClient(api_base_url=config.BEEFLOW_API_BASE_URL)

        products_to_query = df_input[df_input["설정일"].isna()]["상품번호"].unique()
        print(f"조회 필요 상품: {len(products_to_query)}개")

        channel_mappings = api_client.query_products(products_to_query)
        print(f"✓ 채널 매핑 완료\n")

        # Step 3: 데이터 변환
        print("[3/5] 데이터 변환...")
        df_output = process_product_promotion(df_input, channel_mappings)
        print(f"✓ {len(df_output)}개 행 생성\n")

        # Step 4: 채널별 엑셀 파일 생성
        print("[4/5] 채널별 엑셀 파일 생성...")
        output_files = generate_upload_files(df_output, config.OUTPUT_DIR, file_prefix="상품")
        print(f"✓ {len(output_files)}개 파일 생성 완료\n")

        # Step 5: 비플로우 자동 업로드
        upload_success = False
        if output_files:
            print("[5/5] 비플로우 자동 업로드...")
            
            while True:
                response = input("생성된 파일을 비플로우에 업로드하시겠습니까? (y/n): ").strip().lower()
                if response in ['y', 'yes', 'n', 'no']:
                    break
                print("y 또는 n을 입력해주세요.")
            
            if response in ['y', 'yes']:
                try:
                    upload_promotions(
                        output_files=output_files,
                        output_dir=config.OUTPUT_DIR,
                        email=config.BEEFLOW_EMAIL,
                        password=config.BEEFLOW_PASSWORD,
                        promotion_type="product"
                    )
                    upload_success = True
                except Exception as e:
                    print(f"\n⚠️  업로드 중 오류 발생: {e}")
                    upload_success = False
            else:
                print("업로드를 건너뜁니다.\n")
        else:
            print("[5/5] 업로드할 파일이 없습니다.\n")

        # Step 6: 업로드 성공 시 구글 시트 설정일 업데이트
        if upload_success and len(products_to_query) > 0:
            update_setting_dates(
                sheet_url=config.GOOGLE_SHEET_URL,
                credentials_path=config.GOOGLE_CREDENTIALS_PATH,
                ids=products_to_query.tolist(),
                id_column="M",
                setting_column="R",
                sheet_name=selected_sheet_name
            )

        print("=" * 60)
        print("✅ 작업 완료")
        print("=" * 60)
        print(f"출력 디렉토리: {config.OUTPUT_DIR}")
        print(f"생성된 파일 수: {len(output_files)}")
        print(f"총 행 수: {len(df_output)}")
        print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if output_files:
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


def run_brand_promotion():
    """브랜드 프로모션 실행"""
    print("=" * 60)
    print("브랜드 프로모션 자동화 시작")
    print("=" * 60)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    selected_sheet_name = None

    try:
        # Step 1: 구글 시트 읽기 (A~I열)
        print("[1/4] 구글 시트 데이터 읽기 (A~I열)...")
        df_input = read_sheet(
            config.GOOGLE_SHEET_URL,
            config.GOOGLE_CREDENTIALS_PATH,
            column_range="A:I",
            column_mapping=config.BRAND_COLUMNS,
            start_row=3,  # 브랜드는 3행부터 시작
            interactive=True
        )
        
        # 선택된 시트 이름 저장
        if 'gid=' in config.GOOGLE_SHEET_URL:
            import gspread
            from google.oauth2.service_account import Credentials
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = Credentials.from_service_account_file(config.GOOGLE_CREDENTIALS_PATH, scopes=scopes)
            client = gspread.authorize(creds)
            sheet_id = config.GOOGLE_SHEET_URL.split('/d/')[1].split('/')[0]
            spreadsheet = client.open_by_key(sheet_id)
            gid = config.GOOGLE_SHEET_URL.split('gid=')[1].split('&')[0].split('#')[0]
            worksheet = spreadsheet.get_worksheet_by_id(int(gid))
            selected_sheet_name = worksheet.title
        
        print(f"✓ {len(df_input)}개 행 읽음\n")

        # Step 2: 데이터 변환 (API 조회 없음)
        print("[2/4] 데이터 변환...")
        df_output = process_brand_promotion(df_input)
        print(f"✓ {len(df_output)}개 행 생성\n")

        # Step 3: 채널별 엑셀 파일 생성
        print("[3/4] 채널별 엑셀 파일 생성...")
        output_files = generate_upload_files(df_output, config.OUTPUT_DIR, file_prefix="브랜드")
        print(f"✓ {len(output_files)}개 파일 생성 완료\n")

        # Step 4: 비플로우 자동 업로드
        upload_success = False
        if output_files:
            print("[4/4] 비플로우 자동 업로드...")
            
            while True:
                response = input("생성된 파일을 비플로우에 업로드하시겠습니까? (y/n): ").strip().lower()
                if response in ['y', 'yes', 'n', 'no']:
                    break
                print("y 또는 n을 입력해주세요.")
            
            if response in ['y', 'yes']:
                try:
                    upload_promotions(
                        output_files=output_files,
                        output_dir=config.OUTPUT_DIR,
                        email=config.BEEFLOW_EMAIL,
                        password=config.BEEFLOW_PASSWORD,
                        promotion_type="brand"
                    )
                    upload_success = True
                except Exception as e:
                    print(f"\n⚠️  업로드 중 오류 발생: {e}")
                    upload_success = False
            else:
                print("업로드를 건너뜁니다.\n")
        else:
            print("[4/4] 업로드할 파일이 없습니다.\n")

        # Step 5: 업로드 성공 시 구글 시트 설정일 업데이트
        brands_to_update = df_input[df_input["설정일"].isna()]["브랜드번호"].unique()
        if upload_success and len(brands_to_update) > 0:
            update_setting_dates(
                sheet_url=config.GOOGLE_SHEET_URL,
                credentials_path=config.GOOGLE_CREDENTIALS_PATH,
                ids=brands_to_update.tolist(),
                id_column="C",
                setting_column="I",
                sheet_name=selected_sheet_name
            )

        print("=" * 60)
        print("✅ 작업 완료")
        print("=" * 60)
        print(f"출력 디렉토리: {config.OUTPUT_DIR}")
        print(f"생성된 파일 수: {len(output_files)}")
        print(f"총 행 수: {len(df_output)}")
        print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if output_files:
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


if __name__ == "__main__":
    main()