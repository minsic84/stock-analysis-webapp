#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import re
from urllib.parse import urljoin, quote

from .models import NewsData, StockData
from common.utils import safe_request, clean_text, get_news_time_display


class NewsCrawler:
    """뉴스 크롤링 클래스"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Referer': 'https://finance.naver.com/',
        })

    def crawl_stock_news(self, stock_data: StockData, limit: int = 3) -> List[NewsData]:
        """특정 종목의 뉴스 크롤링"""
        try:
            # 네이버 금융 종목 뉴스 페이지
            url = f"https://finance.naver.com/item/news_news.naver?code={stock_data.stock_code}&page=1&sm=title_entity_id.basic&clusterId="

            response = safe_request(url, headers=self.session.headers)
            if not response:
                logging.error(f"뉴스 페이지 요청 실패: {stock_data.stock_name}")
                return []

            soup = BeautifulSoup(response.content, 'html.parser')

            # 뉴스 리스트 테이블 찾기
            news_table = soup.find('table', {'class': 'type5'})
            if not news_table:
                logging.warning(f"뉴스 테이블을 찾을 수 없습니다: {stock_data.stock_name}")
                return []

            news_list = []
            rows = news_table.find_all('tr')

            current_date = None
            for row in rows:
                try:
                    # 날짜 행 확인
                    date_cell = row.find('td', {'class': 'date'})
                    if date_cell and date_cell.get('colspan'):
                        date_text = clean_text(date_cell.text)
                        current_date = self._parse_news_date(date_text)
                        continue

                    # 뉴스 제목 행
                    title_cell = row.find('td', {'class': 'title'})
                    if not title_cell:
                        continue

                    # 뉴스 링크와 제목 추출
                    news_link = title_cell.find('a')
                    if not news_link:
                        continue

                    title = clean_text(news_link.text)
                    if not title:
                        continue

                    # 뉴스 URL 생성
                    news_url = news_link.get('href', '')
                    if news_url and not news_url.startswith('http'):
                        news_url = urljoin('https://finance.naver.com', news_url)

                    # 뉴스 출처 추출
                    source_cell = row.find('td', {'class': 'info'})
                    source = ""
                    if source_cell:
                        source = clean_text(source_cell.text)

                    # 시간 정보 추출
                    time_cell = row.find('td', {'class': 'date'})
                    news_time = current_date
                    if time_cell and not time_cell.get('colspan'):
                        time_text = clean_text(time_cell.text)
                        news_time = self._parse_news_time(time_text, current_date)

                    # 당일 뉴스만 필터링
                    is_today = self._is_today_news(news_time)

                    # 뉴스 데이터 생성
                    news_data = NewsData(
                        title=title,
                        url=news_url,
                        source=source,
                        published_at=news_time or datetime.now(),
                        is_today=is_today
                    )

                    # 키워드 추출
                    news_data.keywords = self._extract_keywords(title)

                    news_list.append(news_data)

                    # 당일 뉴스 중 limit 개수만 수집
                    today_news_count = len([n for n in news_list if n.is_today])
                    if today_news_count >= limit:
                        break

                except Exception as e:
                    logging.error(f"뉴스 파싱 오류: {e}")
                    continue

            # 당일 뉴스만 필터링하여 반환
            today_news = [news for news in news_list if news.is_today][:limit]

            logging.info(f"{stock_data.stock_name} 뉴스 크롤링 완료: {len(today_news)}개")
            return today_news

        except Exception as e:
            logging.error(f"종목 뉴스 크롤링 실패 ({stock_data.stock_name}): {e}")
            return []

    def crawl_multiple_stocks_news(self, stocks: List[StockData], limit_per_stock: int = 3) -> Dict[
        str, List[NewsData]]:
        """여러 종목의 뉴스를 일괄 크롤링"""
        news_dict = {}

        for i, stock in enumerate(stocks):
            try:
                news_list = self.crawl_stock_news(stock, limit_per_stock)
                news_dict[stock.stock_code] = news_list

                # 요청 간격 조절
                if i < len(stocks) - 1:
                    time.sleep(0.5)

            except Exception as e:
                logging.error(f"종목 뉴스 크롤링 실패 ({stock.stock_name}): {e}")
                news_dict[stock.stock_code] = []

        total_news = sum(len(news_list) for news_list in news_dict.values())
        logging.info(f"전체 뉴스 크롤링 완료: {len(stocks)}개 종목, {total_news}개 뉴스")

        return news_dict

    def get_news_content(self, news_url: str) -> Optional[str]:
        """뉴스 본문 내용 추출"""
        try:
            response = safe_request(news_url, headers=self.session.headers)
            if not response:
                return None

            soup = BeautifulSoup(response.content, 'html.parser')

            # 뉴스 본문 찾기 (여러 패턴 시도)
            content_selectors = [
                'div.newsct_article',
                'div.article_body',
                'div.news_body',
                'div.article-body',
                'div#articleBodyContents'
            ]

            content = ""
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    content = clean_text(content_elem.get_text())
                    break

            return content[:1000] if content else None  # 최대 1000자

        except Exception as e:
            logging.error(f"뉴스 본문 추출 실패 ({news_url}): {e}")
            return None

    def _parse_news_date(self, date_text: str) -> Optional[datetime]:
        """뉴스 날짜 파싱"""
        try:
            # "2025.08.12" 형태
            if '.' in date_text:
                date_parts = date_text.split('.')
                if len(date_parts) == 3:
                    year = int(date_parts[0])
                    month = int(date_parts[1])
                    day = int(date_parts[2])
                    return datetime(year, month, day)

            # "오늘", "어제" 등의 상대적 표현
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            if '오늘' in date_text:
                return today
            elif '어제' in date_text:
                return today - timedelta(days=1)
            elif '그제' in date_text:
                return today - timedelta(days=2)

            return today

        except Exception as e:
            logging.error(f"날짜 파싱 오류: {date_text}, {e}")
            return datetime.now()

    def _parse_news_time(self, time_text: str, base_date: datetime) -> Optional[datetime]:
        """뉴스 시간 파싱"""
        try:
            if not base_date:
                base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            # "09:30" 형태의 시간
            time_match = re.search(r'(\d{1,2}):(\d{2})', time_text)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
                return base_date.replace(hour=hour, minute=minute)

            return base_date

        except Exception as e:
            logging.error(f"시간 파싱 오류: {time_text}, {e}")
            return base_date

    def _is_today_news(self, news_time: Optional[datetime]) -> bool:
        """당일 뉴스 여부 확인"""
        if not news_time:
            return False

        today = datetime.now().date()
        return news_time.date() == today

    def _extract_keywords(self, title: str) -> List[str]:
        """뉴스 제목에서 키워드 추출"""
        if not title:
            return []

        # AI 분석용 중요 키워드들
        keywords = []

        # 혁신/글로벌 키워드
        innovation_keywords = ['AI', '인공지능', '혁신', '시대개막', '세계최초', '글로벌', '해외진출', 'K푸드']
        for keyword in innovation_keywords:
            if keyword in title:
                keywords.append(keyword)

        # 실적 관련 키워드
        performance_keywords = ['실적', '매출', '영업이익', '순이익', '증가', '급증', '성장', '호조']
        for keyword in performance_keywords:
            if keyword in title:
                keywords.append('대박실적')
                break

        # 규제/승인 키워드
        approval_keywords = ['FDA', '승인', '허가', '임상', '특허', '기술이전']
        for keyword in approval_keywords:
            if keyword in title:
                keywords.append('FDA승인')
                break

        # 대기업/투자 키워드
        investment_keywords = ['투자', '협업', '계약', '파트너십', 'MOU', '테슬라', '애플', '구글', '마이크로소프트']
        for keyword in investment_keywords:
            if keyword in title:
                keywords.append('글로벌대기업')
                break

        # 조 단위 키워드
        if '조' in title and any(char.isdigit() for char in title):
            keywords.append('조단위이슈')

        return list(set(keywords))  # 중복 제거

    def search_news_by_keyword(self, keyword: str, limit: int = 10) -> List[NewsData]:
        """키워드로 뉴스 검색"""
        try:
            # 네이버 뉴스 검색 API 또는 웹 검색 사용
            encoded_keyword = quote(keyword)
            url = f"https://search.naver.com/search.naver?where=news&query={encoded_keyword}&sort=1"  # 최신순

            response = safe_request(url, headers=self.session.headers)
            if not response:
                return []

            soup = BeautifulSoup(response.content, 'html.parser')

            news_list = []
            # 뉴스 검색 결과 파싱 로직 구현
            # (네이버 검색 결과 구조에 따라 수정 필요)

            return news_list[:limit]

        except Exception as e:
            logging.error(f"키워드 뉴스 검색 실패 ({keyword}): {e}")
            return []