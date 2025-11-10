#!/usr/bin/env python3
"""
프로모션 자동화 메인 스크립트 (재시도 로직 + 하이브리드 API)
상품 프로모션과 브랜드 프로모션 지원
"""

import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Optional

import config
from modules.sheets import read_sheet, update_setting_dates
from modules.product_hybrid import HybridProductClient  # ✅ 변경
from modules.processor import process_product_promotion, process_brand_promotion
from modules.excel import generate_upload_files
from modules.uploader import upload_promotions


# ==================== 상태 관리 함수 ====================

def load_upload_status(status_file: str) -> Optional[Dict]:
    """업로드 상태 파일 로드"""
    if not os.path.exists(status_file):
        return None
    
    try:
        with open(status_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  상태 파일 로드 실패: {e}")
        return None


def get_failed_files(status_data: Dict, output_dir: str) -> List[str]:
    """실패한 파일 목록 반환 (실제 파일 존재 확인)"""
    if not status_data or "files" not in status_data:
        return []
    
    failed_files = []
    for filename, info in status_data["files"].items():
        if info.get("status") == "failed":
            filepath = os.path.join(output_dir, filename)
            if os.path.exists(filepath):
                failed_files.append(filepath)
    
    return failed_files


def save_upload_status(status_file: str, mode: str, files_status: Dict):
    """업로드 상태 저장"""
    data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": mode,
        "files": files_status
    }
    
    try:
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✓ 상태 파일 저장: {status_file}")
    except Exception as e:
        print(f"⚠️  상태 파일 저장 실패: {e}")


