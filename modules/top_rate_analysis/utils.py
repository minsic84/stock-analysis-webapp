#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
등락율상위분석 유틸리티 함수들 (수정완료)
- 거래일 기준 날짜 처리 (오전 8시 기준)
- 텍스트 정리 및 파싱 함수
- 크롤링 관련 헬퍼 함수
"""

import re
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import logging


def get_trading_date(target_time: Optional[datetime] = None) -> str:
    """
    거래일 기준 날짜 반환

    Args:
        target_time: 기준 시간 (None이면 현재 시간)

    Returns:
        YYYY-MM-DD 형식의 거래일 날짜
    """
    if target_time is None:
        target_time = datetime.now()

    if target_time.hour < 8:  # 오전 8시 이전
        trading_date = target_time - timedelta(days=1)
    else:
        trading_date = target_time

    return trading_date.strftime('%Y-%m-%d')


def format_date_for_display(date_str: str) -> str:
    """날짜를 표시용으로 포맷"""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%Y년 %m월 %d일')
    except:
        return date_str


def get_table_name(date_str: str) -> str:
    """날짜 문자열을 DB 테이블명으로 변환"""
    clean_date = date_str.replace('-', '')
    return f"theme_{clean_date}"


def clean_text(text: str) -> str:
    """텍스트 정리"""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def parse_percentage(text: str) -> float:
    """텍스트에서 퍼센트 값 추출"""
    if not text:
        return 0.0
    clean_text_str = str(text).replace('%', '').replace(',', '').strip()
    try:
        return float(clean_text_str)
    except ValueError:
        return 0.0


def calculate_theme_stats(theme_data: Dict) -> Dict:
    """
    🔥 테마 통계 계산 (올바른 구현)

    Args:
        theme_data: 데이터베이스에서 가져온 테마 데이터

    Returns:
        계산된 통계 정보
    """
    try:
        # 기본 정보 추출
        stats = {
            'theme_name': theme_data.get('theme_name', ''),
            'stock_count': theme_data.get('stock_count', 0),
            'avg_change_rate': theme_data.get('avg_change_rate', 0.0),
            'avg_volume_ratio': theme_data.get('avg_volume_ratio', 0.0),
            'total_volume': theme_data.get('total_volume', 0),
            'positive_stocks': theme_data.get('positive_stocks', 0),
            'icon': '📈'  # 기본 아이콘
        }

        # 아이콘 매핑
        icon_mapping = {
            '증권': '🏦', 'AI반도체': '🤖', '2차전지': '🔋',
            'AI': '🤖', '반도체': '💾', '바이오': '🧬',
            '게임': '🎮', '자동차': '🚗', '화학': '⚗️',
            '조선': '🚢', '항공': '✈️', '건설': '🏗️',
            '통신': '📡', '은행': '🏛️', '헬스케어': '🏥',
            '엔터테인먼트': '🎭', '코로나19': '🦠',
            'K-pop': '🎵', '메타버스': '🌐', '전기차': '⚡',
            '친환경': '🌱', '우주항공': '🚀', '로봇': '🤖',
            'VR/AR': '🥽', 'VR': '🥽', 'AR': '🥽',
            '블록체인': '⛓️', '가상화폐': '₿'
        }

        # 테마명에서 아이콘 찾기
        theme_name = stats['theme_name']
        for keyword, icon in icon_mapping.items():
            if keyword in theme_name:
                stats['icon'] = icon
                break

        # 상승 비율 계산
        if stats['stock_count'] > 0:
            stats['positive_ratio'] = (stats['positive_stocks'] / stats['stock_count']) * 100
        else:
            stats['positive_ratio'] = 0.0

        return stats

    except Exception as e:
        logging.error(f"테마 통계 계산 실패: {e}")
        return {
            'theme_name': theme_data.get('theme_name', '알 수 없음'),
            'stock_count': 0,
            'avg_change_rate': 0.0,
            'avg_volume_ratio': 0.0,
            'total_volume': 0,
            'positive_stocks': 0,
            'positive_ratio': 0.0,
            'icon': '📊'
        }


def validate_stock_code(stock_code: str) -> bool:
    """종목코드 유효성 검증"""
    if not stock_code:
        return False
    return bool(re.match(r'^\d{6}$', stock_code.strip()))


def get_default_headers() -> Dict[str, str]:
    """기본 HTTP 헤더 반환"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }


# 상수 정의
TRADING_START_HOUR = 8
DEFAULT_TIMEOUT = 10
MAX_RETRY_COUNT = 3