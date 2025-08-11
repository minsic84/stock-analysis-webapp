from datetime import datetime
import re
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
import logging

def format_datetime(dt):
    """날짜/시간 포맷팅"""
    if dt:
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    return ''

def format_number(num):
    """숫자 포맷팅 (천단위 콤마)"""
    if num:
        return f"{num:,}"
    return '0'

def safe_int(value, default=0):
    """안전한 정수 변환"""
    try:
        return int(value) if value else default
    except (ValueError, TypeError):
        return default


def clean_text(text: str) -> str:
    """텍스트 정리 (공백, 특수문자 제거)"""
    if not text:
        return ""

    # HTML 태그 제거
    text = re.sub(r'<[^>]+>', '', text)
    # 연속된 공백을 하나로
    text = re.sub(r'\s+', ' ', text)
    # 앞뒤 공백 제거
    text = text.strip()

    return text


def parse_number(text: str) -> Optional[float]:
    """문자열에서 숫자 추출 (천단위 콤마, % 등 처리)"""
    if not text:
        return None

    # 숫자가 아닌 문자 제거 (콤마, % 제외)
    clean_num = re.sub(r'[^\d.,-]', '', str(text))
    clean_num = clean_num.replace(',', '')

    try:
        return float(clean_num)
    except ValueError:
        return None


def parse_percentage(text: str) -> Optional[float]:
    """퍼센트 문자열을 숫자로 변환"""
    if not text:
        return None

    # % 기호와 함께 숫자 추출
    match = re.search(r'([+-]?\d+\.?\d*)%?', str(text))
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


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


def get_date_range(days_back: int = 1) -> tuple:
    """날짜 범위 계산 (N일 전부터 오늘까지)"""
    today = datetime.now().date()
    start_date = today - timedelta(days=days_back)

    return start_date, today


def is_trading_day(date_obj: datetime) -> bool:
    """거래일 여부 확인 (주말 제외, 공휴일은 별도 처리 필요)"""
    # 토요일(5), 일요일(6) 제외
    return date_obj.weekday() < 5


def get_latest_trading_date() -> datetime:
    """최근 거래일 조회"""
    today = datetime.now()

    # 오늘이 거래일이면 오늘, 아니면 이전 거래일
    while not is_trading_day(today):
        today -= timedelta(days=1)

    return today.date()


def safe_request(url: str, headers: Dict = None, timeout: int = 30) -> Optional[requests.Response]:
    """안전한 HTTP 요청"""
    default_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
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


def extract_stock_code(text: str) -> Optional[str]:
    """텍스트에서 종목코드 추출 (6자리 숫자)"""
    if not text:
        return None

    # 6자리 숫자 패턴 찾기
    match = re.search(r'\b(\d{6})\b', text)
    if match:
        return match.group(1)

    return None


def calculate_high_days(prices: List[float], target_price: float) -> Optional[int]:
    """지정 기간 신고가 여부 확인 (며칠 만의 고가인지)"""
    if not prices or not target_price:
        return None

    # 최근 가격이 타겟 가격보다 높은 경우의 일수 계산
    for i, price in enumerate(prices):
        if price >= target_price:
            return i + 1

    return len(prices) + 1  # 전체 기간 중 최고가


def get_price_concentration_zones(prices: List[float], volumes: List[float] = None) -> List[Dict]:
    """가격 집중 구간 분석"""
    if not prices:
        return []

    # 가격대별 빈도 계산
    price_counts = {}

    for i, price in enumerate(prices):
        # 100원 단위로 구간화
        price_zone = round(price / 100) * 100

        if price_zone not in price_counts:
            price_counts[price_zone] = {
                'count': 0,
                'volume': 0,
                'price': price_zone
            }

        price_counts[price_zone]['count'] += 1
        if volumes and i < len(volumes):
            price_counts[price_zone]['volume'] += volumes[i]

    # 빈도순 정렬
    concentration_zones = sorted(
        price_counts.values(),
        key=lambda x: x['count'],
        reverse=True
    )

    return concentration_zones[:5]  # 상위 5개 구간


def validate_stock_code(stock_code: str) -> bool:
    """종목코드 유효성 검증"""
    if not stock_code:
        return False

    # 6자리 숫자인지 확인
    return bool(re.match(r'^\d{6}$', stock_code))


def get_news_time_display(news_time: datetime) -> str:
    """뉴스 시간을 상대적 시간으로 표시"""
    if not news_time:
        return ""

    now = datetime.now()
    diff = now - news_time

    if diff.days > 0:
        return f"{diff.days}일 전"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours}시간 전"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes}분 전"
    else:
        return "방금 전"