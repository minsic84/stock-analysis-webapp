#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime
import re

from .models import SectorData, StockData
from common.utils import safe_request, clean_text, parse_number, parse_percentage


class NaverFinanceCrawler:
    """네이버 금융 크롤링 클래스"""

    BASE_URL = "https://finance.naver.com"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def crawl_top_sectors(self, limit: int = 5) -> List[SectorData]:
        """상위 업종 크롤링"""
        try:
            url = f"{self.BASE_URL}/sise/sise_group.naver?type=upjong"

            response = safe_request(url, headers=self.session.headers)
            if not response:
                raise Exception("업종 페이지 요청 실패")

            soup = BeautifulSoup(response.content, 'html.parser')

            # 업종 테이블 찾기
            table = soup.find('table', {'class': 'type_1'})
            if not table:
                raise Exception("업종 테이블을 찾을 수 없습니다")

            sectors = []
            rows = table.find('tbody').find_all('tr')

            for i, row in enumerate(rows[:limit]):
                try:
                    cols = row.find_all('td')
                    if len(cols) < 6:
                        continue

                    # 업종명 추출
                    sector_link = cols[0].find('a')
                    if not sector_link:
                        continue

                    sector_name = clean_text(sector_link.text)
                    sector_url = sector_link.get('href', '')

                    # 업종 코드 추출 (URL에서)
                    sector_code = self._extract_sector_code(sector_url)

                    # 현재가, 등락률 등 추출
                    current_value = parse_number(cols[1].text)
                    change_amount = parse_number(cols[2].text)
                    change_rate = parse_percentage(cols[3].text)
                    volume = parse_number(cols[4].text)

                    sector_data = SectorData(
                        sector_name=sector_name,
                        sector_code=sector_code,
                        current_value=current_value or 0,
                        change_amount=change_amount or 0,
                        change_rate=change_rate or 0,
                        volume=volume or 0
                    )

                    sectors.append(sector_data)
                    logging.info(f"업종 크롤링 완료: {sector_name} ({change_rate}%)")

                except Exception as e:
                    logging.error(f"업종 데이터 파싱 오류: {e}")
                    continue

            # 각 업종별 상위 3개 종목 크롤링
            for sector in sectors:
                try:
                    sector.top_stocks = self.crawl_sector_top_stocks(sector.sector_code, limit=3)
                    time.sleep(0.5)  # 요청 간격 조절
                except Exception as e:
                    logging.error(f"업종 {sector.sector_name} 종목 크롤링 실패: {e}")

            return sectors

        except Exception as e:
            logging.error(f"상위 업종 크롤링 실패: {e}")
            raise

    def crawl_sector_top_stocks(self, sector_code: str, limit: int = 3) -> List[StockData]:
        """특정 업종의 상위 종목 크롤링"""
        try:
            url = f"{self.BASE_URL}/sise/sise_group_detail.naver?type=upjong&no={sector_code}"

            response = safe_request(url, headers=self.session.headers)
            if not response:
                return []

            soup = BeautifulSoup(response.content, 'html.parser')

            # 종목 테이블 찾기
            table = soup.find('table', {'class': 'type_1'})
            if not table:
                return []

            stocks = []
            rows = table.find('tbody').find_all('tr')

            for row in rows[:limit]:
                try:
                    cols = row.find_all('td')
                    if len(cols) < 12:
                        continue

                    # 종목명과 코드 추출
                    stock_link = cols[1].find('a')
                    if not stock_link:
                        continue

                    stock_name = clean_text(stock_link.text)
                    stock_url = stock_link.get('href', '')
                    stock_code = self._extract_stock_code(stock_url)

                    if not stock_code:
                        continue

                    # 가격 정보 추출
                    current_price = parse_number(cols[2].text)
                    change_amount = parse_number(cols[3].text)
                    change_rate = parse_percentage(cols[4].text)
                    volume = parse_number(cols[5].text)
                    trading_value = parse_number(cols[6].text)

                    stock_data = StockData(
                        stock_code=stock_code,
                        stock_name=stock_name,
                        current_price=current_price or 0,
                        change_amount=change_amount or 0,
                        change_rate=change_rate or 0,
                        volume=volume or 0,
                        trading_value=trading_value or 0
                    )

                    stocks.append(stock_data)
                    logging.info(f"종목 크롤링 완료: {stock_name} ({stock_code})")

                except Exception as e:
                    logging.error(f"종목 데이터 파싱 오류: {e}")
                    continue

            return stocks

        except Exception as e:
            logging.error(f"업종 종목 크롤링 실패: {e}")
            return []

    def crawl_all_sector_stocks(self, sector_code: str) -> List[StockData]:
        """특정 업종의 모든 종목 크롤링 (신고가 분석용)"""
        try:
            all_stocks = []
            page = 1

            while True:
                url = f"{self.BASE_URL}/sise/sise_group_detail.naver?type=upjong&no={sector_code}&page={page}"

                response = safe_request(url, headers=self.session.headers)
                if not response:
                    break

                soup = BeautifulSoup(response.content, 'html.parser')
                table = soup.find('table', {'class': 'type_1'})

                if not table:
                    break

                rows = table.find('tbody').find_all('tr')
                if not rows:
                    break

                page_stocks = []
                for row in rows:
                    try:
                        cols = row.find_all('td')
                        if len(cols) < 12:
                            continue

                        stock_link = cols[1].find('a')
                        if not stock_link:
                            continue

                        stock_name = clean_text(stock_link.text)
                        stock_url = stock_link.get('href', '')
                        stock_code = self._extract_stock_code(stock_url)

                        if not stock_code:
                            continue

                        current_price = parse_number(cols[2].text)
                        change_rate = parse_percentage(cols[4].text)
                        volume = parse_number(cols[5].text)

                        stock_data = StockData(
                            stock_code=stock_code,
                            stock_name=stock_name,
                            current_price=current_price or 0,
                            change_rate=change_rate or 0,
                            volume=volume or 0
                        )

                        page_stocks.append(stock_data)

                    except Exception as e:
                        logging.error(f"종목 파싱 오류: {e}")
                        continue

                if not page_stocks:
                    break

                all_stocks.extend(page_stocks)
                page += 1
                time.sleep(0.3)  # 페이지 간 요청 간격

                # 최대 10페이지까지만 크롤링
                if page > 10:
                    break

            logging.info(f"업종 전체 종목 크롤링 완료: {len(all_stocks)}개")
            return all_stocks

        except Exception as e:
            logging.error(f"업종 전체 종목 크롤링 실패: {e}")
            return []

    def crawl_rising_stocks(self, limit: int = 50) -> List[StockData]:
        """상승률 상위 종목 크롤링"""
        try:
            url = f"{self.BASE_URL}/sise/sise_rise.naver"

            response = safe_request(url, headers=self.session.headers)
            if not response:
                logging.error("상승률 페이지 요청 실패")
                return []

            soup = BeautifulSoup(response.content, 'html.parser')

            # 디버깅을 위한 HTML 출력
            logging.info(f"응답 상태코드: {response.status_code}")
            logging.info(f"페이지 제목: {soup.title.text if soup.title else 'No title'}")

            table = soup.find('table', {'class': 'type_2'})
            if not table:
                # 다른 클래스명 시도
                table = soup.find('table', {'summary': '거래량상위'})
                if not table:
                    logging.error("상승률 테이블을 찾을 수 없습니다")
                    # HTML 구조 디버깅
                    tables = soup.find_all('table')
                    logging.info(f"페이지에서 발견된 테이블 수: {len(tables)}")
                    return []

            stocks = []
            rows = table.find('tbody').find_all('tr') if table.find('tbody') else table.find_all('tr')

            logging.info(f"발견된 행 수: {len(rows)}")

            for i, row in enumerate(rows[:limit]):
                try:
                    cols = row.find_all('td')
                    if len(cols) < 6:
                        continue

                    # 종목명과 링크 찾기
                    stock_link = None
                    stock_name = ""

                    # 여러 컬럼에서 종목 링크 찾기
                    for col in cols:
                        link = col.find('a')
                        if link and 'item/main.naver' in link.get('href', ''):
                            stock_link = link
                            stock_name = clean_text(link.text)
                            break

                    if not stock_link or not stock_name:
                        continue

                    stock_url = stock_link.get('href', '')
                    stock_code = self._extract_stock_code(stock_url)

                    if not stock_code:
                        continue

                    # 가격 정보 추출 (더 유연한 방식)
                    current_price = 0
                    change_rate = 0
                    volume = 0

                    for col in cols:
                        text = clean_text(col.text)
                        if text and text.replace(',', '').replace('+', '').replace('-', '').replace('%', '').replace(
                                '.', '').isdigit():
                            if '%' in text:
                                change_rate = parse_percentage(text) or 0
                            elif ',' in text and len(text) > 3:
                                if current_price == 0:
                                    current_price = parse_number(text) or 0
                                elif volume == 0:
                                    volume = parse_number(text) or 0

                    stock_data = StockData(
                        stock_code=stock_code,
                        stock_name=stock_name,
                        current_price=current_price,
                        change_rate=change_rate,
                        volume=volume
                    )

                    stocks.append(stock_data)
                    logging.info(f"종목 파싱 성공: {stock_name} ({stock_code}) - {change_rate}%")

                except Exception as e:
                    logging.error(f"상승률 종목 파싱 오류 (행 {i}): {e}")
                    continue

            logging.info(f"상승률 상위 종목 크롤링 완료: {len(stocks)}개")
            return stocks

        except Exception as e:
            logging.error(f"상승률 상위 종목 크롤링 실패: {e}")
            return []

    def _extract_sector_code(self, url: str) -> str:
        """URL에서 업종 코드 추출"""
        if not url:
            return ""

        # no= 파라미터에서 업종 코드 추출
        match = re.search(r'no=(\d+)', url)
        return match.group(1) if match else ""

    def _extract_stock_code(self, url: str) -> str:
        """URL에서 종목 코드 추출"""
        if not url:
            return ""

        # code= 파라미터에서 종목 코드 추출
        match = re.search(r'code=(\d{6})', url)
        return match.group(1) if match else ""

    def get_stock_basic_info(self, stock_code: str) -> Optional[Dict]:
        """종목 기본 정보 조회"""
        try:
            url = f"{self.BASE_URL}/item/main.naver?code={stock_code}"

            response = safe_request(url, headers=self.session.headers)
            if not response:
                return None

            soup = BeautifulSoup(response.content, 'html.parser')

            # 종목명
            stock_name_elem = soup.find('div', {'class': 'wrap_company'})
            stock_name = ""
            if stock_name_elem:
                name_elem = stock_name_elem.find('h2')
                if name_elem:
                    stock_name = clean_text(name_elem.text)

            # 현재가 정보
            price_elem = soup.find('p', {'class': 'no_today'})
            current_price = 0
            if price_elem:
                price_span = price_elem.find('span', {'class': 'blind'})
                if price_span:
                    current_price = parse_number(price_span.text) or 0

            # 등락률 정보
            change_elem = soup.find('p', {'class': 'no_exday'})
            change_rate = 0
            if change_elem:
                rate_span = change_elem.find('span', {'class': 'blind'})
                if rate_span:
                    change_rate = parse_percentage(rate_span.text) or 0

            return {
                'stock_code': stock_code,
                'stock_name': stock_name,
                'current_price': current_price,
                'change_rate': change_rate
            }

        except Exception as e:
            logging.error(f"종목 기본 정보 조회 실패 ({stock_code}): {e}")
            return None