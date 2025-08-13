#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
등락율상위분석 결과 테스트 스크립트
콘솔에서 실제 반환 데이터를 확인
"""

import sys
import os
import json
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.top_rate_analysi.database import TopRateDatabase
from modules.top_rate_analysi.utils import group_themes_by_name, calculate_theme_stats


def test_db_connection():
    """데이터베이스 연결 테스트"""
    print("=" * 60)
    print("🔍 데이터베이스 연결 테스트")
    print("=" * 60)

    try:
        db = TopRateDatabase()
        success = db.setup_crawling_database()

        if success:
            print("✅ 데이터베이스 연결 성공")
            return db
        else:
            print("❌ 데이터베이스 연결 실패")
            return None

    except Exception as e:
        print(f"❌ 데이터베이스 연결 오류: {e}")
        return None


def test_theme_tables(db):
    """테마 테이블 존재 여부 확인"""
    print("\n" + "=" * 60)
    print("📊 테마 테이블 확인")
    print("=" * 60)

    try:
        connection = db.get_connection(db.crawling_db)
        cursor = connection.cursor()

        # crawling_db의 모든 테이블 조회
        cursor.execute("SHOW TABLES LIKE 'theme_%'")
        tables = cursor.fetchall()

        if tables:
            print(f"✅ 발견된 테마 테이블: {len(tables)}개")
            for table in tables:
                table_name = table[0]

                # 각 테이블의 레코드 수 확인
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]

                print(f"   📋 {table_name}: {count}개 레코드")

                # 최근 테이블의 샘플 데이터 확인
                if 'theme_20250812' in table_name or 'theme_20250813' in table_name:
                    print(f"\n🔍 {table_name} 샘플 데이터:")
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 2")
                    samples = cursor.fetchall()

                    # 컬럼명 가져오기
                    cursor.execute(f"DESCRIBE {table_name}")
                    columns = [col[0] for col in cursor.fetchall()]

                    for i, sample in enumerate(samples):
                        print(f"\n   레코드 {i + 1}:")
                        for j, col in enumerate(columns):
                            value = sample[j]
                            if col in ['themes', 'news', 'theme_stocks']:
                                # JSON 데이터는 앞부분만 표시
                                if isinstance(value, str) and len(value) > 100:
                                    value = value[:100] + "..."
                            print(f"     {col}: {value}")
        else:
            print("❌ 테마 테이블이 없습니다")

        cursor.close()
        connection.close()

        return tables

    except Exception as e:
        print(f"❌ 테이블 확인 오류: {e}")
        return []


def test_load_themes_data(db, date='2025-08-12'):
    """실제 load-themes API와 동일한 로직 테스트"""
    print("\n" + "=" * 60)
    print(f"📈 {date} 테마 데이터 로드 테스트")
    print("=" * 60)

    try:
        # 1. 원본 데이터 조회
        print("1️⃣ 원본 데이터 조회 중...")
        raw_data = db.get_theme_data(date)

        if not raw_data:
            print(f"❌ {date} 데이터가 없습니다")
            return None

        print(f"✅ 원본 데이터: {len(raw_data)}개 레코드")

        # 2. 첫 번째 레코드 상세 출력
        print("\n2️⃣ 첫 번째 레코드 상세:")
        if raw_data:
            first_record = raw_data[0]
            for key, value in first_record.items():
                if key in ['themes', 'news', 'theme_stocks']:
                    print(f"   {key}: {type(value)} - {str(value)[:200]}...")
                else:
                    print(f"   {key}: {value}")

        # 3. 테마별 그룹화 테스트
        print("\n3️⃣ 테마별 그룹화 테스트...")
        try:
            grouped_themes = group_themes_by_name(raw_data)
            print(f"✅ 그룹화 성공: {len(grouped_themes)}개 테마")

            # 첫 번째 테마 상세 출력
            if grouped_themes:
                first_theme_name = list(grouped_themes.keys())[0]
                first_theme = grouped_themes[first_theme_name]

                print(f"\n🎯 첫 번째 테마: {first_theme_name}")
                print(f"   테마명: {first_theme.get('theme_name')}")
                print(f"   종목 수: {first_theme.get('total_stocks')}")
                print(f"   평균 등락률: {first_theme.get('avg_change_rate')}")
                print(f"   avg_change_rate 타입: {type(first_theme.get('avg_change_rate'))}")

                if first_theme.get('stocks'):
                    print(f"\n   첫 번째 종목:")
                    first_stock = first_theme['stocks'][0]
                    for key, value in first_stock.items():
                        if key == 'news':
                            print(f"     {key}: {len(value) if isinstance(value, list) else 'N/A'}개")
                        else:
                            print(f"     {key}: {value} ({type(value)})")

        except Exception as e:
            print(f"❌ 그룹화 실패: {e}")
            import traceback
            traceback.print_exc()

        # 4. 통계 계산 테스트
        print("\n4️⃣ 통계 계산 테스트...")
        try:
            stats = calculate_theme_stats(raw_data)
            print(f"✅ 통계 계산 성공:")
            for key, value in stats.items():
                print(f"   {key}: {value}")

        except Exception as e:
            print(f"❌ 통계 계산 실패: {e}")
            import traceback
            traceback.print_exc()

        return {
            'raw_data': raw_data,
            'grouped_themes': grouped_themes if 'grouped_themes' in locals() else None,
            'stats': stats if 'stats' in locals() else None
        }

    except Exception as e:
        print(f"❌ 테마 데이터 로드 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_json_parsing(raw_data):
    """JSON 파싱 상세 테스트"""
    print("\n" + "=" * 60)
    print("🔍 JSON 파싱 상세 테스트")
    print("=" * 60)

    if not raw_data:
        print("❌ 테스트할 데이터가 없습니다")
        return

    for i, record in enumerate(raw_data[:3]):  # 처음 3개만 테스트
        print(f"\n📋 레코드 {i + 1} JSON 파싱 테스트:")

        # themes 파싱
        try:
            themes_raw = record['themes']
            print(f"   themes 원본: {themes_raw} ({type(themes_raw)})")

            if isinstance(themes_raw, str):
                themes_parsed = json.loads(themes_raw)
            else:
                themes_parsed = themes_raw

            print(f"   themes 파싱 결과: {themes_parsed} ({type(themes_parsed)})")

        except Exception as e:
            print(f"   ❌ themes 파싱 실패: {e}")

        # news 파싱
        try:
            news_raw = record['news']
            print(f"   news 원본 타입: {type(news_raw)}")

            if isinstance(news_raw, str):
                news_parsed = json.loads(news_raw)
            else:
                news_parsed = news_raw

            print(f"   news 파싱 결과: {len(news_parsed) if isinstance(news_parsed, list) else 'Not a list'}개")

            if isinstance(news_parsed, list) and news_parsed:
                print(f"   첫 번째 뉴스: {news_parsed[0].get('title', 'No title')}")

        except Exception as e:
            print(f"   ❌ news 파싱 실패: {e}")


def main():
    """메인 테스트 실행"""
    print("🚀 등락율상위분석 데이터 구조 테스트 시작")
    print("현재 시간:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    # 1. DB 연결 테스트
    db = test_db_connection()
    if not db:
        print("❌ DB 연결 실패로 테스트 중단")
        return

    # 2. 테이블 확인
    tables = test_theme_tables(db)
    if not tables:
        print("❌ 테이블이 없어서 테스트 중단")
        return

    # 3. 테스트할 날짜 확인
    test_dates = ['2025-08-12']

    for test_date in test_dates:
        print(f"\n{'=' * 80}")
        print(f"📅 {test_date} 데이터 테스트")
        print(f"{'=' * 80}")

        result = test_load_themes_data(db, test_date)

        if result and result['raw_data']:
            # JSON 파싱 상세 테스트
            test_json_parsing(result['raw_data'])

            # 최종 API 응답 형태 시뮬레이션
            print(f"\n🎯 {test_date} 최종 API 응답 시뮬레이션:")

            if result['grouped_themes'] and result['stats']:
                api_response = {
                    'success': True,
                    'themes': result['grouped_themes'],
                    'stats': result['stats'],
                    'date': test_date
                }

                print("✅ API 응답 구조:")
                print(f"   success: {api_response['success']}")
                print(f"   themes 개수: {len(api_response['themes'])}")
                print(f"   stats: {api_response['stats']}")
                print(f"   date: {api_response['date']}")

                # 테마 중 하나의 avg_change_rate 확인
                if api_response['themes']:
                    first_theme = list(api_response['themes'].values())[0]
                    avg_rate = first_theme.get('avg_change_rate')
                    print(f"   샘플 avg_change_rate: {avg_rate} ({type(avg_rate)})")

                    if avg_rate is not None:
                        try:
                            formatted = f"{avg_rate:.2f}"
                            print(f"   .toFixed(2) 시뮬레이션: {formatted}")
                        except Exception as e:
                            print(f"   ❌ .toFixed() 시뮬레이션 실패: {e}")

            else:
                print("❌ 그룹화 또는 통계 계산 실패로 API 응답 생성 불가")

        print(f"\n{'=' * 80}")


if __name__ == "__main__":
    main()