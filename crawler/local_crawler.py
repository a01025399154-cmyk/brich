#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
로컬 환경에서 실행하는 GS샵 + 포스티 상품 크롤러
- 구글 스프레드시트 '상품목록'에서 상품명 읽기
- undetected_chromedriver로 두 사이트 검색
- 결과를 다시 스프레드시트에 기록
"""

import os
import re
import time
from datetime import datetime
from typing import Dict, List, Any

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from google.oauth2 import service_account
from googleapiclient.discovery import build
from urllib.parse import urljoin

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 설정
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 네 스프레드시트 ID와 시트 이름
SPREADSHEET_ID = "14Pmvc1I9qAIojNoRETE1UWPqG-n1uK98cdQHm_TbIxU"
SHEET_NAME = "시트1"

SERVICE_ACCOUNT_FILE = os.environ.get(
    "GOOGLE_SA_JSON",
    "service_account.json",  # 환경변수 없으면 기본값
)

# Google Sheets API 스코프
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# 사이트 URL
GSSHOP_URL = "https://www.gsshop.com/"
POSTY_URL = "https://posty.kr"  # 실제 URL 확인 필요


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 유틸 함수
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def to_int(text: str | None) -> int | None:
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def now_kst_str() -> str:
    """크롤링 시점: 문자열로 기록 (간단히 시스템 로컬 시간 기준)"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Google Sheets 관련
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_sheets_service():
    """서비스 계정으로 Sheets API 클라이언트 생성"""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES,
    )
    service = build("sheets", "v4", credentials=credentials)
    return service


def fetch_input_rows(service) -> List[Dict[str, Any]]:
    """
    상품목록 시트에서 '상품명' 컬럼(A열)을 읽어서
    행 번호 + 상품명 리스트로 반환.
    멀티헤더로 1~2행은 헤더, 데이터는 3행부터 있다고 가정.
    """
    # A3:A 범위: 3행부터 끝까지
    range_name = f"{SHEET_NAME}!A3:A"
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=SPREADSHEET_ID, range=range_name)
        .execute()
    )
    values = result.get("values", [])

    rows: List[Dict[str, Any]] = []
    start_row = 3
    for idx, row in enumerate(values, start=start_row):
        name = row[0].strip() if row else ""
        if not name:
            continue
        rows.append({"row_index": idx, "product_name": name})
    return rows


