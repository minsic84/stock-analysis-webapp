#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
등락율상위분석 모듈 (완전 독립형)
- 네이버 금융 테마별 상위 종목 크롤링
- 실시간 진행상황 추적
- 자동 스케줄링 (오전 8시 기준 날짜 처리)
- 완전 독립적인 DB 및 API 구조
"""

__version__ = '3.0.0'
__author__ = 'Stock Analysis Team'

from .routes import top_rate_bp
from .database import TopRateDatabase
from .crawler import TopRateCrawler
from .utils import get_trading_date, clean_text, parse_percentage
from .scheduler import TopRateScheduler

__all__ = [
    'top_rate_bp',
    'TopRateDatabase',
    'TopRateCrawler',
    'TopRateScheduler',
    'get_trading_date',
    'clean_text',
    'parse_percentage'
]


def register_module(app):
    """Flask 앱에 등락율상위분석 모듈 등록"""
    try:
        # Blueprint 등록
        app.register_blueprint(top_rate_bp, url_prefix='/top-rate')

        # 스케줄러 초기화 (선택사항)
        scheduler = TopRateScheduler()
        scheduler.init_app(app)

        app.logger.info("✅ 등락율상위분석 모듈 등록 완료 (독립형 v3.0)")
        return True

    except Exception as e:
        app.logger.error(f"❌ 등락율상위분석 모듈 등록 실패: {e}")
        return False