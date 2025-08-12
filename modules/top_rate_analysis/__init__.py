#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
등락율상위분석 모듈 (완전 독립형)

주요 기능:
- 네이버 금융에서 테마별 상위 종목 크롤링 (theme_crawler_test.py 기반)
- 종목별 당일 뉴스 수집 및 분석
- OpenAI GPT를 이용한 AI 뉴스 분석 (개별이슈 vs 테마이슈 구분)
- 일봉/수급 데이터와 결합한 종합분석
- 완전 독립적인 DB 및 유틸 클래스 포함
"""

__version__ = '2.0.0'
__author__ = 'Stock Analysis Team'

# 독립적인 모듈 컴포넌트들
from .routes import top_rate_bp
from .database import TopRateDatabase
from .crawler import ThemeCrawler
from .ai_analyzer import AIAnalyzer
from .utils import (
    clean_text,
    parse_number,
    parse_percentage,
    safe_request,
    group_themes_by_name,
    calculate_theme_stats
)

__all__ = [
    'top_rate_bp',
    'TopRateDatabase',
    'ThemeCrawler',
    'AIAnalyzer',
    'clean_text',
    'parse_number',
    'parse_percentage',
    'safe_request',
    'group_themes_by_name',
    'calculate_theme_stats'
]


def register_module(app):
    """Flask 앱에 모듈 등록"""
    app.register_blueprint(top_rate_bp, url_prefix='/top-rate')
    app.logger.info("✅ 등락율상위분석 모듈 등록 완료 (독립형 v2.0)")