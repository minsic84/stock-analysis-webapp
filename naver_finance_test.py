#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
네이버 금융 접근 테스트
현재 사이트 구조와 접근 가능 여부 확인
"""

import requests
from bs4 import BeautifulSoup
import time


def test_naver_finance():
    """네이버 금융 접근 테스트"""

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    print("🔍 네이버 금융 접근 테스트 시작")
    print("=" * 60)

    # 1단계: 메인 테마 페이지 접근
    theme_url = "https://finance.naver.com/sise/theme.naver"

    try:
        print(f"📡 테마 페이지 접근: {theme_url}")
        response = requests.get(theme_url, headers=headers, timeout=10)
        print(f"📊 응답 코드: {response.status_code}")
        print(f"📏 응답 크기: {len(response.text):,} bytes")

        if response.status_code == 200:
            response.encoding = 'euc-kr'
            soup = BeautifulSoup(response.text, 'html.parser')

            # 테이블 찾기
            table = soup.find('table', {'class': 'type_1'})
            if table:
                rows = table.find_all('tr')[1:]  # 헤더 제외
                print(f"✅ 테마 테이블 발견: {len(rows)}개 행")

                # 처음 5개 테마 정보 출력
                print("\n📋 상위 5개 테마:")
                for i, row in enumerate(rows[:5]):
                    try:
                        cols = row.find_all('td')
                        if len(cols) >= 4:
                            theme_link = cols[0].find('a')
                            if theme_link:
                                theme_name = theme_link.text.strip()
                                change_rate = cols[3].text.strip()
                                print(f"   {i + 1}. {theme_name} ({change_rate})")
                    except Exception as e:
                        print(f"   {i + 1}. 파싱 오류: {e}")

            else:
                print("❌ 테마 테이블을 찾을 수 없습니다")
                print("🔍 페이지 구조 변경 가능성 있음")

                # 페이지 내용 샘플 출력
                print("\n📄 페이지 내용 샘플 (처음 500자):")
                print(response.text[:500])

        else:
            print(f"❌ 접근 실패: HTTP {response.status_code}")

    except requests.exceptions.Timeout:
        print("❌ 타임아웃 발생")
    except requests.exceptions.ConnectionError:
        print("❌ 연결 오류")
    except Exception as e:
        print(f"❌ 기타 오류: {e}")

    print("\n" + "=" * 60)

    # 2단계: 특정 테마 상세 페이지 테스트
    theme_detail_url = "https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no=224"  # 2차전지

    try:
        print(f"📡 테마 상세 페이지 접근: {theme_detail_url}")
        response = requests.get(theme_detail_url, headers=headers, timeout=10)
        print(f"📊 응답 코드: {response.status_code}")

        if response.status_code == 200:
            response.encoding = 'euc-kr'
            soup = BeautifulSoup(response.text, 'html.parser')

            # 종목 테이블 찾기
            table = soup.find('table', {'class': 'type_1'})
            if table:
                rows = table.find_all('tr')[1:]  # 헤더 제외
                print(f"✅ 종목 테이블 발견: {len(rows)}개 행")

                # 처음 3개 종목 정보 출력
                print("\n📈 상위 3개 종목:")
                for i, row in enumerate(rows[:3]):
                    try:
                        cols = row.find_all('td')
                        if len(cols) >= 6:
                            stock_link = cols[0].find('a')
                            if stock_link:
                                stock_name = stock_link.text.strip()
                                price = cols[1].text.strip()
                                change = cols[3].text.strip()
                                print(f"   {i + 1}. {stock_name} ({price}, {change})")
                    except Exception as e:
                        print(f"   {i + 1}. 파싱 오류: {e}")

            else:
                print("❌ 종목 테이블을 찾을 수 없습니다")

        else:
            print(f"❌ 접근 실패: HTTP {response.status_code}")

    except Exception as e:
        print(f"❌ 오류: {e}")

    print("\n" + "=" * 60)
    print("🎯 테스트 완료")


if __name__ == "__main__":
    test_naver_finance()