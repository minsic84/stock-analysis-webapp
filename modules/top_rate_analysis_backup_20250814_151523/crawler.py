#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
등락율상위분석 크롤러 (작동하는 paste.txt 기반으로 완전 재작성)
- 네이버 금융 테마별 상위 종목 크롤링
- 실시간 진행상황 추적
- 종목별 뉴스 수집
"""

import requests
from bs4 import BeautifulSoup
import time
import re
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from urllib.parse import urljoin

from .database import TopRateDatabase
from .utils import get_trading_date


class TopRateCrawler:
    """등락율상위분석 크롤러 (작동 검증된 코드 기반)"""

    def __init__(self, progress_callback: Optional[Callable] = None):
        """크롤러 초기화"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        self.db = TopRateDatabase()
        self.progress_callback = progress_callback

        # 크롤링 설정
        self.max_stocks_per_theme = 5  # 테마당 최대 종목 수
        self.news_per_stock = 5  # 종목당 뉴스 수
        self.request_delay = 0.8  # 요청 간 지연시간
        self.theme_delay = 2.0  # 테마 간 지연시간

    def crawl_and_save(self, target_date: Optional[str] = None) -> bool:
        """전체 크롤링 및 저장 프로세스"""
        start_time = datetime.now()

        if target_date is None:
            target_date = get_trading_date()

        logging.info(f"🚀 등락율상위분석 크롤링 시작 (날짜: {target_date})")

        try:
            # 1단계: 데이터베이스 설정
            self._update_progress(5, "데이터베이스 설정 중...")
            self.db.setup_crawling_database()
            table_name = self.db.setup_theme_table(target_date)

            # 2단계: 테마 리스트 크롤링
            self._update_progress(10, "테마 리스트 크롤링 중...")
            themes = self._get_theme_list()

            if not themes:
                logging.error("❌ 크롤링할 테마가 없습니다")
                return False

            logging.info(f"✅ {len(themes)}개 상승 테마 발견")

            # 3단계: 테마별 데이터 수집
            result = {}
            total_themes = len(themes)

            for i, theme in enumerate(themes):
                try:
                    # 진행상황 업데이트
                    progress = 15 + (70 * i / total_themes)  # 15% ~ 85%
                    message = f"{theme['name']} 테마 분석 중... ({i + 1}/{total_themes})"
                    self._update_progress(progress, message)

                    logging.info(f"[{i + 1}/{total_themes}] {theme['name']} (+{theme['change_rate']}%) 처리 중...")

                    # 테마별 종목 + 뉴스 수집
                    theme_data = self._process_theme(theme)

                    if theme_data:
                        result[theme['name']] = theme_data
                        stocks_count = len(theme_data['stocks'])
                        total_news = sum(len(stock['news']) for stock in theme_data['stocks'])
                        logging.info(f"    ✅ {theme['name']} 완료: {stocks_count}개 종목, {total_news}개 뉴스")
                    else:
                        logging.warning(f"    ❌ {theme['name']}: 데이터 수집 실패")

                    # 테마 간 지연
                    time.sleep(self.theme_delay)

                except Exception as e:
                    logging.error(f"    ❌ {theme['name']} 처리 실패: {e}")
                    continue

            if not result:
                logging.error("❌ 크롤링된 데이터가 없습니다")
                return False

            # 4단계: 데이터베이스 저장
            self._update_progress(90, "데이터베이스 저장 중...")

            # 데이터 변환 (기존 DB 저장 형식에 맞게)
            converted_data = self._convert_data_format(result)
            success = self.db.save_theme_data(table_name, converted_data)

            if success:
                self._update_progress(100, "크롤링 완료!")
                self._print_summary(result, target_date)

                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                logging.info(f"⚡ 전체 크롤링 완료: {duration:.1f}초 소요")

                return True
            else:
                logging.error("❌ 데이터베이스 저장 실패")
                return False

        except Exception as e:
            logging.error(f"❌ 크롤링 프로세스 실패: {e}")
            return False

    def _get_theme_list(self) -> List[Dict]:
        """테마 리스트 크롤링 (작동 검증된 코드)"""
        url = "https://finance.naver.com/sise/theme.naver"

        try:
            response = self.session.get(url, timeout=10)
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

                    theme_name = self._clean_text(theme_link.text)
                    theme_url = theme_link.get('href', '')
                    theme_code_match = re.search(r'no=(\d+)', theme_url)
                    theme_code = theme_code_match.group(1) if theme_code_match else ""
                    change_rate = self._parse_percentage(cols[3].text)

                    if theme_name and theme_code and change_rate > 0:
                        themes.append({
                            'name': theme_name,
                            'code': theme_code,
                            'change_rate': change_rate,
                            'url': f"https://finance.naver.com{theme_url}"
                        })

                except Exception:
                    continue

            return themes

        except Exception as e:
            logging.error(f"테마 리스트 크롤링 실패: {e}")
            return []

    def _process_theme(self, theme: Dict) -> Optional[Dict]:
        """테마별 종목 + 뉴스 처리 (작동 검증된 코드)"""
        theme_name = theme['name']
        theme_code = theme['code']

        # 종목 정보 수집
        top_stocks, all_theme_stocks = self._get_theme_stocks(theme_code, theme_name)
        if not top_stocks:
            return None

        # 뉴스 수집
        stocks_with_news = []
        for j, stock in enumerate(top_stocks):
            logging.info(f"       [{j + 1}/{len(top_stocks)}] {stock['name']} 뉴스 수집...")
            stock_news = self._get_stock_news(stock['code'], stock['name'])

            stock_data = stock.copy()
            stock_data['news'] = stock_news
            stocks_with_news.append(stock_data)

            time.sleep(self.request_delay)  # 종목 간 지연

        return {
            'theme_info': {
                'code': theme_code,
                'change_rate': theme['change_rate']
            },
            'stocks': stocks_with_news,
            'theme_stocks': all_theme_stocks
        }

    def _get_theme_stocks(self, theme_code: str, theme_name: str) -> tuple:
        """테마별 종목 수집 (작동 검증된 코드)"""
        url = f"https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no={theme_code}"

        try:
            response = self.session.get(url, timeout=15)
            response.encoding = 'euc-kr'
            soup = BeautifulSoup(response.text, 'html.parser')

            stock_links = soup.find_all('a', href=re.compile(r'/item/main\.naver\?code=\d{6}'))
            if not stock_links:
                return [], []

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

                    stock_name = self._clean_text(link.text)
                    if not stock_name or len(stock_name) < 2:
                        continue

                    # 가격/등락률/거래량 추출
                    row = link.find_parent('tr')
                    current_price = 0
                    change_rate = 0
                    volume = 0

                    if row:
                        cells = row.find_all('td')
                        for cell in cells:
                            cell_text = self._clean_text(cell.text)

                            # 가격 (1000 이상 숫자)
                            if cell_text.isdigit() and int(cell_text) >= 1000:
                                if current_price == 0:
                                    current_price = int(cell_text)

                            # 등락률 (% 포함)
                            if '%' in cell_text:
                                rate = self._parse_percentage(cell_text)
                                if abs(rate) < 100:
                                    change_rate = rate

                            # 거래량 (큰 숫자)
                            if cell_text.isdigit() and int(cell_text) > 10000:
                                if volume == 0 or int(cell_text) > volume:
                                    volume = int(cell_text)

                    stock_info = {
                        'code': stock_code,
                        'name': stock_name,
                        'price': current_price,
                        'change_rate': change_rate,
                        'volume': volume
                    }

                    all_theme_stocks.append(stock_info)

                    # 상위 종목만 따로 저장
                    if len(top_stocks) < self.max_stocks_per_theme:
                        top_stocks.append(stock_info)

                except Exception:
                    continue

            return top_stocks, all_theme_stocks

        except Exception as e:
            logging.error(f"테마 종목 수집 실패 ({theme_name}): {e}")
            return [], []

    def _get_stock_news(self, stock_code: str, stock_name: str) -> List[Dict]:
        """종목별 뉴스 수집 (작동 검증된 코드)"""
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
                    # 날짜 헤더 처리
                    date_cell = row.find('td', {'class': 'date'})
                    if date_cell and date_cell.get('colspan'):
                        date_text = self._clean_text(date_cell.text)
                        current_date = self._parse_news_date(date_text)
                        continue

                    # 뉴스 제목 추출
                    title_cell = row.find('td', {'class': 'title'})
                    if not title_cell:
                        continue

                    news_link = title_cell.find('a')
                    if not news_link:
                        continue

                    title = self._clean_text(news_link.text)
                    if not title:
                        continue

                    news_url = news_link.get('href', '')
                    if news_url and not news_url.startswith('http'):
                        news_url = urljoin('https://finance.naver.com', news_url)

                    # 출처 추출
                    source_cell = row.find('td', {'class': 'info'})
                    source = self._clean_text(source_cell.text) if source_cell else ""

                    # 시간 추출
                    time_cell = row.find('td', {'class': 'date'})
                    news_time = current_date
                    if time_cell and not time_cell.get('colspan'):
                        time_text = self._clean_text(time_cell.text)
                        news_time = self._parse_news_time(time_text, current_date)

                    # 당일/전일 뉴스만 수집
                    if news_time and (news_time.date() == today or news_time.date() == yesterday):
                        news_data = {
                            'title': title,
                            'url': news_url,
                            'source': source,
                            'time': news_time.strftime('%Y-%m-%d %H:%M') if news_time else '',
                            'is_today': news_time.date() == today if news_time else False
                        }

                        news_list.append(news_data)

                        if len(news_list) >= self.news_per_stock:
                            break

                except Exception:
                    continue

            return news_list

        except Exception as e:
            logging.warning(f"뉴스 수집 실패 ({stock_name}): {e}")
            return []

    def _convert_data_format(self, result: Dict) -> List[Dict]:
        """크롤링 결과를 DB 저장 형식으로 변환"""
        converted_data = []

        # 종목별로 데이터 정리 (중복 제거)
        stock_data = {}

        for theme_name, theme_data in result.items():
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
                        'theme_stocks': {}
                    }

                # 테마 추가 (중복 방지)
                if theme_name not in stock_data[stock_code]['themes']:
                    stock_data[stock_code]['themes'].append(theme_name)

                # 테마별 종목 정보 추가
                stock_data[stock_code]['theme_stocks'][theme_name] = theme_data['theme_stocks']

        # 리스트로 변환
        converted_data = list(stock_data.values())

        return converted_data

    def _update_progress(self, percent: float, message: str):
        """진행상황 업데이트"""
        if self.progress_callback:
            self.progress_callback(percent, message)
        logging.info(f"🔄 [{percent:.1f}%] {message}")

    def _print_summary(self, result: Dict, target_date: str):
        """크롤링 결과 요약 출력"""
        total_themes = len(result)
        total_stocks = sum(len(data['stocks']) for data in result.values())
        total_news = sum(len(stock['news']) for data in result.values() for stock in data['stocks'])

        logging.info(f"""
🎯 크롤링 결과 요약 ({target_date})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 총 테마: {total_themes}개
📈 총 종목: {total_stocks}개  
📰 총 뉴스: {total_news}개
⚡ 평균 뉴스/종목: {total_news / total_stocks:.1f}개
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""")

    # 유틸리티 함수들 (작동 검증된 코드)
    def _clean_text(self, text):
        """텍스트 정리"""
        if not text:
            return ""
        return text.strip().replace('\n', '').replace('\t', '').replace('\xa0', '').replace(',', '')

    def _parse_percentage(self, text):
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

    def _parse_news_date(self, date_text):
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

    def _parse_news_time(self, time_text, base_date):
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


# 진행상황 추적을 위한 전역 변수 (웹 인터페이스용)
crawling_progress = {
    'is_running': False,
    'percent': 0,
    'message': '',
    'start_time': None,
    'end_time': None,
    'success': None,
    'error_message': ''
}