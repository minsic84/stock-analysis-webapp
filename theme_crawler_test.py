#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
네이버 금융 테마 + 뉴스 크롤링 + DB 저장
- 테마별 상위 3개 종목의 뉴스 5개씩 수집
- MySQL DB에 JSON 형태로 저장
- DB 저장 결과만 콘솔 출력
"""

import requests
from bs4 import BeautifulSoup
import time
import re
import json
import pymysql
from datetime import datetime, timedelta
from urllib.parse import urljoin
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()


def clean_text(text):
    """텍스트 정리"""
    if not text:
        return ""
    return text.strip().replace('\n', '').replace('\t', '').replace('\xa0', '').replace(',', '')


def parse_number(text):
    """숫자 파싱"""
    if not text:
        return 0
    try:
        clean_num = re.sub(r'[^\d.-]', '', str(text))
        return int(float(clean_num)) if clean_num else 0
    except:
        return 0


def parse_percentage(text):
    """퍼센트 파싱"""
    if not text:
        return 0
    try:
        match = re.search(r'([+-]?\d+\.?\d*)%?', str(text))
        if match:
            return float(match.group(1))
        return 0
    except:
        return 0


def get_db_connection():
    """DB 연결"""
    try:
        connection = pymysql.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 3306)),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            charset='utf8mb4',
            autocommit=True
        )
        return connection
    except Exception as e:
        print(f"❌ DB 연결 실패: {e}")
        return None


def setup_database():
    """DB 스키마 및 테이블 설정"""
    print("🗄️ DB 설정 시작...")

    connection = get_db_connection()
    if not connection:
        return False

    try:
        cursor = connection.cursor()

        # 1. crawling_db 스키마 생성
        cursor.execute("CREATE DATABASE IF NOT EXISTS crawling_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print("   ✅ crawling_db 스키마 생성/확인 완료")

        # 2. crawling_db 사용
        cursor.execute("USE crawling_db")

        # 3. 오늘 날짜 테이블명
        today = datetime.now().strftime('%Y%m%d')
        table_name = f"theme_{today}"

        # 4. 기존 테이블 삭제 (있다면)
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        print(f"   🗑️ 기존 {table_name} 테이블 삭제")

        # 5. 새 테이블 생성
        create_table_sql = f"""
        CREATE TABLE {table_name} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            stock_code VARCHAR(10) NOT NULL,
            stock_name VARCHAR(100) NOT NULL,
            themes JSON NOT NULL,
            price INT DEFAULT 0,
            change_rate DECIMAL(5,2) DEFAULT 0,
            volume BIGINT DEFAULT 0,
            news JSON NOT NULL,
            theme_stocks JSON NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_stock_code (stock_code),
            INDEX idx_stock_name (stock_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """

        cursor.execute(create_table_sql)
        print(f"   ✅ {table_name} 테이블 생성 완료")

        cursor.close()
        connection.close()

        return table_name

    except Exception as e:
        print(f"   ❌ DB 설정 실패: {e}")
        if connection:
            connection.close()
        return False


def save_to_database(data, table_name):
    """크롤링 데이터를 DB에 저장"""
    print(f"\n💾 DB 저장 시작 (테이블: {table_name})...")

    connection = get_db_connection()
    if not connection:
        return False

    try:
        cursor = connection.cursor()
        cursor.execute("USE crawling_db")

        # 종목별로 데이터 정리 (중복 제거)
        stock_data = {}

        for theme_name, theme_data in data.items():
            theme_info = theme_data['theme_info']
            theme_stocks = theme_data['theme_stocks']  # 테마 내 모든 종목 정보

            for stock in theme_data['stocks']:
                stock_code = stock['code']

                if stock_code not in stock_data:
                    stock_data[stock_code] = {
                        'stock_code': stock_code,
                        'stock_name': stock['name'],
                        'themes': [],
                        'price': stock['price'],
                        'change_rate': stock['change_rate'],
                        'volume': stock['volume'],
                        'news': stock['news'],
                        'theme_stocks': {}  # 테마별 종목 정보
                    }

                # 테마 추가 (중복 방지)
                if theme_name not in stock_data[stock_code]['themes']:
                    stock_data[stock_code]['themes'].append(theme_name)

                # 해당 테마의 모든 종목 정보 추가
                stock_data[stock_code]['theme_stocks'][theme_name] = theme_stocks

        # DB에 삽입
        insert_sql = f"""
        INSERT INTO {table_name} (stock_code, stock_name, themes, price, change_rate, volume, news, theme_stocks)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        success_count = 0
        for stock_code, stock_info in stock_data.items():
            try:
                cursor.execute(insert_sql, (
                    stock_info['stock_code'],
                    stock_info['stock_name'],
                    json.dumps(stock_info['themes'], ensure_ascii=False),
                    stock_info['price'],
                    stock_info['change_rate'],
                    stock_info['volume'],
                    json.dumps(stock_info['news'], ensure_ascii=False),
                    json.dumps(stock_info['theme_stocks'], ensure_ascii=False)
                ))
                success_count += 1

                # 저장된 데이터 출력
                themes_str = ', '.join(stock_info['themes'])
                news_count = len(stock_info['news'])
                total_theme_stocks = sum(len(stocks) for stocks in stock_info['theme_stocks'].values())

                print(f"   💾 {stock_info['stock_name']} ({stock_code})")
                print(f"      📋 테마: {themes_str}")
                print(f"      💰 가격: {stock_info['price']:,}원 ({stock_info['change_rate']:+.2f}%)")
                print(f"      📰 뉴스: {news_count}개")
                print(f"      👥 테마 내 종목: {total_theme_stocks}개")

            except Exception as e:
                print(f"   ❌ {stock_info['stock_name']} 저장 실패: {e}")

        cursor.close()
        connection.close()

        print(f"\n✅ DB 저장 완료: {success_count}/{len(stock_data)}개 종목")
        return True

    except Exception as e:
        print(f"❌ DB 저장 실패: {e}")
        if connection:
            connection.close()
        return False


def verify_database(table_name):
    """DB 저장 결과 검증"""
    print(f"\n🔍 DB 저장 결과 검증 (테이블: {table_name})...")

    connection = get_db_connection()
    if not connection:
        return

    try:
        cursor = connection.cursor()
        cursor.execute("USE crawling_db")

        # 총 레코드 수
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_count = cursor.fetchone()[0]

        # 테마별 통계
        cursor.execute(f"""
        SELECT 
            JSON_UNQUOTE(JSON_EXTRACT(themes, '$[0]')) as first_theme,
            COUNT(*) as stock_count,
            AVG(change_rate) as avg_change_rate
        FROM {table_name}
        GROUP BY first_theme
        ORDER BY stock_count DESC
        """)

        theme_stats = cursor.fetchall()

        # 뉴스 통계
        cursor.execute(f"""
        SELECT 
            AVG(JSON_LENGTH(news)) as avg_news_count,
            MIN(JSON_LENGTH(news)) as min_news_count,
            MAX(JSON_LENGTH(news)) as max_news_count
        FROM {table_name}
        """)

        news_stats = cursor.fetchone()

        # 상위 5개 종목
        cursor.execute(f"""
        SELECT stock_name, change_rate, JSON_LENGTH(news) as news_count
        FROM {table_name}
        ORDER BY change_rate DESC
        LIMIT 5
        """)

        top_stocks = cursor.fetchall()

        # 테마 내 종목 통계
        cursor.execute(f"""
        SELECT 
            AVG(JSON_LENGTH(theme_stocks)) as avg_theme_stocks,
            JSON_UNQUOTE(JSON_EXTRACT(JSON_KEYS(theme_stocks), '$[0]')) as sample_theme
        FROM {table_name}
        WHERE JSON_LENGTH(theme_stocks) > 0
        LIMIT 1
        """)

        theme_stocks_stats = cursor.fetchone()

        # 결과 출력
        print(f"   📊 총 종목 수: {total_count}개")
        print(f"   📰 평균 뉴스 수: {news_stats[0]:.1f}개 (최소: {news_stats[1]}개, 최대: {news_stats[2]}개)")

        if theme_stocks_stats and theme_stocks_stats[0]:
            print(f"   👥 평균 테마 내 종목 수: {theme_stocks_stats[0]:.1f}개")

        print(f"\n   📋 테마별 종목 수:")
        for theme, count, avg_rate in theme_stats[:5]:  # 상위 5개 테마
            print(f"      {theme}: {count}개 종목 (평균 등락률: {avg_rate:+.2f}%)")

        print(f"\n   🏆 상위 5개 종목:")
        for i, (name, rate, news_count) in enumerate(top_stocks, 1):
            print(f"      {i}. {name}: {rate:+.2f}% ({news_count}개 뉴스)")

        cursor.close()
        connection.close()

    except Exception as e:
        print(f"   ❌ DB 검증 실패: {e}")
        if connection:
            connection.close()


# 기존 크롤링 함수들 (간소화 - DB 저장 관련 로그만 출력)
def get_theme_list():
    """테마 리스트 크롤링 (로그 최소화)"""
    url = "https://finance.naver.com/sise/theme.naver"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'euc-kr'
        soup = BeautifulSoup(response.text, 'html.parser')

        table = soup.find('table', {'class': 'type_1'})
        if not table:
            return []

        themes = []
        rows = table.find_all('tr')[1:]

        for row in rows:
            try:
                cols = row.find_all('td')
                if len(cols) < 4:
                    continue

                theme_link = cols[0].find('a')
                if not theme_link:
                    continue

                theme_name = clean_text(theme_link.text)
                theme_url = theme_link.get('href', '')
                theme_code_match = re.search(r'no=(\d+)', theme_url)
                theme_code = theme_code_match.group(1) if theme_code_match else ""
                change_rate = parse_percentage(cols[3].text)

                if theme_name and theme_code and change_rate > 0:
                    themes.append({
                        'name': theme_name,
                        'code': theme_code,
                        'change_rate': change_rate,
                        'url': f"https://finance.naver.com{theme_url}"
                    })
            except:
                continue

        return themes
    except:
        return []


def get_theme_stocks(theme_code, theme_name, limit=5):
    """특정 테마의 상위 종목 크롤링 + 테마 내 모든 종목 정보"""
    print(f"    📈 {theme_name} 상위 {limit}개 종목 + 전체 종목 정보 수집...")

    url = f"https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no={theme_code}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'euc-kr'
        soup = BeautifulSoup(response.text, 'html.parser')

        stock_links = soup.find_all('a', href=re.compile(r'/item/main\.naver\?code=\d{6}'))
        if not stock_links:
            return [], []

        # 모든 종목 정보 수집 (theme_stocks용)
        all_theme_stocks = []
        top_stocks = []  # 상위 종목들
        processed_codes = set()

        for link in stock_links:
            try:
                href = link.get('href', '')
                code_match = re.search(r'code=(\d{6})', href)
                if not code_match:
                    continue

                stock_code = code_match.group(1)
                if stock_code in processed_codes:
                    continue
                processed_codes.add(stock_code)

                stock_name = clean_text(link.text)
                if not stock_name or len(stock_name) < 2:
                    continue

                row = link.find_parent('tr')
                current_price = 0
                change_rate = 0
                volume = 0

                if row:
                    cells = row.find_all('td')
                    for cell in cells:
                        cell_text = clean_text(cell.text)

                        if cell_text.isdigit() and int(cell_text) >= 1000:
                            if current_price == 0:
                                current_price = int(cell_text)

                        if '%' in cell_text:
                            rate = parse_percentage(cell_text)
                            if abs(rate) < 100:
                                change_rate = rate

                        if cell_text.isdigit() and int(cell_text) > 10000:
                            if volume == 0 or int(cell_text) > volume:
                                volume = int(cell_text)

                # 모든 종목 정보 (theme_stocks용)
                theme_stock_info = {
                    'code': stock_code,
                    'name': stock_name,
                    'price': current_price,
                    'change_rate': change_rate,
                    'volume': volume
                }
                all_theme_stocks.append(theme_stock_info)

                # 상위 종목들만 따로 저장 (뉴스 수집용)
                if len(top_stocks) < limit:
                    top_stocks.append({
                        'code': stock_code,
                        'name': stock_name,
                        'price': current_price,
                        'change_rate': change_rate,
                        'volume': volume
                    })

            except:
                continue

        print(f"    ✅ {theme_name}: 상위 {len(top_stocks)}개 종목, 전체 {len(all_theme_stocks)}개 종목 정보 수집")
        return top_stocks, all_theme_stocks

    except Exception as e:
        print(f"    ❌ {theme_name} 크롤링 실패: {e}")
        return [], []


def get_stock_news(stock_code, stock_name, limit=5):
    """특정 종목의 뉴스 크롤링 (뉴스 5개)"""
    url = f"https://finance.naver.com/item/news_news.naver?code={stock_code}&page=1&sm=title_entity_id.basic&clusterId="
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': f'https://finance.naver.com/item/main.naver?code={stock_code}'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'euc-kr'
        soup = BeautifulSoup(response.text, 'html.parser')

        news_table = soup.find('table', {'class': 'type5'})
        if not news_table:
            return []

        news_list = []
        rows = news_table.find_all('tr')

        current_date = None
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        for row in rows:
            try:
                date_cell = row.find('td', {'class': 'date'})
                if date_cell and date_cell.get('colspan'):
                    date_text = clean_text(date_cell.text)
                    current_date = parse_news_date(date_text)
                    continue

                title_cell = row.find('td', {'class': 'title'})
                if not title_cell:
                    continue

                news_link = title_cell.find('a')
                if not news_link:
                    continue

                title = clean_text(news_link.text)
                if not title:
                    continue

                news_url = news_link.get('href', '')
                if news_url and not news_url.startswith('http'):
                    news_url = urljoin('https://finance.naver.com', news_url)

                source_cell = row.find('td', {'class': 'info'})
                source = clean_text(source_cell.text) if source_cell else ""

                time_cell = row.find('td', {'class': 'date'})
                news_time = current_date
                if time_cell and not time_cell.get('colspan'):
                    time_text = clean_text(time_cell.text)
                    news_time = parse_news_time(time_text, current_date)

                if news_time and (news_time.date() == today or news_time.date() == yesterday):
                    news_data = {
                        'title': title,
                        'url': news_url,
                        'source': source,
                        'time': news_time.strftime('%Y-%m-%d %H:%M') if news_time else '',
                        'is_today': news_time.date() == today if news_time else False
                    }

                    news_list.append(news_data)

                    if len(news_list) >= limit:
                        break

            except:
                continue

        return news_list
    except:
        return []


def parse_news_date(date_text):
    """뉴스 날짜 파싱"""
    try:
        if '.' in date_text:
            date_parts = date_text.split('.')
            if len(date_parts) == 3:
                year = int(date_parts[0])
                month = int(date_parts[1])
                day = int(date_parts[2])
                return datetime(year, month, day)

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if '오늘' in date_text:
            return today
        elif '어제' in date_text:
            return today - timedelta(days=1)

        return today
    except:
        return datetime.now()


def parse_news_time(time_text, base_date):
    """뉴스 시간 파싱"""
    try:
        if not base_date:
            base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        time_match = re.search(r'(\d{1,2}):(\d{2})', time_text)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            return base_date.replace(hour=hour, minute=minute)

        return base_date
    except:
        return base_date


def main():
    """메인 실행 함수"""
    print("🚀 네이버 금융 테마 + 뉴스 크롤링 + DB 저장 시작\n")

    # 1. DB 설정
    table_name = setup_database()
    if not table_name:
        print("❌ DB 설정 실패 - 프로그램 종료")
        return

    # 2. 크롤링 실행 (로그 최소화)
    print("\n📡 크롤링 시작...")
    themes = get_theme_list()

    if not themes:
        print("❌ 크롤링할 테마가 없습니다")
        return

    print(f"✅ {len(themes)}개 상승 테마 발견")

    # 3. 데이터 수집 (모든 상승 테마의 상위 5개 종목)
    result = {}

    for i, theme in enumerate(themes):
        theme_name = theme['name']
        theme_code = theme['code']
        change_rate = theme['change_rate']

        print(f"[{i + 1}/{len(themes)}] {theme_name} (+{change_rate}%) 처리 중...")

        # 해당 테마의 상위 5개 종목 + 전체 종목 정보 수집
        top_stocks, all_theme_stocks = get_theme_stocks(theme_code, theme_name, limit=5)
        if not top_stocks:
            print(f"    ❌ {theme_name}: 종목을 찾을 수 없음")
            continue

        print(f"    📰 상위 {len(top_stocks)}개 종목의 뉴스 수집 시작...")

        # 상위 5개 종목의 뉴스만 수집
        stocks_with_news = []
        for j, stock in enumerate(top_stocks):
            print(f"       [{j + 1}/{len(top_stocks)}] {stock['name']} 뉴스 수집...")
            stock_news = get_stock_news(stock['code'], stock['name'], limit=5)

            stock_data = stock.copy()
            stock_data['news'] = stock_news
            stocks_with_news.append(stock_data)

            time.sleep(0.8)  # 종목 간 요청 간격

        result[theme_name] = {
            'theme_info': {
                'code': theme_code,
                'change_rate': change_rate
            },
            'stocks': stocks_with_news,
            'theme_stocks': all_theme_stocks  # 테마 내 모든 종목 정보
        }

        total_news = sum(len(stock['news']) for stock in stocks_with_news)
        print(
            f"    ✅ {theme_name} 완료: 상위 {len(stocks_with_news)}개 종목, {total_news}개 뉴스, 테마 내 {len(all_theme_stocks)}개 종목 정보")

        time.sleep(2)  # 테마 간 요청 간격

    # 4. DB 저장
    if result:
        save_success = save_to_database(result, table_name)

        if save_success:
            # 5. DB 검증
            verify_database(table_name)

        print(f"\n🎯 최종 결과:")
        print(f"   📊 테이블: {table_name}")
        print(f"   📋 테마: {len(result)}개")
        total_stocks = sum(len(data['stocks']) for data in result.values())
        total_news = sum(len(stock['news']) for data in result.values() for stock in data['stocks'])
        print(f"   📈 총 종목: {total_stocks}개")
        print(f"   📰 총 뉴스: {total_news}개")
        print(f"   ⚡ 평균 종목당 뉴스: {total_news / total_stocks:.1f}개" if total_stocks > 0 else "")

        # 테마별 통계
        print(f"\n📊 테마별 상세:")
        for theme_name, data in result.items():
            stock_count = len(data['stocks'])
            news_count = sum(len(stock['news']) for stock in data['stocks'])
            print(f"   {theme_name}: {stock_count}개 종목, {news_count}개 뉴스")
    else:
        print("❌ 크롤링 결과가 없습니다")


if __name__ == "__main__":
    main()