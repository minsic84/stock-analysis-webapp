#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
네이버 금융 테마 크롤러 (theme_crawler_test.py 기반)
테마별 상위 종목의 뉴스를 수집하여 DB에 저장
"""

import requests
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin
import logging
from typing import List, Dict

from modules.top_rate_analysis.utils import clean_text, parse_percentage, parse_news_date, parse_news_time
from .database import TopRateDatabase


class ThemeCrawler:
    """테마 크롤링 클래스 (theme_crawler_test.py 기반)"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
        self.db = TopRateDatabase()

    def crawl_and_save_themes(self, target_date: str) -> bool:
        """테마 크롤링 후 DB 저장 (메인 함수)"""
        try:
            logging.info(f"🚀 {target_date} 테마 크롤링 시작...")

            # 1. 데이터베이스 설정
            self.db.setup_crawling_database()
            table_name = self.db.setup_theme_table(target_date)

            # 2. 테마 리스트 크롤링
            themes = self.get_theme_list()
            if not themes:
                logging.error("크롤링할 테마가 없습니다")
                return False

            logging.info(f"✅ {len(themes)}개 상승 테마 발견")

            # 3. 테마별 데이터 수집
            result = {}
            for i, theme in enumerate(themes):
                try:
                    theme_name = theme['name']
                    theme_code = theme['code']
                    change_rate = theme['change_rate']

                    logging.info(f"[{i + 1}/{len(themes)}] {theme_name} (+{change_rate}%) 처리 중...")

                    # 테마별 상위 5개 종목 + 전체 종목 정보 수집
                    top_stocks, all_theme_stocks = self.get_theme_stocks(theme_code, theme_name, limit=5)
                    if not top_stocks:
                        logging.warning(f"{theme_name}: 종목을 찾을 수 없음")
                        continue

                    logging.info(f"    📰 상위 {len(top_stocks)}개 종목의 뉴스 수집 시작...")

                    # 상위 5개 종목의 뉴스 수집
                    stocks_with_news = []
                    for j, stock in enumerate(top_stocks):
                        logging.info(f"       [{j + 1}/{len(top_stocks)}] {stock['name']} 뉴스 수집...")
                        stock_news = self.get_stock_news(stock['code'], stock['name'], limit=5)

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
                        'theme_stocks': all_theme_stocks
                    }

                    total_news = sum(len(stock['news']) for stock in stocks_with_news)
                    logging.info(f"    ✅ {theme_name} 완료: 상위 {len(stocks_with_news)}개 종목, {total_news}개 뉴스")

                    time.sleep(2)  # 테마 간 요청 간격

                except Exception as e:
                    logging.error(f"테마 {theme.get('name', 'Unknown')} 처리 실패: {e}")
                    continue

            # 4. DB 저장
            if result:
                success = self.db.save_theme_data(table_name, result)
                if success:
                    logging.info(f"🎯 {target_date} 테마 크롤링 완료!")
                    self._print_crawling_summary(result)
                    return True
                else:
                    logging.error("DB 저장 실패")
                    return False
            else:
                logging.error("크롤링 결과가 없습니다")
                return False

        except Exception as e:
            logging.error(f"테마 크롤링 실패: {e}")
            return False

    def get_theme_list(self) -> List[Dict]:
        """테마 리스트 크롤링"""
        url = "https://finance.naver.com/sise/theme.naver"

        try:
            response = requests.get(url, headers=self.session.headers, timeout=10)
            response.encoding = 'euc-kr'
            soup = BeautifulSoup(response.text, 'html.parser')

            table = soup.find('table', {'class': 'type_1'})
            if not table:
                return []

            themes = []
            rows = table.find_all('tr')[1:]  # 헤더 제외

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
                except Exception as e:
                    logging.error(f"테마 파싱 오류: {e}")
                    continue

            return themes

        except Exception as e:
            logging.error(f"테마 리스트 크롤링 실패: {e}")
            return []

    def get_theme_stocks(self, theme_code: str, theme_name: str, limit: int = 5) -> tuple:
        """특정 테마의 상위 종목 크롤링 + 테마 내 모든 종목 정보"""
        url = f"https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no={theme_code}"

        try:
            response = requests.get(url, headers=self.session.headers, timeout=15)
            response.encoding = 'euc-kr'
            soup = BeautifulSoup(response.text, 'html.parser')

            stock_links = soup.find_all('a', href=re.compile(r'/item/main\.naver\?code=\d{6}'))
            if not stock_links:
                return [], []

            # 모든 종목 정보 수집
            all_theme_stocks = []
            top_stocks = []
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

                    # 모든 종목 정보
                    theme_stock_info = {
                        'code': stock_code,
                        'name': stock_name,
                        'price': current_price,
                        'change_rate': change_rate,
                        'volume': volume
                    }
                    all_theme_stocks.append(theme_stock_info)

                    # 상위 종목들만 따로 저장
                    if len(top_stocks) < limit:
                        top_stocks.append({
                            'code': stock_code,
                            'name': stock_name,
                            'price': current_price,
                            'change_rate': change_rate,
                            'volume': volume
                        })

                except Exception as e:
                    logging.error(f"종목 파싱 오류: {e}")
                    continue

            logging.info(f"    ✅ {theme_name}: 상위 {len(top_stocks)}개 종목, 전체 {len(all_theme_stocks)}개 종목 정보 수집")
            return top_stocks, all_theme_stocks

        except Exception as e:
            logging.error(f"테마 종목 크롤링 실패 ({theme_name}): {e}")
            return [], []

    def get_stock_news(self, stock_code: str, stock_name: str, limit: int = 5) -> List[Dict]:
        """특정 종목의 뉴스 크롤링"""
        url = f"https://finance.naver.com/item/news_news.naver?code={stock_code}&page=1&sm=title_entity_id.basic&clusterId="

        try:
            response = requests.get(url, headers=self.session.headers, timeout=10)
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
                    # 날짜 행 확인
                    date_cell = row.find('td', {'class': 'date'})
                    if date_cell and date_cell.get('colspan'):
                        date_text = clean_text(date_cell.text)
                        current_date = parse_news_date(date_text)
                        continue

                    # 뉴스 제목 행
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

                    # 뉴스 출처
                    source_cell = row.find('td', {'class': 'info'})
                    source = clean_text(source_cell.text) if source_cell else ""

                    # 시간 정보
                    time_cell = row.find('td', {'class': 'date'})
                    news_time = current_date
                    if time_cell and not time_cell.get('colspan'):
                        time_text = clean_text(time_cell.text)
                        news_time = parse_news_time(time_text, current_date)

                    # 당일 또는 어제 뉴스만
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

                except Exception as e:
                    logging.error(f"뉴스 파싱 오류: {e}")
                    continue

            return news_list

        except Exception as e:
            logging.error(f"종목 뉴스 크롤링 실패 ({stock_name}): {e}")
            return []

    def _print_crawling_summary(self, result: Dict):
        """크롤링 결과 요약 출력"""
        total_themes = len(result)
        total_stocks = sum(len(data['stocks']) for data in result.values())
        total_news = sum(len(stock['news']) for data in result.values() for stock in data['stocks'])

        logging.info(f"\n🎯 크롤링 최종 결과:")
        logging.info(f"   📊 테마: {total_themes}개")
        logging.info(f"   📈 총 종목: {total_stocks}개")
        logging.info(f"   📰 총 뉴스: {total_news}개")
        logging.info(f"   ⚡ 평균 종목당 뉴스: {total_news / total_stocks:.1f}개" if total_stocks > 0 else "")

        logging.info(f"\n📊 테마별 상세:")
        for theme_name, data in result.items():
            stock_count = len(data['stocks'])
            news_count = sum(len(stock['news']) for stock in data['stocks'])
            logging.info(f"   {theme_name}: {stock_count}개 종목, {news_count}개 뉴스")