def update_result_row(
    service,
    row_index: int,
    crawl_time: str,
    g: Dict[str, Any],
    p: Dict[str, Any],
):
    """
    하나의 행(B~Q열)을 업데이트.
    - 기존 값은 먼저 모두 지우고(clear) 새 값으로 채움
    - URL은 셀에 직접 넣지 않고 =HYPERLINK("url","링크") 형식으로 넣어서
      화면에는 '링크' 텍스트만 보이게 함
    """
    range_name = f"{SHEET_NAME}!B{row_index}:Q{row_index}"

    # 1) 기존 값 전부 삭제 (B~Q)
    service.spreadsheets().values().clear(
        spreadsheetId=SPREADSHEET_ID,
        range=range_name,
        body={},
    ).execute()

    # 2) None → "" 변환
    def norm(v):
        if v is None:
            return ""
        return v

    # 3) URL → HYPERLINK 함수 문자열로 변환
    def make_link(url: str | None) -> str:
        if not url:
            return ""
        # 따옴표 깨지는 경우를 피하려면 " 만 간단히 이스케이프
        safe_url = str(url).replace('"', '""')
        return f'=HYPERLINK("{safe_url}", "링크")'

    values = [
        norm(crawl_time),
        norm(g.get("status")),
        norm(g.get("name")),
        norm(g.get("list_price")),
        norm(g.get("sale_price")),
        norm(g.get("discount_rate")),
        norm(g.get("review_count")),
        norm(g.get("free_shipping")),
        make_link(g.get("url")),   # 👈 GS샵 URL → '링크' 하이퍼링크
        norm(p.get("status")),
        norm(p.get("brand")),
        norm(p.get("name")),
        norm(p.get("price")),
        norm(p.get("discount_rate")),
        norm(p.get("label")),
        make_link(p.get("url")),   # 👈 포스티 URL → '링크' 하이퍼링크
    ]

    body = {"values": [values]}

    # ⚠️ 여기 valueInputOption을 USER_ENTERED로!
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=range_name,
        valueInputOption="USER_ENTERED",
        body=body,
    ).execute()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 브라우저 관련
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_driver(profile_dir: str) -> uc.Chrome:
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")  # GitHub Actions용 headless 모드
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,720")
    options.add_argument(f"--user-data-dir={profile_dir}")
    
    # GitHub Actions 환경에서 자동으로 Chrome 다운로드
    driver = uc.Chrome(
        options=options,
        use_subprocess=False,  # 시스템 Chrome 무시
        version_main=None,      # 자동 버전 감지
    )
    return driver


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# no-result 판별 (Selenium 기반 헬퍼)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def is_no_result_gsshop(driver) -> bool:
    """
    GS SHOP 검색 결과 없음 판별
    - '검색결과가 없습니다' 문구
    - error-msg 박스
    """
    try:
        driver.find_element(
            By.XPATH,
            "//h2[contains(@class,'search-title') "
            "and contains(normalize-space(), '검색결과가 없습니다')]"
        )
        return True
    except NoSuchElementException:
        pass

    try:
        driver.find_element(By.CSS_SELECTOR, "div.error-msg .main-txt")
        return True
    except NoSuchElementException:
        pass

    return False


