#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
import logging


def clean_text(text: str) -> str:
    """텍스트 정리 (공백, 특수문자 제거)"""
    if not text:
        return ""

    # HTML 태그 제거
    text = re.sub(r'<[^>]+>', '', text)
    # 연속된 공백을 하나로
    text = re.sub(r'\s+', ' ', text)
    # 앞뒤 공백 제거
    text = text.strip().replace('\n', '').replace('\t', '').replace('\xa0', '').replace(',', '')

    return text


def parse_number(text: str) -> Optional[int]:
    """문자열에서 숫자 추출 (천단위 콤마 등 처리)"""
    if not text:
        return 0

    try:
        # 숫자가 아닌 문자 제거 (콤마, % 제외)
        clean_num = re.sub(r'[^\d.-]', '', str(text))
        return int(float(clean_num)) if clean_num else 0
    except (ValueError, TypeError):
        return 0


def parse_percentage(text: str) -> Optional[float]:
    """퍼센트 문자열을 숫자로 변환"""
    if not text:
        return 0

    try:
        # % 기호와 함께 숫자 추출
        match = re.search(r'([+-]?\d+\.?\d*)%?', str(text))
        if match:
            return float(match.group(1))
        return 0
    except (ValueError, TypeError):
        return 0


def safe_request(url: str, headers: Dict = None, timeout: int = 15) -> Optional[requests.Response]:
    """안전한 HTTP 요청"""
    default_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }

    if headers:
        default_headers.update(headers)

    try:
        response = requests.get(
            url,
            headers=default_headers,
            timeout=timeout,
            allow_redirects=True
        )
        response.raise_for_status()
        return response

    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP 요청 실패 ({url}): {e}")
        return None


def parse_news_date(date_text: str) -> Optional[datetime]:
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
        elif '그제' in date_text:
            return today - timedelta(days=2)

        return today

    except Exception as e:
        logging.error(f"날짜 파싱 오류: {date_text}, {e}")
        return datetime.now()


def parse_news_time(time_text: str, base_date: datetime) -> Optional[datetime]:
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


def format_currency(amount: Union[int, float]) -> str:
    """통화 포맷팅 (천단위 콤마)"""
    if amount is None:
        return "0"

    try:
        return f"{int(amount):,}"
    except (ValueError, TypeError):
        return str(amount)


def format_percentage(value: Union[int, float], digits: int = 2) -> str:
    """퍼센트 포맷팅"""
    if value is None:
        return "0.00%"

    try:
        return f"{float(value):.{digits}f}%"
    except (ValueError, TypeError):
        return f"{value}%"


def is_today_news(news_time: Optional[datetime]) -> bool:
    """당일 뉴스 여부 확인"""
    if not news_time:
        return False

    today = datetime.now().date()
    return news_time.date() == today


def extract_stock_code(url: str) -> str:
    """URL에서 종목 코드 추출"""
    if not url:
        return ""

    match = re.search(r'code=(\d{6})', url)
    return match.group(1) if match else ""


def extract_theme_code(url: str) -> str:
    """URL에서 테마 코드 추출"""
    if not url:
        return ""

    match = re.search(r'no=(\d+)', url)
    return match.group(1) if match else ""


def group_themes_by_name(theme_data: List[Dict]) -> Dict:
    """테마 데이터를 테마명별로 그룹화"""
    themes_grouped = {}

    for stock in theme_data:
        try:
            # JSON 문자열을 파싱
            import json
            themes = json.loads(stock['themes']) if isinstance(stock['themes'], str) else stock['themes']

            for theme_name in themes:
                if theme_name not in themes_grouped:
                    themes_grouped[theme_name] = {
                        'theme_name': theme_name,
                        'stocks': [],
                        'total_stocks': 0,
                        'avg_change_rate': 0
                    }

                # 뉴스 파싱
                news_list = json.loads(stock['news']) if isinstance(stock['news'], str) else stock['news']

                stock_info = {
                    'stock_code': stock['stock_code'],
                    'stock_name': stock['stock_name'],
                    'price': stock['price'],
                    'change_rate': stock['change_rate'],
                    'volume': stock['volume'],
                    'news': news_list
                }

                themes_grouped[theme_name]['stocks'].append(stock_info)

        except Exception as e:
            logging.error(f"테마 그룹화 오류: {e}")
            continue

    # 통계 계산
    for theme_name, theme_info in themes_grouped.items():
        theme_info['total_stocks'] = len(theme_info['stocks'])
        if theme_info['stocks']:
            theme_info['avg_change_rate'] = sum(s['change_rate'] for s in theme_info['stocks']) / len(
                theme_info['stocks'])

    # 평균 등락률 순으로 정렬
    return dict(sorted(themes_grouped.items(), key=lambda x: x[1]['avg_change_rate'], reverse=True))


def calculate_theme_stats(theme_data: List[Dict]) -> Dict:
    """테마 데이터 통계 계산"""
    if not theme_data:
        return {
            'theme_count': 0,
            'stock_count': 0,
            'news_count': 0
        }

    import json

    # 테마 개수 계산
    all_themes = set()
    total_news = 0

    for stock in theme_data:
        try:
            themes = json.loads(stock['themes']) if isinstance(stock['themes'], str) else stock['themes']
            all_themes.update(themes)

            news_list = json.loads(stock['news']) if isinstance(stock['news'], str) else stock['news']
            total_news += len(news_list)

        except Exception as e:
            logging.error(f"통계 계산 오류: {e}")
            continue

    return {
        'theme_count': len(all_themes),
        'stock_count': len(theme_data),
        'news_count': total_news
    }