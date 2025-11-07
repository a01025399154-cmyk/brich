#!/usr/bin/env python3
"""
엑셀 파일 통합 디버깅 스크립트
생성된 파일과 수동 저장 파일의 모든 차이점 분석
"""

import zipfile
import xml.etree.ElementTree as ET
import sys
import os

def analyze_file(filepath, label):
    """파일 전체 분석"""
    print(f"\n{'='*70}")
    print(f"{label}: {filepath.split('/')[-1]}")
    print(f"{'='*70}")
    
    try:
        with zipfile.ZipFile(filepath, 'r') as zf:
            # 1. 파일 리스트
            print("\n[1] ZIP 내부 파일:")
            files = zf.namelist()
            has_shared = 'xl/sharedStrings.xml' in files
            print(f"  sharedStrings.xml: {'있음 ✅' if has_shared else '없음 ❌'}")
            
            # 2. sharedStrings 내용
            if has_shared:
                with zf.open('xl/sharedStrings.xml') as f:
                    content = f.read().decode('utf-8')
                    root = ET.fromstring(content)
                    ns = {'ss': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                    si_list = root.findall('ss:si', ns)
                    print(f"\n[2] sharedStrings ({len(si_list)}개):")
                    for idx, si in enumerate(si_list[:15]):  # 처음 15개만
                        t = si.find('ss:t', ns)
                        text = t.text if t is not None else "None"
                        print(f"  [{idx}]: {text}")
            else:
                print(f"\n[2] sharedStrings: 없음 ❌")
            
            # 3. sheet1.xml 분석
            with zf.open('xl/worksheets/sheet1.xml') as f:
                content = f.read().decode('utf-8')
                root = ET.fromstring(content)
                ns = {'ss': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                
                # dimension
                dimension = root.find('.//ss:dimension', ns)
                dim_ref = dimension.get('ref') if dimension is not None else 'None'
                print(f"\n[3] Dimension: {dim_ref}")
                
                # Row 1 (헤더)
                sheet_data = root.find('.//ss:sheetData', ns)
                row1 = sheet_data.find("ss:row[@r='1']", ns)
                
                print(f"\n[4] Row 1 (헤더):")
                if row1 is not None:
                    cells = row1.findall('ss:c', ns)[:5]  # 처음 5개
                    for cell in cells:
                        ref = cell.get('r')
                        s = cell.get('s', 'None')
                        t = cell.get('t', 'None')
                        v = cell.find('ss:v', ns)
                        val = v.text if v is not None else 'empty'
                        print(f"  {ref}: s={s}, t={t}, v={val}")
                
                # Row 2 (첫 데이터)
                row2 = sheet_data.find("ss:row[@r='2']", ns)
                
                print(f"\n[5] Row 2 (첫 데이터):")
                if row2 is not None:
                    cells = row2.findall('ss:c', ns)[:5]  # 처음 5개
                    for cell in cells:
                        ref = cell.get('r')
                        s = cell.get('s', 'None')
                        t = cell.get('t', 'None')
                        v = cell.find('ss:v', ns)
                        val = v.text if v is not None else 'empty'
                        
                        # XML 전체 출력
                        xml_str = ET.tostring(cell, encoding='unicode')
                        print(f"\n  {ref}:")
                        print(f"    XML: {xml_str[:150]}")
                        print(f"    s={s}, t={t}, value={val}")
                
                # 총 row 개수
                rows = sheet_data.findall('ss:row', ns)
                print(f"\n[6] 총 행 개수: {len(rows)}")
            
            # 4. styles.xml 분석
            with zf.open('xl/styles.xml') as f:
                content = f.read().decode('utf-8')
                root = ET.fromstring(content)
                ns = {'ss': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                
                xfs = root.find('.//ss:cellXfs', ns)
                if xfs:
                    xf_list = list(xfs.findall('ss:xf', ns))
                    print(f"\n[7] Styles ({len(xf_list)}개):")
                    for idx in [0, 1, 2, 3, 4, 5]:
                        if idx < len(xf_list):
                            xf = xf_list[idx]
                            xml_str = ET.tostring(xf, encoding='unicode')
                            print(f"  Style {idx}:")
                            print(f"    {xml_str[:100]}")
            
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()


def compare_files(auto, manual):
    """두 파일 비교 요약"""
    print(f"\n{'='*70}")
    print("비교 요약")
    print(f"{'='*70}")
    
    issues = []
    
    with zipfile.ZipFile(auto, 'r') as zf_auto:
        with zipfile.ZipFile(manual, 'r') as zf_manual:
            # sharedStrings 비교
            has_auto = 'xl/sharedStrings.xml' in zf_auto.namelist()
            has_manual = 'xl/sharedStrings.xml' in zf_manual.namelist()
            
            if not has_auto and has_manual:
                issues.append("❌ 자동생성에 sharedStrings.xml 없음")
            
            # A1, A2 비교
            ns = {'ss': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            
            for zf, lbl in [(zf_auto, "자동"), (zf_manual, "수동")]:
                with zf.open('xl/worksheets/sheet1.xml') as f:
                    root = ET.fromstring(f.read().decode('utf-8'))
                    sheet_data = root.find('.//ss:sheetData', ns)
                    
                    # A1
                    row1 = sheet_data.find("ss:row[@r='1']", ns)
                    a1 = row1.find("ss:c[@r='A1']", ns) if row1 else None
                    a1_t = a1.get('t', 'None') if a1 else 'None'
                    
                    # A2
                    row2 = sheet_data.find("ss:row[@r='2']", ns)
                    a2 = row2.find("ss:c[@r='A2']", ns) if row2 else None
                    a2_s = a2.get('s', 'None') if a2 else 'None'
                    a2_t = a2.get('t', 'None') if a2 else 'None'
                    
                    print(f"\n{lbl}:")
                    print(f"  A1: t={a1_t}")
                    print(f"  A2: s={a2_s}, t={a2_t}")
    
    if issues:
        print(f"\n발견된 문제:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print(f"\n✅ 구조적 문제 없음")


if __name__ == "__main__":
    print("="*70)
    print("엑셀 파일 통합 디버깅 - 상품 & 브랜드")
    print("="*70)
    
    # 파일 쌍 정의
    file_pairs = [
        {
            'type': '상품',
            'auto': '/Users/brich/Desktop/brich/outputs/251106-251111_상품_옥션_1.xlsx',
            'manual': '/Users/brich/Desktop/brich/251106-251111_상품_옥션_1_manual.xlsx'
        },
        {
            'type': '브랜드',
            'auto': '/Users/brich/Desktop/brich/outputs/251105-251205_브랜드_11번가_1.xlsx',
            'manual': '/Users/brich/Desktop/brich/내부할인브랜드.xlsx'
        }
    ]
    
    # 각 파일 쌍 분석
    for pair in file_pairs:
        print(f"\n\n{'#'*70}")
        print(f"# {pair['type']} 파일 분석")
        print(f"{'#'*70}")
        
        auto = pair['auto']
        manual = pair['manual']
        
        # 파일 존재 확인
        import os
        if not os.path.exists(auto):
            print(f"❌ 자동생성 파일 없음: {auto}")
            continue
        if not os.path.exists(manual):
            print(f"❌ 수동저장 파일 없음: {manual}")
            continue
        
        # 분석
        analyze_file(auto, f"자동생성 ({pair['type']})")
        analyze_file(manual, f"수동저장 ({pair['type']})")
        
        # 비교
        compare_files(auto, manual)
    
    # 최종 요약
    print(f"\n\n{'='*70}")
    print("전체 요약")
    print(f"{'='*70}")
    
    for pair in file_pairs:
        auto = pair['auto']
        manual = pair['manual']
        
        if not os.path.exists(auto) or not os.path.exists(manual):
            continue
        
        print(f"\n[{pair['type']}]")
        
        with zipfile.ZipFile(auto, 'r') as zf_auto:
            with zipfile.ZipFile(manual, 'r') as zf_manual:
                ns = {'ss': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                
                # 자동생성
                has_ss_auto = 'xl/sharedStrings.xml' in zf_auto.namelist()
                with zf_auto.open('xl/worksheets/sheet1.xml') as f:
                    root = ET.fromstring(f.read().decode('utf-8'))
                    sheet_data = root.find('.//ss:sheetData', ns)
                    row1 = sheet_data.find("ss:row[@r='1']", ns)
                    a1_auto = row1.find("ss:c[@r='A1']", ns) if row1 else None
                    row2 = sheet_data.find("ss:row[@r='2']", ns)
                    a2_auto = row2.find("ss:c[@r='A2']", ns) if row2 else None
                
                # 수동저장
                has_ss_manual = 'xl/sharedStrings.xml' in zf_manual.namelist()
                with zf_manual.open('xl/worksheets/sheet1.xml') as f:
                    root = ET.fromstring(f.read().decode('utf-8'))
                    sheet_data = root.find('.//ss:sheetData', ns)
                    row1 = sheet_data.find("ss:row[@r='1']", ns)
                    a1_manual = row1.find("ss:c[@r='A1']", ns) if row1 else None
                    row2 = sheet_data.find("ss:row[@r='2']", ns)
                    a2_manual = row2.find("ss:c[@r='A2']", ns) if row2 else None
                
                # 비교
                issues = []
                
                # sharedStrings
                if has_ss_auto != has_ss_manual:
                    issues.append(f"sharedStrings: 자동={has_ss_auto}, 수동={has_ss_manual}")
                
                # A1
                a1_t_auto = a1_auto.get('t', 'None') if a1_auto else 'None'
                a1_t_manual = a1_manual.get('t', 'None') if a1_manual else 'None'
                if a1_t_auto != a1_t_manual:
                    issues.append(f"A1 t: 자동={a1_t_auto}, 수동={a1_t_manual}")
                
                # A2
                a2_s_auto = a2_auto.get('s', 'None') if a2_auto else 'None'
                a2_s_manual = a2_manual.get('s', 'None') if a2_manual else 'None'
                a2_t_auto = a2_auto.get('t', 'None') if a2_auto else 'None'
                a2_t_manual = a2_manual.get('t', 'None') if a2_manual else 'None'
                
                if a2_s_auto != a2_s_manual:
                    issues.append(f"A2 s: 자동={a2_s_auto}, 수동={a2_s_manual}")
                if a2_t_auto != a2_t_manual:
                    issues.append(f"A2 t: 자동={a2_t_auto}, 수동={a2_t_manual}")
                
                # 결과
                if issues:
                    print("  ❌ 차이점:")
                    for issue in issues:
                        print(f"    - {issue}")
                else:
                    print("  ✅ 완전히 일치!")
    
    print(f"\n{'='*70}")
    print("디버깅 완료")
    print(f"{'='*70}")