#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
등락율상위분석 크롤러 (theme_crawler_test.py 기반)
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
from datetime import datetime
from typing import List, Dict, Optional, Callable
from urllib.parse import urljoin

from .database import TopRateDatabase
from .utils import (
    get_trading_date, clean_text, parse_percentage,
    parse_number, safe_request, get_default_headers,
    format_progress_message, log_performance
)


class TopRateCrawler:
    """등락율상위분석 크롤러"""

    def __init__(self, progress_callback: Optional[Callable] = None):
        """
        크롤러 초기화

        Args:
            progress_callback: 진행상황 콜백 함수 (percent, message)
        """
        self.session = requests.Session()
        self.session.headers.update(get_default_headers())

        self.db = TopRateDatabase()
        self.progress_callback = progress_callback

        # 크롤링 설정
        self.max_stocks_per_theme = 5  # 테마당 최대 종목 수
        self.request_delay = 0.5  # 요청 간 지연시간 (초)
        self.max_retry = 3  # 최대 재시도 횟수

    def crawl_and_save(self, target_date: Optional[str] = None) -> bool:
        """
        전체 크롤링 및 저장 프로세스

        Args:
            target_date: 대상 날짜 (None이면 거래일 기준 자동 계산)

        Returns:
            성공 여부
        """
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

            # 3단계: 테마별 종목 크롤링
            self._update_progress(15, f"{len(themes)}개 테마 분석 시작...")
            all_stock_data = []

            for i, theme in enumerate(themes):
                try:
                    progress = 15 + (70 * (i + 1) / len(themes))  # 15% ~ 85%
                    message = f"{theme['name']} 테마 분석 중... ({i + 1}/{len(themes)})"
                    self._update_progress(progress, message)

                    # 테마별 종목 크롤링
                    theme_stocks = self._get_theme_stocks(
                        theme['code'],
                        theme['name'],
                        limit=self.max_stocks_per_theme
                    )

                    if theme_stocks:
                        all_stock_data.extend(theme_stocks)
                        logging.info(f"  ✅ {theme['name']}: {len(theme_stocks)}개 종목")

                    # 요청 간 지연
                    time.sleep(self.request_delay)

                except Exception as e:
                    logging.error(f"  ❌ {theme['name']} 크롤링 실패: {e}")
                    continue

            if not all_stock_data:
                logging.error("❌ 크롤링된 종목이 없습니다")
                return False

            # 4단계: 종목별 뉴스 수집
            self._update_progress(85, f"{len(all_stock_data)}개 종목 뉴스 수집 중...")
            self._collect_stock_news(all_stock_data)

            # 5단계: 데이터베이스 저장
            self._update_progress(95, "데이터베이스 저장 중...")
            success = self.db.save_theme_data(table_name, all_stock_data)

            if success:
                self._update_progress(100, "크롤링 완료!")
                self._print_crawling_summary(all_stock_data, target_date)

                # 성능 로그
                end_time = datetime.now()
                log_performance("전체 크롤링", start_time, end_time, len(all_stock_data))

                return True
            else:
                logging.error("❌ 데이터베이스 저장 실패")
                return False

        except Exception as e:
            logging.error(f"❌ 크롤링 프로세스 실패: {e}")
            return False

    def _get_theme_list(self) -> List[Dict]:
        """
        네이버 금융에서 상승 테마 리스트 크롤링

        Returns:
            테마 정보 리스트
        """
        url = "https://finance.naver.com/sise/theme.naver"

        for attempt in range(self.max_retry):
            try:
                response = safe_request(url, timeout=10)
                if not response:
                    continue

                response.encoding = 'euc-kr'
                soup = BeautifulSoup(response.text, 'html.parser')

                table = soup.find('table', {'class': 'type_1'})
                if not table:
                    logging.warning("테마 테이블을 찾을 수 없습니다")
                    continue

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

                        # 상승 테마만 수집
                        if theme_name and theme_code and change_rate > 0:
                            themes.append({
                                'name': theme_name,
                                'code': theme_code,
                                'change_rate': change_rate,
                                'url': f"https://finance.naver.com{theme_url}"
                            })

                    except Exception as e:
                        logging.warning(f"테마 파싱 오류: {e}")
                        continue

                if themes:
                    logging.info(f"✅ 테마 리스트 수집 완료: {len(themes)}개")
                    return sorted(themes, key=lambda x: x['change_rate'], reverse=True)

            except Exception as e:
                logging.error(f"테마 리스트 크롤링 시도 {attempt + 1} 실패: {e}")
                if attempt < self.max_retry - 1:
                    time.sleep(1)
                    continue

        logging.error("❌ 테마 리스트 크롤링 완전 실패")
        return []

    def _get_theme_stocks(self, theme_code: str, theme_name: str, limit: int = 5) -> List[Dict]:
        """
        특정 테마의 상위 종목 크롤링

        Args:
            theme_code: 테마 코드
            theme_name: 테마명
            limit: 수집할 종목 수

        Returns:
            종목 정보 리스트
        """
        url = f"https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no={theme_code}"

        for attempt in range(self.max_retry):
            try:
                response = safe_request(url, timeout=10)
                if not response:
                    continue

                response.encoding = 'euc-kr'
                soup = BeautifulSoup(response.text, 'html.parser')

                # 종목 테이블 찾기
                table = soup.find('table', {'class': 'type_1'})
                if not table:
                    logging.warning(f"  {theme_name}: 종목 테이블을 찾을 수 없습니다")
                    continue

                stocks = []
                rows = table.find_all('tr')[1:]  # 헤더 제외

                for i, row in enumerate(rows):
                    if i >= limit:  # 상위 N개만
                        break

                    try:
                        cols = row.find_all('td')
                        if len(cols) < 6:
                            continue

                        # 종목명 및 코드
                        stock_link = cols[0].find('a')
                        if not stock_link:
                            continue

                        stock_name = clean_text(stock_link.text)
                        stock_href = stock_link.get('href', '')
                        stock_code_match = re.search(r'code=(\d{6})', stock_href)
                        stock_code = stock_code_match.group(1) if stock_code_match else ""

                        if not stock_code:
                            continue

                        # 가격 정보
                        price = parse_number(cols[1].text) or 0
                        change_rate = parse_percentage(cols[3].text)
                        volume = parse_number(cols[5].text) or 0

                        # 테마 내 전체 종목 정보도 수집
                        theme_stocks_info = self._get_all_theme_stocks(soup, theme_name)

                        stock_data = {
                            'stock_code': stock_code,
                            'stock_name': stock_name,
                            'price': price,
                            'change_rate': change_rate,
                            'volume': volume,
                            'themes': [theme_name],  # 주 테마
                            'news': [],  # 뉴스는 나중에 수집
                            'theme_stocks': {theme_name: theme_stocks_info}
                        }

                        stocks.append(stock_data)

                    except Exception as e:
                        logging.warning(f"  {theme_name} 종목 파싱 오류: {e}")
                        continue

                if stocks:
                    return stocks

            except Exception as e:
                logging.error(f"  {theme_name} 크롤링 시도 {attempt + 1} 실패: {e}")
                if attempt < self.max_retry - 1:
                    time.sleep(1)
                    continue

        logging.error(f"  ❌ {theme_name} 크롤링 완전 실패")
        return []

    def _get_all_theme_stocks(self, soup: BeautifulSoup, theme_name: str) -> List[Dict]:
        """
        테마 내 전체 종목 정보 수집

        Args:
            soup: BeautifulSoup 객체
            theme_name: 테마명

        Returns:
            전체 종목 정보 리스트
        """
        try:
            table = soup.find('table', {'class': 'type_1'})
            if not table:
                return []

            all_stocks = []
            rows = table.find_all('tr')[1:]  # 헤더 제외

            for row in rows:
                try:
                    cols = row.find_all('td')
                    if len(cols) < 6:
                        continue

                    stock_link = cols[0].find('a')
                    if not stock_link:
                        continue

                    stock_name = clean_text(stock_link.text)
                    stock_href = stock_link.get('href', '')
                    stock_code_match = re.search(r'code=(\d{6})', stock_href)
                    stock_code = stock_code_match.group(1) if stock_code_match else ""

                    if stock_code:
                        price = parse_number(cols[1].text) or 0
                        change_rate = parse_percentage(cols[3].text)

                        all_stocks.append({
                            'stock_code': stock_code,
                            'stock_name': stock_name,
                            'price': price,
                            'change_rate': change_rate
                        })

                except Exception:
                    continue

            return all_stocks

        except Exception as e:
            logging.warning(f"  {theme_name} 전체 종목 수집 실패: {e}")
            return []

    def _collect_stock_news(self, stock_data: List[Dict]) -> None:
        """
        종목별 뉴스 수집

        Args:
            stock_data: 종목 데이터 리스트 (뉴스가 추가됨)
        """
        for i, stock in enumerate(stock_data):
            try:
                # 진행상황 업데이트
                if i % 5 == 0:  # 5개마다 업데이트
                    progress = 85 + (10 * i / len(stock_data))
                    message = f"{stock['stock_name']} 뉴스 수집 중... ({i + 1}/{len(stock_data)})"
                    self._update_progress(progress, message)

                news = self._get_stock_news(stock['stock_code'])
                stock['news'] = news[:5]  # 최대 5개 뉴스

                # 요청 간 지연
                time.sleep(0.3)

            except Exception as e:
                logging.warning(f"  {stock['stock_name']} 뉴스 수집 실패: {e}")
                stock['news'] = []
                continue

    def _get_stock_news(self, stock_code: str) -> List[Dict]:
        """
        개별 종목의 뉴스 수집

        Args:
            stock_code: 종목 코드

        Returns:
            뉴스 리스트
        """
        url = f"https://finance.naver.com/item/news_news.naver?code={stock_code}&page=1"

        try:
            response = safe_request(url, timeout=5)
            if not response:
                return []

            response.encoding = 'euc-kr'
            soup = BeautifulSoup(response.text, 'html.parser')

            news_list = []
            news_table = soup.find('table', {'class': 'type5'})

            if news_table:
                news_rows = news_table.find_all('tr')

                for row in news_rows:
                    try:
                        title_cell = row.find('td', {'class': 'title'})
                        if not title_cell:
                            continue

                        title_link = title_cell.find('a')
                        if not title_link:
                            continue

                        title = clean_text(title_link.text)
                        if not title:
                            continue

                        # 날짜 정보
                        date_cell = row.find('td', {'class': 'date'})
                        date_text = clean_text(date_cell.text) if date_cell else ""

                        # 뉴스 URL
                        news_url = title_link.get('href', '')
                        if news_url and not news_url.startswith('http'):
                            news_url = urljoin('https://finance.naver.com', news_url)

                        news_list.append({
                            'title': title,
                            'date': date_text,
                            'url': news_url
                        })

                        if len(news_list) >= 5:  # 최대 5개
                            break

                    except Exception:
                        continue

            return news_list

        except Exception as e:
            logging.warning(f"종목 {stock_code} 뉴스 수집 실패: {e}")
            return []

    def _update_progress(self, percent: float, message: str) -> None:
        """
        진행상황 업데이트

        Args:
            percent: 진행 퍼센트 (0-100)
            message: 진행 메시지
        """
        if self.progress_callback:
            self.progress_callback(percent, message)

        logging.info(f"🔄 [{percent:.1f}%] {message}")

    def _print_crawling_summary(self, stock_data: List[Dict], target_date: str) -> None:
        """
        크롤링 결과 요약 출력

        Args:
            stock_data: 수집된 종목 데이터
            target_date: 수집 날짜
        """
        if not stock_data:
            return

        # 테마별 통계
        theme_stats = {}
        total_news = 0

        for stock in stock_data:
            themes = stock.get('themes', [])
            news_count = len(stock.get('news', []))
            total_news += news_count

            for theme in themes:
                if theme not in theme_stats:
                    theme_stats[theme] = {'stocks': 0, 'news': 0}
                theme_stats[theme]['stocks'] += 1
                theme_stats[theme]['news'] += news_count

        logging.info(f"""
🎯 크롤링 결과 요약 ({target_date})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 총 종목: {len(stock_data)}개
📰 총 뉴스: {total_news}개
🏷️ 테마 수: {len(theme_stats)}개
⚡ 평균 뉴스/종목: {total_news / len(stock_data):.1f}개

📋 테마별 상세:""")

        for theme, stats in sorted(theme_stats.items(), key=lambda x: x[1]['stocks'], reverse=True):
            logging.info(f"   {theme}: {stats['stocks']}개 종목, {stats['news']}개 뉴스")

        logging.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


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