def is_no_result_posty(driver) -> bool:
    """
    포스티(지그재그) 검색 결과 없음 판별
    - '검색결과가 없어요' 문구
    - '총 0개' 문구
    """
    # '검색결과가 없어요'
    try:
        driver.find_element(
            By.XPATH,
            "//*[contains(normalize-space(), '검색결과가 없어요')]"
        )
        return True
    except NoSuchElementException:
        pass

    # '총 0개'
    try:
        driver.find_element(
            By.XPATH,
            "//*[contains(normalize-space(), '총') "
            "and contains(normalize-space(), '0개')]"
        )
        return True
    except NoSuchElementException:
        pass

    return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GS샵 크롤링
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def crawl_gsshop(driver: uc.Chrome, product_name: str) -> Dict[str, Any]:
    """
    GS샵에서 상품명 검색 후 첫 번째 결과를 기준으로 정보 수집.
    - 검색창: #gnb_tq
    - 검색버튼: #searchSubmit (하지만 Enter만으로도 동작)
    - 결과 카드: li a.prd-item
    - 상품명: dt.prd-name
    - 정가: del.price-upper
    - 판매가: span.set-price > strong
    - 할인율: span.price-discount > span
    - 리뷰수: button.user-comment (텍스트: '상품평 1' → 숫자만 추출)
    - 무료배송: dd.advantage 안에 '무료배송' 포함 여부
    """
    try:
        driver.get(GSSHOP_URL)
        wait = WebDriverWait(driver, 10)

        # 검색창 찾기
        search_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#global-search #gnb_tq"))
        )
        search_input.clear()
        search_input.send_keys(product_name)
        search_input.send_keys(Keys.ENTER)

        # 페이지 로딩
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
        time.sleep(1)

        # 먼저 no-result 문구 있는지 체크
        if is_no_result_gsshop(driver):
            return {
                "status": "no_result",
                "name": None,
                "list_price": None,
                "sale_price": None,
                "discount_rate": None,
                "review_count": None,
                "free_shipping": None,
                "url": None,
            }

        # 상품 리스트가 뜨기를 대기
        try:
            wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "li a.prd-item"))
            )
        except TimeoutException:
            # 타임아웃이라도, 다시 한 번 no-result인지 확인
            if is_no_result_gsshop(driver):
                return {
                    "status": "no_result",
                    "name": None,
                    "list_price": None,
                    "sale_price": None,
                    "discount_rate": None,
                    "review_count": None,
                    "free_shipping": None,
                    "url": None,
                }
            # 그 외는 에러 처리
            raise

        time.sleep(1)

        items = driver.find_elements(By.CSS_SELECTOR, "li a.prd-item")
        if not items:
            # 여기까지 왔는데도 아이템이 없으면 no_result로 처리
            return {
                "status": "no_result",
                "name": None,
                "list_price": None,
                "sale_price": None,
                "discount_rate": None,
                "review_count": None,
                "free_shipping": None,
                "url": None,
            }

        item = items[0]
        url = item.get_attribute("href")

        # 상품명
        try:
            name_el = item.find_element(By.CSS_SELECTOR, "dt.prd-name")
            name = name_el.text.strip()
        except Exception:
            name = None

        # 정가
        try:
            list_price_el = item.find_element(By.CSS_SELECTOR, "dd.price-info del.price-upper")
            list_price_txt = list_price_el.text
        except Exception:
            list_price_txt = None

        # 판매가
        try:
            sale_price_el = item.find_element(By.CSS_SELECTOR, "dd.price-info span.set-price strong")
            sale_price_txt = sale_price_el.text
        except Exception:
            sale_price_txt = None

        # 할인율 (3%)
        try:
            disc_el = item.find_element(By.CSS_SELECTOR, "dd.price-info span.price-discount span")
            disc_txt = disc_el.text
        except Exception:
            disc_txt = None

        # 리뷰수 (상품평 1)
        try:
            review_el = item.find_element(By.CSS_SELECTOR, "dd.user-side button.user-comment")
            review_txt = review_el.text
        except Exception:
            review_txt = None

        # 무료배송 여부 (dd.advantage 안의 span 텍스트에 '무료배송' 포함)
        try:
            adv_el = item.find_element(By.CSS_SELECTOR, "dd.advantage")
            free_shipping = "무료배송" in adv_el.text
        except Exception:
            free_shipping = None

        return {
            "status": "ok",
            "name": name,
            "list_price": to_int(list_price_txt),
            "sale_price": to_int(sale_price_txt),
            "discount_rate": to_int(disc_txt),
            "review_count": to_int(review_txt),
            "free_shipping": free_shipping,
            "url": url,
        }

    except Exception as e:
        return {
            "status": "error",
            "name": None,
            "list_price": None,
            "sale_price": None,
            "discount_rate": None,
            "review_count": None,
            "free_shipping": None,
            "url": None,
            "error": str(e),
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 포스티 크롤링
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def crawl_posty(driver: uc.Chrome, product_name: str) -> Dict[str, Any]:
    """
    포스티에서 상품명 검색 후 첫 번째 결과를 기반으로 정보 수집.
    - 검색창: [data-testid="search-bar"] input[type="search"]
    - 결과 래퍼: [data-testid="product-list-view"]
    - 카드: a[data-testid^="product-card"]
    - 브랜드: div.css-9d4fdca215
    - 상품명: div.css-2da8439148
    - 라벨: div.css-e45e9bacca
    - 할인율: span.css-b45adc6b0d
    - 가격: span.css-1d862205be
    """
    try:
        driver.get(POSTY_URL)
        wait = WebDriverWait(driver, 10)

        # 검색창 찾기 (search-bar 안의 input[type=search])
        try:
            search_input = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[data-testid="search-bar"] input[type="search"]')
                )
            )
        except Exception:
            # 혹시 안 잡히면 fallback
            search_input = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'input[type="search"]')
                )
            )

        search_input.clear()
        search_input.send_keys(product_name)
        search_input.send_keys(Keys.ENTER)

        # 페이지 로딩
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
        time.sleep(1)

        # 먼저 no-result 문구 체크
        if is_no_result_posty(driver):
            return {
                "status": "no_result",
                "brand": None,
                "name": None,
                "price": None,
                "discount_rate": None,
                "label": None,
                "url": None,
            }

        # 결과 리스트 로딩 대기
        try:
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[data-testid="product-list-view"]')
                )
            )
        except TimeoutException:
            if is_no_result_posty(driver):
                return {
                    "status": "no_result",
                    "brand": None,
                    "name": None,
                    "price": None,
                    "discount_rate": None,
                    "label": None,
                    "url": None,
                }
            raise

        time.sleep(1)

        # product-card 앵커들 찾기
        items = driver.find_elements(
            By.CSS_SELECTOR, '[data-testid^="product-card"]'
        )
        if not items:
            # 리스트 뷰는 떴는데 카드가 하나도 없으면 no_result로 처리
            return {
                "status": "no_result",
                "brand": None,
                "name": None,
                "price": None,
                "discount_rate": None,
                "label": None,
                "url": None,
            }

        item = items[0]
        href = item.get_attribute("href") or ""
        # href가 /products/... 형식이면 POSTY_URL과 합쳐서 절대 URL로
        if href.startswith("http"):
            url = href
        else:
            url = urljoin(POSTY_URL, href)

        brand = None
        name = None
        price_txt = None
        disc_txt = None
        label_txt = None

        # 브랜드
        try:
            brand_el = item.find_element(By.CSS_SELECTOR, "div.css-9d4fdca215")
            brand = brand_el.text.strip()
        except Exception:
            pass

        # 상품명
        try:
            name_el = item.find_element(By.CSS_SELECTOR, "div.css-2da8439148")
            name = name_el.text.strip()
        except Exception:
            pass

        # 라벨 (예: 블프특가)
        try:
            label_el = item.find_element(By.CSS_SELECTOR, "div.css-e45e9bacca")
            label_txt = label_el.text.strip()
        except Exception:
            pass

        # 할인율 (예: 10%)
        try:
            disc_el = item.find_element(By.CSS_SELECTOR, "span.css-b45adc6b0d")
            disc_txt = disc_el.text
        except Exception:
            disc_txt = None

        # 가격 (예: 27,720)
        try:
            price_el = item.find_element(By.CSS_SELECTOR, "span.css-1d862205be")
            price_txt = price_el.text
        except Exception:
            price_txt = None

        return {
            "status": "ok",
            "brand": brand,
            "name": name,
            "price": to_int(price_txt),
            "discount_rate": to_int(disc_txt),
            "label": label_txt,
            "url": url,
        }

    except Exception as e:
        return {
            "status": "error",
            "brand": None,
            "name": None,
            "price": None,
            "discount_rate": None,
            "label": None,
            "url": None,
            "error": str(e),
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 메인 실행부
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    # 1) Sheets 서비스 생성
    service = get_sheets_service()

    # 2) 상품명 목록 가져오기
    rows = fetch_input_rows(service)
    print(f"▶ 처리 대상 상품 수: {len(rows)}")

    if not rows:
        return

    # 3) 브라우저 두 개 생성 (GS샵, 포스티)
    driver_gs = create_driver(profile_dir="/tmp/chrome-gsshop")
    driver_posty = create_driver(profile_dir="/tmp/chrome-posty")

    try:
        for i, row in enumerate(rows, start=1):
            idx = row["row_index"]
            name = row["product_name"]
            print(f"[{i}/{len(rows)}] 행 {idx} | 상품명: {name}")

            crawl_time = now_kst_str()

            g = crawl_gsshop(driver_gs, name)
            p = crawl_posty(driver_posty, name)

            print("  - GS샵:", g.get("status"), g.get("name"))
            print("  - 포스티:", p.get("status"), p.get("name"))

            update_result_row(service, idx, crawl_time, g, p)

            # 사이트 부담 줄이기 위해 약간 쉬어가기
            time.sleep(2)

    finally:
        driver_gs.quit()
        driver_posty.quit()

    print("✅ 크롤링 완료")


if __name__ == "__main__":
    main()