def update_upload_status(status_file: str, filename: str, success: bool, error_msg: str = ""):
    """개별 파일 업로드 상태 업데이트"""
    status_data = load_upload_status(status_file)
    
    if not status_data:
        status_data = {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "mode": "unknown",
            "files": {}
        }
    
    if "files" not in status_data:
        status_data["files"] = {}
    
    file_info = status_data["files"].get(filename, {"attempts": 0})
    
    file_info["status"] = "success" if success else "failed"
    file_info["attempts"] = file_info.get("attempts", 0) + 1
    file_info["last_attempt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if success:
        file_info["uploaded_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if "last_error" in file_info:
            del file_info["last_error"]
    else:
        file_info["last_error"] = error_msg
    
    status_data["files"][filename] = file_info
    status_data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    save_upload_status(status_file, status_data.get("mode", "unknown"), status_data["files"])


def check_and_prompt_retry(output_dir: str) -> Optional[List[str]]:
    """
    자동 감지: 실패한 파일이 있으면 재시도 여부 확인
    
    Returns:
        List[str]: 재시도할 파일 목록 (None이면 전체 과정 진행)
    """
    status_file = os.path.join(output_dir, "upload_status.json")
    status_data = load_upload_status(status_file)
    
    if not status_data:
        # 상태 파일 없음 → 전체 과정 진행
        return None
    
    failed_files = get_failed_files(status_data, output_dir)
    
    if not failed_files:
        # 실패 파일 없음 → 상태 파일 삭제 후 전체 과정 진행
        print(f"✓ 이전 업로드가 모두 성공했습니다.")
        print(f"  상태 파일을 삭제하고 새로 시작합니다.\n")
        try:
            os.remove(status_file)
        except:
            pass
        return None
    
    # 실패 파일 있음 → 재시도 여부 확인
    print("\n" + "=" * 60)
    print("⚠️  이전 업로드 중 실패한 파일이 발견되었습니다")
    print("=" * 60)
    print(f"실패 파일 수: {len(failed_files)}")
    print("\n실패한 파일 목록:")
    for filepath in failed_files:
        filename = os.path.basename(filepath)
        file_info = status_data["files"].get(filename, {})
        attempts = file_info.get("attempts", 0)
        last_error = file_info.get("last_error", "알 수 없음")
        print(f"  - {filename}")
        print(f"    시도 횟수: {attempts}회 | 마지막 오류: {last_error}")
    
    print("=" * 60)
    
    while True:
        response = input("\n실패한 파일만 재시도하시겠습니까? (y: 재시도, n: 처음부터 다시): ").strip().lower()
        
        if response in ['y', 'yes']:
            print("\n✅ 실패한 파일만 재업로드합니다.\n")
            return failed_files
        
        elif response in ['n', 'no']:
            print("\n✅ 상태 파일을 삭제하고 전체 과정을 새로 시작합니다.\n")
            try:
                os.remove(status_file)
            except:
                pass
            return None
        
        else:
            print("y 또는 n을 입력해주세요.")


# ==================== 업로드 래퍼 함수 ====================

def upload_with_status_tracking(output_files: List[str], output_dir: str, 
                                email: str, password: str, mode: str):
    """
    상태 추적을 포함한 업로드 함수
    
    Args:
        output_files: 업로드할 파일 목록
        output_dir: 출력 디렉토리
        email: 로그인 이메일
        password: 로그인 비밀번호
        mode: "product", "brand", "both"
    """
    from modules.uploader import BeeflowUploader
    
    status_file = os.path.join(output_dir, "upload_status.json")
    
    # 초기 상태 저장
    initial_status = {filename: {"status": "pending", "attempts": 0} 
                     for filename in [os.path.basename(f) for f in output_files]}
    save_upload_status(status_file, mode, initial_status)
    
    print("\n" + "=" * 60)
    print("비플로우 자동 업로드 시작 (상태 추적 모드)")
    print("=" * 60)
    
    uploader = BeeflowUploader(email, password)
    
    try:
        uploader.init_driver()
        uploader.login()
        
        total = len(output_files)
        success_count = 0
        processed_count = 0

        for idx, file_path in enumerate(output_files, start=1):
            filename = os.path.basename(file_path)
            print("\n" + "-" * 60)
            print(f"[{idx}/{total}] 파일 처리 시작: {filename}")

            try:
                name_without_ext = filename.replace('.xlsx', '')
                parts = name_without_ext.split('_')
                
                if len(parts) < 3:
                    raise ValueError(f"파일명 형식이 예상과 다릅니다: {filename}")
                
                # 날짜 범위
                date_range = parts[0]
                dates = date_range.split('-')
                if len(dates) != 2:
                    raise ValueError(f"날짜 구간 형식이 잘못되었습니다: {date_range}")
                
                start_date = datetime.strptime('20' + dates[0], '%Y%m%d')
                end_date = datetime.strptime('20' + dates[1], '%Y%m%d')
                
                # 프로모션 타입
                raw_type = parts[1]
                if "브랜드" in raw_type:
                    promotion_type = "brand"
                else:
                    promotion_type = "product"
                
                # 채널명
                channel_name = parts[2]
                
                print(f"  - 유형: {raw_type} → {promotion_type}")
                print(f"  - 채널: {channel_name}")

                ok = uploader.upload_promotion(
                    file_path=file_path,
                    channel_name=channel_name,
                    start_date=start_date,
                    end_date=end_date,
                    promotion_type=promotion_type,
                )

                processed_count += 1

                if ok:
                    success_count += 1
                    update_upload_status(status_file, filename, success=True)
                    print(f"[{idx}/{total}] ✅ 성공: {filename}")
                else:
                    update_upload_status(status_file, filename, success=False, 
                                       error_msg="업로드 실패 (재시도 횟수 초과)")
                    print(f"[{idx}/{total}] ❌ 실패: {filename}")
                    print("\n‼ 첫 업로드 실패 발생 → 이후 작업을 중단합니다.")
                    break
            
            except Exception as e:
                processed_count += 1
                update_upload_status(status_file, filename, success=False, 
                                   error_msg=str(e))
                print(f"[{idx}/{total}] ❌ 예외로 실패: {filename}")
                print(f"  - 원인: {e}")
                print("\n‼ 예외 발생으로 인해 이후 작업을 중단합니다.")
                break
        
        print("\n" + "=" * 60)
        print("업로드 작업 요약")
        print("-" * 60)
        print(f"총 대상 파일 수 : {total}")
        print(f"처리한 파일 수 : {processed_count}")
        print(f"성공한 파일 수 : {success_count}")
        print(f"실패한 파일 수 : {processed_count - success_count}")
        if processed_count < total:
            print("※ 중간에 실패가 발생하여 남은 파일은 처리하지 않았습니다.")
            print(f"※ 다시 실행하면 실패한 파일부터 재시도할 수 있습니다.")
        print("=" * 60)
        
    finally:
        import time
        time.sleep(1)
        uploader.close()


# ==================== 기존 함수들 (수정) ====================

def select_sheet_name():
    """시트 선택 (통합 실행용)"""
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = Credentials.from_service_account_file(config.GOOGLE_CREDENTIALS_PATH, scopes=scopes)
    client = gspread.authorize(creds)

    if "/d/" not in config.GOOGLE_SHEET_URL:
        raise ValueError("GOOGLE_SHEET_URL에서 스프레드시트 ID를 찾을 수 없습니다.")

    sheet_id = config.GOOGLE_SHEET_URL.split('/d/')[1].split('/')[0]
    spreadsheet = client.open_by_key(sheet_id)

    worksheets = spreadsheet.worksheets()

    print("\n" + "=" * 60)
    print("📋 사용 가능한 시트 목록")
    print("=" * 60)
    for idx, ws in enumerate(worksheets, start=1):
        print(f"{idx}. {ws.title}")
    print("=" * 60)

    while True:
        choice = input(f"\n시트 번호를 선택하세요 (1-{len(worksheets)}): ").strip()
        if not choice.isdigit():
            print("숫자를 입력해주세요.")
            continue

        idx = int(choice)
        if 1 <= idx <= len(worksheets):
            selected_ws = worksheets[idx - 1]
            print(f"\n✅ '{selected_ws.title}' 시트를 선택했습니다.\n")
            return selected_ws.title
        else:
            print(f"1에서 {len(worksheets)} 사이의 번호를 입력해주세요.")


def run_product_promotion(sheet_name=None, skip_upload_prompt=False):
    """상품 프로모션 실행"""
    print("=" * 60)
    print("상품 프로모션 자동화 시작")
    print("=" * 60)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # ==================== 자동 감지 ====================
    retry_files = check_and_prompt_retry(config.OUTPUT_DIR)
    
    if retry_files is not None:
        # 재시도 모드
        print(f"📤 실패한 파일 {len(retry_files)}개를 재업로드합니다.\n")
        
        upload_with_status_tracking(
            output_files=retry_files,
            output_dir=config.OUTPUT_DIR,
            email=config.BEEFLOW_EMAIL,
            password=config.BEEFLOW_PASSWORD,
            mode="product"
        )
        
        print("\n✅ 재업로드 완료")
        return
    
    # ==================== 전체 과정 ====================
    
    hybrid_client = None  # ✅ 변경
    selected_sheet_name = sheet_name

    try:
        # Step 1: 구글 시트 읽기
        print("[1/5] 구글 시트 데이터 읽기 (K~R열)...")

        if sheet_name:
            df_input = read_sheet(
                config.GOOGLE_SHEET_URL,
                config.GOOGLE_CREDENTIALS_PATH,
                column_range="K:R",
                column_mapping=config.PRODUCT_COLUMNS,
                interactive=False,
                sheet_name=sheet_name
            )
        else:
            df_input = read_sheet(
                config.GOOGLE_SHEET_URL,
                config.GOOGLE_CREDENTIALS_PATH,
                column_range="K:R",
                column_mapping=config.PRODUCT_COLUMNS,
                interactive=True
            )

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

        # Step 2: 비플로우 채널 정보 조회 (하이브리드: API + 웹 스크래핑)
        print("[2/5] 비플로우 상품 조회 (하이브리드 방식)...")
        hybrid_client = HybridProductClient(
            api_base_url=config.BEEFLOW_API_BASE_URL,
            email=config.BEEFLOW_EMAIL,
            password=config.BEEFLOW_PASSWORD
        )

        products_to_query = df_input[df_input["설정일"].isna()]["상품번호"].unique()
        print(f"조회 필요 상품: {len(products_to_query)}개")

        channel_mappings = hybrid_client.query_products(products_to_query)  # ✅ 수정
        print(f"✓ 채널 매핑 완료\n")

        # Step 3: 데이터 변환
        print("[3/5] 데이터 변환...")
        df_output = process_product_promotion(df_input, channel_mappings)
        print(f"✓ {len(df_output)}개 행 생성\n")

        # Step 4: 엑셀 파일 생성
        print("[4/5] 채널별 엑셀 파일 생성...")
        output_files = generate_upload_files(df_output, config.OUTPUT_DIR, file_prefix="상품")
        print(f"✓ {len(output_files)}개 파일 생성 완료\n")

        # Step 5: 업로드
        upload_success = False
        if output_files:
            print("[5/5] 비플로우 자동 업로드...")
            
            if not skip_upload_prompt:
                while True:
                    response = input("생성된 파일을 비플로우에 업로드하시겠습니까? (y/n): ").strip().lower()
                    if response in ['y', 'yes', 'n', 'no']:
                        break
                    print("y 또는 n을 입력해주세요.")
            else:
                response = 'y'
            
            if response in ['y', 'yes']:
                try:
                    upload_with_status_tracking(
                        output_files=output_files,
                        output_dir=config.OUTPUT_DIR,
                        email=config.BEEFLOW_EMAIL,
                        password=config.BEEFLOW_PASSWORD,
                        mode="product"
                    )
                    
                    # 업로드 성공 여부 확인
                    status_file = os.path.join(config.OUTPUT_DIR, "upload_status.json")
                    status_data = load_upload_status(status_file)
                    if status_data:
                        failed = get_failed_files(status_data, config.OUTPUT_DIR)
                        upload_success = len(failed) == 0
                    
                except Exception as e:
                    print(f"\n⚠️  업로드 중 오류 발생: {e}")
                    upload_success = False
            else:
                print("업로드를 건너뜁니다.\n")
        else:
            print("[5/5] 업로드할 파일이 없습니다.\n")

        # Step 6: 구글 시트 설정일 업데이트
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
    
    finally:
        # ✅ 리소스 정리
        if hybrid_client:
            hybrid_client.close()


def run_brand_promotion(sheet_name=None, skip_upload_prompt=False):
    """브랜드 프로모션 실행"""
    print("=" * 60)
    print("브랜드 프로모션 자동화 시작")
    print("=" * 60)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # ==================== 자동 감지 ====================
    retry_files = check_and_prompt_retry(config.OUTPUT_DIR)
    
    if retry_files is not None:
        # 재시도 모드
        print(f"📤 실패한 파일 {len(retry_files)}개를 재업로드합니다.\n")
        
        upload_with_status_tracking(
            output_files=retry_files,
            output_dir=config.OUTPUT_DIR,
            email=config.BEEFLOW_EMAIL,
            password=config.BEEFLOW_PASSWORD,
            mode="brand"
        )
        
        print("\n✅ 재업로드 완료")
        return
    
    # ==================== 전체 과정 ====================

    selected_sheet_name = sheet_name

    try:
        # Step 1: 구글 시트 읽기
        print("[1/4] 구글 시트 데이터 읽기 (A~I열)...")

        if sheet_name:
            df_input = read_sheet(
                config.GOOGLE_SHEET_URL,
                config.GOOGLE_CREDENTIALS_PATH,
                column_range="A:I",
                column_mapping=config.BRAND_COLUMNS,
                start_row=3,
                interactive=False,
                sheet_name=sheet_name
            )
        else:
            df_input = read_sheet(
                config.GOOGLE_SHEET_URL,
                config.GOOGLE_CREDENTIALS_PATH,
                column_range="A:I",
                column_mapping=config.BRAND_COLUMNS,
                start_row=3,
                interactive=True
            )
            
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

        # Step 2: 데이터 변환
        print("[2/4] 데이터 변환...")
        df_output = process_brand_promotion(df_input)
        print(f"✓ {len(df_output)}개 행 생성\n")

        # Step 3: 엑셀 파일 생성
        print("[3/4] 채널별 엑셀 파일 생성...")
        output_files = generate_upload_files(df_output, config.OUTPUT_DIR, file_prefix="브랜드")
        print(f"✓ {len(output_files)}개 파일 생성 완료\n")

        # Step 4: 업로드
        upload_success = False
        if output_files:
            print("[4/4] 비플로우 자동 업로드...")
            
            if not skip_upload_prompt:
                while True:
                    response = input("생성된 파일을 비플로우에 업로드하시겠습니까? (y/n): ").strip().lower()
                    if response in ['y', 'yes', 'n', 'no']:
                        break
                    print("y 또는 n을 입력해주세요.")
            else:
                response = 'y'
            
            if response in ['y', 'yes']:
                try:
                    upload_with_status_tracking(
                        output_files=output_files,
                        output_dir=config.OUTPUT_DIR,
                        email=config.BEEFLOW_EMAIL,
                        password=config.BEEFLOW_PASSWORD,
                        mode="brand"
                    )
                    
                    # 업로드 성공 여부 확인
                    status_file = os.path.join(config.OUTPUT_DIR, "upload_status.json")
                    status_data = load_upload_status(status_file)
                    if status_data:
                        failed = get_failed_files(status_data, config.OUTPUT_DIR)
                        upload_success = len(failed) == 0
                    
                except Exception as e:
                    print(f"\n⚠️  업로드 중 오류 발생: {e}")
                    upload_success = False
            else:
                print("업로드를 건너뜁니다.\n")
        else:
            print("[4/4] 업로드할 파일이 없습니다.\n")

        # Step 5: 구글 시트 설정일 업데이트
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


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("프로모션 자동화")
    print("=" * 60)
    print("1. 상품 프로모션")
    print("2. 브랜드 프로모션")
    print("3. 상품 + 브랜드 모두 실행")
    print("=" * 60)
    
    while True:
        choice = input("\n선택 (1-3): ").strip()
        
        if choice == "1":
            print("\n✅ 상품 프로모션을 선택했습니다.\n")
            run_product_promotion()
            break

        elif choice == "2":
            print("\n✅ 브랜드 프로모션을 선택했습니다.\n")
            run_brand_promotion()
            break

        elif choice == "3":
            print("\n✅ 상품 + 브랜드 프로모션을 순차적으로 실행합니다.\n")

            sheet_name = select_sheet_name()

            print("\n[🔹 1단계] 상품 프로모션 실행\n")
            run_product_promotion(sheet_name=sheet_name, skip_upload_prompt=True)

            print("\n[🔹 2단계] 브랜드 프로모션 실행\n")
            run_brand_promotion(sheet_name=sheet_name, skip_upload_prompt=True)
            break

        else:
            print("❌ 1, 2 또는 3을 입력해주세요.")


if __name__ == "__main__":
    main()