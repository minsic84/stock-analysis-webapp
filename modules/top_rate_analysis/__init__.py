#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
등락율상위분석 모듈

주요 기능:
- 네이버 금융에서 업종별 상위 종목 크롤링
- 상위 종목 뉴스 수집 및 분석
- OpenAI GPT를 이용한 AI 투자 분석
- 신고가 종목 기술적 분석
- 수급 데이터 분석
"""

__version__ = '1.0.0'
__author__ = 'Stock Analysis Team'

from .routes import top_rate_bp
from .models import TopRateAnalysis, SectorData, NewsData
from .crawler import NaverFinanceCrawler
from .news_crawler import NewsCrawler
from .ai_analyzer import AIAnalyzer
from .chart_analyzer import ChartAnalyzer

__all__ = [
    'top_rate_bp',
    'TopRateAnalysis',
    'SectorData',
    'NewsData',
    'NaverFinanceCrawler',
    'NewsCrawler',
    'AIAnalyzer',
    'ChartAnalyzer'
]