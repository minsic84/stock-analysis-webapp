#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
등락율상위분석 유틸리티 함수들
- 거래일 기준 날짜 처리 (오전 8시 기준)
- 텍스트 정리 및 파싱 함수
- 크롤링 관련 헬퍼 함수
"""

import re
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging


def get_trading_date(target_time: Optional[datetime] = None) -> str:
    """
    거래일 기준 날짜 반환

    Args:
        target_time: 기준 시간 (None이면 현재 시간)

    Returns:
        YYYY-MM-DD 형식의 거래일 날짜

    Rule:
        00:00 ~ 07:59 → 전날 데이터
        08:00 ~ 23:59 → 당일 데이터
    """
    if target_time is None:
        target_time = datetime.now()

    if target_time.hour < 8:  # 오전 8시 이전
        trading_date = target_time - timedelta(days=1)
    else:
        trading_date = target_time

    return trading_date.strftime('%Y-%m-%d')


def get_table_name(date_str: str) -> str:
    """
    날짜 문자열을 DB 테이블명으로 변환

    Args:
        date_str: YYYY-MM-DD 형식의 날짜

    Returns:
        theme_YYYYMMDD 형식의 테이블명
    """
    clean_date = date_str.replace('-', '')
    return f"theme_{clean_date}"


def clean_text(text: str) -> str:
    """
    텍스트 정리 (공백, 특수문자 제거)

    Args:
        text: 정리할 텍스트

    Returns:
        정리된 텍스트
    """
    if not text:
        return ""

    # HTML 태그 제거
    text = re.sub(r'<[^>]+>', '', text)

    # 연속된 공백을 하나로
    text = re.sub(r'\s+', ' ', text)

    # 앞뒤 공백 제거
    return text.strip()


def parse_number(text: str) -> Optional[int]:
    """
    텍스트에서 숫자 추출

    Args:
        text: 숫자가 포함된 텍스트

    Returns:
        추출된 숫자 (추출 실패시 None)
    """
    if not text:
        return None

    # 콤마 제거 후 숫자만 추출
    number_str = re.sub(r'[^\d]', '', str(text))

    try:
        return int(number_str) if number_str else None
    except ValueError:
        return None


def parse_percentage(text: str) -> float:
    """
    텍스트에서 퍼센트 값 추출

    Args:
        text: 퍼센트가 포함된 텍스트 (예: "+5.67%")

    Returns:
        퍼센트 값 (float)
    """
    if not text:
        return 0.0

    # %기호 제거하고 숫자만 추출
    clean_text_str = str(text).replace('%', '').replace(',', '').strip()

    try:
        return float(clean_text_str)
    except ValueError:
        return 0.0


def safe_request(url: str, headers: Dict = None, timeout: int = 10) -> Optional[requests.Response]:
    """
    안전한 HTTP 요청

    Args:
        url: 요청할 URL
        headers: 요청 헤더
        timeout: 타임아웃 (초)

    Returns:
        응답 객체 (실패시 None)
    """
    if headers is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        logging.error(f"HTTP 요청 실패 ({url}): {e}")
        return None


def group_themes_by_name(theme_data: List[Dict]) -> Dict[str, List[Dict]]:
    """
    테마 데이터를 테마명으로 그룹화

    Args:
        theme_data: 테마 데이터 리스트

    Returns:
        테마명별로 그룹화된 딕셔너리
    """
    grouped = {}

    for item in theme_data:
        theme_name = item.get('theme_name', '기타')
        if theme_name not in grouped:
            grouped[theme_name] = []
        grouped[theme_name].append(item)

    return grouped


def calculate_theme_stats(stocks: List[Dict]) -> Dict:
    """
    테마 내 종목들의 통계 계산

    Args:
        stocks: 종목 데이터 리스트

    Returns:
        통계 정보 딕셔너리
    """
    if not stocks:
        return {
            'stock_count': 0,
            'avg_change_rate': 0.0,
            'rising_stocks': 0,
            'max_change_rate': 0.0,
            'top_stock': None
        }

    change_rates = [stock.get('change_rate', 0) for stock in stocks]
    rising_count = len([rate for rate in change_rates if rate > 0])

    # 최고 상승률 종목 찾기
    top_stock = max(stocks, key=lambda x: x.get('change_rate', 0))

    return {
        'stock_count': len(stocks),
        'avg_change_rate': sum(change_rates) / len(change_rates),
        'rising_stocks': rising_count,
        'max_change_rate': max(change_rates),
        'top_stock': {
            'name': top_stock.get('stock_name', ''),
            'change_rate': top_stock.get('change_rate', 0)
        }
    }


def format_progress_message(current: int, total: int, current_item: str) -> str:
    """
    진행상황 메시지 포맷팅

    Args:
        current: 현재 진행 수
        total: 전체 수
        current_item: 현재 처리 중인 항목명

    Returns:
        포맷된 진행상황 메시지
    """
    percentage = (current / total * 100) if total > 0 else 0
    return f"{current_item} 처리 중... ({current}/{total}, {percentage:.1f}%)"


def get_default_headers() -> Dict[str, str]:
    """
    크롤링용 기본 헤더 반환

    Returns:
        기본 HTTP 헤더 딕셔너리
    """
    return {
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
    }


def validate_stock_code(stock_code: str) -> bool:
    """
    종목코드 유효성 검증

    Args:
        stock_code: 검증할 종목코드

    Returns:
        유효성 여부 (True/False)
    """
    if not stock_code:
        return False

    # 한국 종목코드는 6자리 숫자
    return bool(re.match(r'^\d{6}$', stock_code.strip()))


def log_performance(func_name: str, start_time: datetime, end_time: datetime, item_count: int = 0):
    """
    성능 로그 기록

    Args:
        func_name: 함수명
        start_time: 시작 시간
        end_time: 종료 시간
        item_count: 처리한 항목 수
    """
    duration = (end_time - start_time).total_seconds()

    if item_count > 0:
        rate = item_count / duration if duration > 0 else 0
        logging.info(f"⚡ {func_name}: {duration:.2f}초, {item_count}개 처리 ({rate:.1f}개/초)")
    else:
        logging.info(f"⚡ {func_name}: {duration:.2f}초 소요")


# 상수 정의
TRADING_START_HOUR = 8  # 거래일 기준 시작 시간
DEFAULT_TIMEOUT = 10  # 기본 HTTP 타임아웃
MAX_RETRY_COUNT = 3  # 최대 재시도 횟수

# 네이버 금융 URL 템플릿
NAVER_THEME_LIST_URL = "https://finance.naver.com/sise/theme.naver"
NAVER_THEME_DETAIL_URL = "https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no={theme_code}"
NAVER_STOCK_NEWS_URL = "https://finance.naver.com/item/news_news.naver?code={stock_code}&page=1"