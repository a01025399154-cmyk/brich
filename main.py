#!/usr/bin/env python3
"""
프로모션 자동화 (수정: Resume 위치 + continue_on_failure)
"""

import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Optional

import config
from modules.sheets import read_sheet, update_setting_dates
from modules.product_hybrid import HybridProductClient
from modules.processor import process_product_promotion, process_brand_promotion
from modules.excel import generate_upload_files


# ==================== 상태 관리 ====================

def load_upload_status(status_file: str) -> Optional[Dict]:
    if not os.path.exists(status_file):
        return None
    try:
        with open(status_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  상태 파일 로드 실패: {e}")
        return None


def save_upload_status(status_file: str, files_status: Dict):
    data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "files": files_status
    }
    try:
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️  상태 파일 저장 실패: {e}")


def update_upload_status(status_file: str, filename: str, file_type: str, 
                         success: bool, error_msg: str = ""):
    status_data = load_upload_status(status_file)
    
    if not status_data:
        status_data = {"last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "files": {}}
    
    if "files" not in status_data:
        status_data["files"] = {}
    
    file_info = status_data["files"].get(filename, {"attempts": 0})
    
    file_info["type"] = file_type
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
    
    save_upload_status(status_file, status_data["files"])


def smart_resume(output_dir: str) -> Dict:
    """모든 미완료 작업 감지"""
    status_file = os.path.join(output_dir, "upload_status.json")
    status_data = load_upload_status(status_file)
    
    if not status_data:
        return {"action": "restart"}
    
    pending_uploads = {"product": [], "brand": []}
    
    for filename, info in status_data.get("files", {}).items():
        status = info.get("status")
        # ✅ failed 또는 pending 모두 미완료로 처리
        if status in ["failed", "pending"]:
            file_type = info.get("type", "unknown")
            filepath = os.path.join(output_dir, filename)
            
            if os.path.exists(filepath) and file_type in ["product", "brand"]:
                pending_uploads[file_type].append(filepath)
    
    total_pending = len(pending_uploads["product"]) + len(pending_uploads["brand"])
    
    if total_pending == 0:
        print(f"✓ 이전 업로드 모두 성공")
        print(f"  상태 파일 삭제\n")
        try:
            os.remove(status_file)
        except:
            pass
        return {"action": "restart"}
    
    print("\n" + "=" * 60)
    print("⚠️  미완료 작업 발견")
    print("=" * 60)
    
    if pending_uploads["product"]:
        print(f"\n📦 상품: {len(pending_uploads['product'])}개")
        for f in pending_uploads["product"]:
            filename = os.path.basename(f)
            info = status_data["files"].get(filename, {})
            status = info.get("status", "unknown")
            status_text = "⏸️ 중단됨" if status == "pending" else f"❌ {info.get('last_error', '실패')}"
            print(f"  - {filename}")
            print(f"    {status_text} (시도: {info.get('attempts', 0)}회)")
    
    if pending_uploads["brand"]:
        print(f"\n🏷️  브랜드: {len(pending_uploads['brand'])}개")
        for f in pending_uploads["brand"]:
            filename = os.path.basename(f)
            info = status_data["files"].get(filename, {})
            status = info.get("status", "unknown")
            status_text = "⏸️ 중단됨" if status == "pending" else f"❌ {info.get('last_error', '실패')}"
            print(f"  - {filename}")
            print(f"    {status_text} (시도: {info.get('attempts', 0)}회)")
    
    print("\n" + "=" * 60)
    
    while True:
        choice = input("\n[1] 미업로드만 재시도  [2] 처음부터: ").strip()
        if choice == "1":
            return {"action": "resume", "pending_uploads": pending_uploads}
        elif choice == "2":
            try:
                os.remove(status_file)
            except:
                pass
            return {"action": "restart"}


# ==================== 업로드 ====================

def upload_with_status_tracking(output_files: List[str], output_dir: str, 
                                email: str, password: str):
    """업로드 (실패해도 계속 진행)"""
    from modules.uploader import BeeflowUploader
    
    status_file = os.path.join(output_dir, "upload_status.json")
    
    initial_status = {}
    for file_path in output_files:
        filename = os.path.basename(file_path)
        file_type = "brand" if "브랜드" in filename else "product"
        initial_status[filename] = {"type": file_type, "status": "pending", "attempts": 0}
    
    existing = load_upload_status(status_file)
    if existing and "files" in existing:
        for fname, finfo in existing["files"].items():
            if fname not in initial_status:
                initial_status[fname] = finfo
    
    save_upload_status(status_file, initial_status)
    
    print("\n" + "=" * 60)
    print("업로드 시작")
    print("=" * 60)
    
    uploader = BeeflowUploader(email, password)
    
    try:
        uploader.init_driver()
        uploader.login()
        
        total = len(output_files)
        success_count = 0
        failed_count = 0

        for idx, file_path in enumerate(output_files, start=1):
            filename = os.path.basename(file_path)
            print(f"[{idx}/{total}] {filename}", end=" ", flush=True)

            try:
                name_without_ext = filename.replace('.xlsx', '')
                parts = name_without_ext.split('_')
                
                if len(parts) < 3:
                    raise ValueError(f"파일명 형식 오류")
                
                date_range = parts[0]
                dates = date_range.split('-')
                start_date = datetime.strptime('20' + dates[0], '%Y%m%d')
                end_date = datetime.strptime('20' + dates[1], '%Y%m%d')
                
                raw_type = parts[1]
                promotion_type = "brand" if "브랜드" in raw_type else "product"
                channel_name = parts[2]
                
                # 진행 단계 표시
                print("→ 페이지 로딩", end="", flush=True)
                time.sleep(0.3)
                print(" → 날짜 설정", end="", flush=True)
                
                ok = uploader.upload_promotion(
                    file_path=file_path,
                    channel_name=channel_name,
                    start_date=start_date,
                    end_date=end_date,
                    promotion_type=promotion_type,
                )

                if ok:
                    success_count += 1
                    update_upload_status(status_file, filename, promotion_type, True)
                    print(" → ✅ 완료")
                else:
                    failed_count += 1
                    update_upload_status(status_file, filename, promotion_type, False, "업로드 실패")
                    print(" → ❌ 실패")
            
            except Exception as e:
                failed_count += 1
                file_type = "brand" if "브랜드" in filename else "product"
                update_upload_status(status_file, filename, file_type, False, str(e))
                print(f" → ❌ 예외: {e}")
        
        print("\n" + "=" * 60)
        print("업로드 요약")
        print("-" * 60)
        print(f"총 대상: {total}개")
        print(f"성공: {success_count}개")
        print(f"실패: {failed_count}개")
        
        if failed_count > 0:
            print("\n💡 재실행 시 실패 파일만 재시도")
        
        print("=" * 60)
        
    finally:
        import time
        time.sleep(1)
        uploader.close()


# ==================== 메인 함수 ====================

def select_sheet_name():
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(config.GOOGLE_CREDENTIALS_PATH, scopes=scopes)
    client = gspread.authorize(creds)

    sheet_id = config.GOOGLE_SHEET_URL.split('/d/')[1].split('/')[0]
    spreadsheet = client.open_by_key(sheet_id)
    worksheets = spreadsheet.worksheets()

    print("\n" + "=" * 60)
    print("📋 시트 목록")
    print("=" * 60)
    for idx, ws in enumerate(worksheets, start=1):
        print(f"{idx}. {ws.title}")
    print("=" * 60)

    while True:
        choice = input(f"\n시트 번호 (1-{len(worksheets)}): ").strip()
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(worksheets):
                selected = worksheets[idx - 1]
                print(f"\n✅ '{selected.title}' 선택\n")
                return selected.title


def run_product_promotion(sheet_name=None, skip_upload_prompt=False, resume_mode=False):
    """상품 프로모션"""
    if not resume_mode:
        print("=" * 60)
        print("상품 프로모션")
        print("=" * 60)
    
    hybrid_client = None
    selected_sheet_name = sheet_name

    try:
        print("[1/5] 시트 읽기...")
        if sheet_name:
            df_input = read_sheet(config.GOOGLE_SHEET_URL, config.GOOGLE_CREDENTIALS_PATH,
                                column_range="K:R", column_mapping=config.PRODUCT_COLUMNS,
                                interactive=False, sheet_name=sheet_name)
        else:
            df_input = read_sheet(config.GOOGLE_SHEET_URL, config.GOOGLE_CREDENTIALS_PATH,
                                column_range="K:R", column_mapping=config.PRODUCT_COLUMNS,
                                interactive=True)
            if 'gid=' in config.GOOGLE_SHEET_URL:
                import gspread
                from google.oauth2.service_account import Credentials
                scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
                creds = Credentials.from_service_account_file(config.GOOGLE_CREDENTIALS_PATH, scopes=scopes)
                client = gspread.authorize(creds)
                sheet_id = config.GOOGLE_SHEET_URL.split('/d/')[1].split('/')[0]
                spreadsheet = client.open_by_key(sheet_id)
                gid = config.GOOGLE_SHEET_URL.split('gid=')[1].split('&')[0].split('#')[0]
                worksheet = spreadsheet.get_worksheet_by_id(int(gid))
                selected_sheet_name = worksheet.title

        print(f"✓ {len(df_input)}개\n")

        print("[2/5] 상품 조회...")
        hybrid_client = HybridProductClient(config.BEEFLOW_API_BASE_URL,
                                           config.BEEFLOW_EMAIL, config.BEEFLOW_PASSWORD)
        products_to_query = df_input[df_input["설정일"].isna()]["상품번호"].unique()
        channel_mappings = hybrid_client.query_products(products_to_query)
        print(f"✓ 완료\n")

        print("[3/5] 변환...")
        df_output = process_product_promotion(df_input, channel_mappings)
        print(f"✓ {len(df_output)}개\n")

        print("[4/5] 파일 생성...")
        output_files = generate_upload_files(df_output, config.OUTPUT_DIR, "상품")
        print(f"✓ {len(output_files)}개\n")

        upload_success = False
        if output_files:
            print("[5/5] 업로드...")
            
            if not skip_upload_prompt:
                response = input("업로드? (y/n): ").strip().lower()
            else:
                response = 'y'
            
            if response in ['y', 'yes']:
                upload_with_status_tracking(output_files, config.OUTPUT_DIR,
                                           config.BEEFLOW_EMAIL, config.BEEFLOW_PASSWORD)
                upload_success = True

        if upload_success and len(products_to_query) > 0:
            update_setting_dates(config.GOOGLE_SHEET_URL, config.GOOGLE_CREDENTIALS_PATH,
                               products_to_query.tolist(), "M", "R", selected_sheet_name)

        print("\n✅ 완료")
        
    except KeyboardInterrupt:
        print("\n❌ 중단")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if hybrid_client:
            hybrid_client.close()


def run_brand_promotion(sheet_name=None, skip_upload_prompt=False, resume_mode=False):
    """브랜드 프로모션"""
    if not resume_mode:
        print("=" * 60)
        print("브랜드 프로모션")
        print("=" * 60)
    
    selected_sheet_name = sheet_name

    try:
        print("[1/4] 시트 읽기...")
        if sheet_name:
            df_input = read_sheet(config.GOOGLE_SHEET_URL, config.GOOGLE_CREDENTIALS_PATH,
                                column_range="A:I", column_mapping=config.BRAND_COLUMNS,
                                start_row=3, interactive=False, sheet_name=sheet_name)
        else:
            df_input = read_sheet(config.GOOGLE_SHEET_URL, config.GOOGLE_CREDENTIALS_PATH,
                                column_range="A:I", column_mapping=config.BRAND_COLUMNS,
                                start_row=3, interactive=True)
            if 'gid=' in config.GOOGLE_SHEET_URL:
                import gspread
                from google.oauth2.service_account import Credentials
                scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
                creds = Credentials.from_service_account_file(config.GOOGLE_CREDENTIALS_PATH, scopes=scopes)
                client = gspread.authorize(creds)
                sheet_id = config.GOOGLE_SHEET_URL.split('/d/')[1].split('/')[0]
                spreadsheet = client.open_by_key(sheet_id)
                gid = config.GOOGLE_SHEET_URL.split('gid=')[1].split('&')[0].split('#')[0]
                worksheet = spreadsheet.get_worksheet_by_id(int(gid))
                selected_sheet_name = worksheet.title

        print(f"✓ {len(df_input)}개\n")

        print("[2/4] 변환...")
        df_output = process_brand_promotion(df_input)
        print(f"✓ {len(df_output)}개\n")

        print("[3/4] 파일 생성...")
        output_files = generate_upload_files(df_output, config.OUTPUT_DIR, "브랜드")
        print(f"✓ {len(output_files)}개\n")

        upload_success = False
        if output_files:
            print("[4/4] 업로드...")
            
            if not skip_upload_prompt:
                response = input("업로드? (y/n): ").strip().lower()
            else:
                response = 'y'
            
            if response in ['y', 'yes']:
                upload_with_status_tracking(output_files, config.OUTPUT_DIR,
                                           config.BEEFLOW_EMAIL, config.BEEFLOW_PASSWORD)
                upload_success = True

        brands_to_update = df_input[df_input["설정일"].isna()]["브랜드번호"].unique()
        if upload_success and len(brands_to_update) > 0:
            update_setting_dates(config.GOOGLE_SHEET_URL, config.GOOGLE_CREDENTIALS_PATH,
                               brands_to_update.tolist(), "C", "I", selected_sheet_name)

        print("\n✅ 완료")
        
    except KeyboardInterrupt:
        print("\n❌ 중단")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run_both_promotions():
    """통합 실행 (Resume 지원)"""
    print("=" * 60)
    print("통합: 상품 + 브랜드")
    print("=" * 60)
    
    sheet_name = select_sheet_name()
    
    print("\n[1단계] 상품\n")
    run_product_promotion(sheet_name=sheet_name, skip_upload_prompt=True, resume_mode=True)
    
    print("\n[2단계] 브랜드\n")
    run_brand_promotion(sheet_name=sheet_name, skip_upload_prompt=True, resume_mode=True)
    
    print("\n✅ 통합 완료")


def main():
    """메인"""
    # ✅ Resume 체크 먼저
    resume_info = smart_resume(config.OUTPUT_DIR)
    
    if resume_info["action"] == "resume":
        pending = resume_info["pending_uploads"]
        
        # 업로드 성공 여부 추적
        upload_success = {"product": False, "brand": False}
        
        if pending["product"]:
            print(f"\n📦 상품 {len(pending['product'])}개 재시도\n")
            upload_with_status_tracking(pending["product"], config.OUTPUT_DIR,
                                       config.BEEFLOW_EMAIL, config.BEEFLOW_PASSWORD)
            
            # 업로드 성공 확인
            status_file = os.path.join(config.OUTPUT_DIR, "upload_status.json")
            status_data = load_upload_status(status_file)
            if status_data:
                product_files = [os.path.basename(f) for f in pending["product"]]
                all_success = all(
                    status_data["files"].get(fname, {}).get("status") == "success"
                    for fname in product_files
                )
                upload_success["product"] = all_success
        
        if pending["brand"]:
            print(f"\n🏷️  브랜드 {len(pending['brand'])}개 재시도\n")
            upload_with_status_tracking(pending["brand"], config.OUTPUT_DIR,
                                       config.BEEFLOW_EMAIL, config.BEEFLOW_PASSWORD)
            
            # 업로드 성공 확인
            status_file = os.path.join(config.OUTPUT_DIR, "upload_status.json")
            status_data = load_upload_status(status_file)
            if status_data:
                brand_files = [os.path.basename(f) for f in pending["brand"]]
                all_success = all(
                    status_data["files"].get(fname, {}).get("status") == "success"
                    for fname in brand_files
                )
                upload_success["brand"] = all_success
        
        # ✅ 설정일 업데이트
        if upload_success["product"] or upload_success["brand"]:
            print("\n📝 구글 시트 설정일 업데이트 중...")
            
            # 시트 선택
            sheet_name = select_sheet_name()
            
            if upload_success["product"]:
                try:
                    # 상품 설정일 업데이트
                    df_input = read_sheet(
                        config.GOOGLE_SHEET_URL,
                        config.GOOGLE_CREDENTIALS_PATH,
                        column_range="K:R",
                        column_mapping=config.PRODUCT_COLUMNS,
                        interactive=False,
                        sheet_name=sheet_name
                    )
                    products_to_update = df_input[df_input["설정일"].isna()]["상품번호"].unique()
                    if len(products_to_update) > 0:
                        update_setting_dates(
                            config.GOOGLE_SHEET_URL,
                            config.GOOGLE_CREDENTIALS_PATH,
                            products_to_update.tolist(),
                            "M", "R", sheet_name
                        )
                except Exception as e:
                    print(f"⚠️  상품 설정일 업데이트 실패: {e}")
            
            if upload_success["brand"]:
                try:
                    # 브랜드 설정일 업데이트
                    df_input = read_sheet(
                        config.GOOGLE_SHEET_URL,
                        config.GOOGLE_CREDENTIALS_PATH,
                        column_range="A:I",
                        column_mapping=config.BRAND_COLUMNS,
                        start_row=3,
                        interactive=False,
                        sheet_name=sheet_name
                    )
                    brands_to_update = df_input[df_input["설정일"].isna()]["브랜드번호"].unique()
                    if len(brands_to_update) > 0:
                        update_setting_dates(
                            config.GOOGLE_SHEET_URL,
                            config.GOOGLE_CREDENTIALS_PATH,
                            brands_to_update.tolist(),
                            "C", "I", sheet_name
                        )
                except Exception as e:
                    print(f"⚠️  브랜드 설정일 업데이트 실패: {e}")
        
        print("\n✅ Resume 완료")
        return
    
    # ✅ 모드 선택
    print("=" * 60)
    print("프로모션 자동화")
    print("=" * 60)
    print("1. 상품")
    print("2. 브랜드")
    print("3. 통합")
    print("=" * 60)
    
    while True:
        choice = input("\n선택 (1-3): ").strip()
        
        if choice == "1":
            run_product_promotion()
            break
        elif choice == "2":
            run_brand_promotion()
            break
        elif choice == "3":
            run_both_promotions()
            break


if __name__ == "__main__":
    main()