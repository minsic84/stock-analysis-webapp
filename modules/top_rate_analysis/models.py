#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum


class SupplyStage(Enum):
    """수급 단계"""
    FOUNDATION = 1  # 기반 단계 (사모펀드, 금융투자)
    TRUST = 2  # 투신 단계 (투신사)
    INDIVIDUAL = 3  # 개인 단계 (개인투자자)


class ScoreGrade(Enum):
    """종합 점수 등급"""
    A_PLUS = "A+"
    A = "A"
    B_PLUS = "B+"
    B = "B"
    C = "C"
    D = "D"


@dataclass
class SectorData:
    """업종 데이터"""
    sector_name: str
    sector_code: str = ""
    change_rate: float = 0.0
    change_amount: int = 0
    current_value: float = 0.0
    volume: int = 0
    top_stocks: List['StockData'] = field(default_factory=list)
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def is_positive(self) -> bool:
        return self.change_rate > 0

    @property
    def formatted_change_rate(self) -> str:
        sign = "+" if self.change_rate > 0 else ""
        return f"{sign}{self.change_rate:.2f}%"


@dataclass
class StockData:
    """종목 데이터"""
    stock_code: str
    stock_name: str
    sector: str = ""
    current_price: int = 0
    change_rate: float = 0.0
    change_amount: int = 0
    volume: int = 0
    trading_value: int = 0

    # 신고가 정보
    is_new_high_20d: bool = False
    is_new_high_60d: bool = False
    is_new_high_120d: bool = False
    is_new_high_200d: bool = False

    # 수급 정보
    foreign_buy: int = 0
    institution_buy: int = 0
    individual_buy: int = 0
    supply_stage: SupplyStage = SupplyStage.FOUNDATION

    # 분석 결과
    total_score: int = 0
    score_grade: ScoreGrade = ScoreGrade.C

    # 뉴스 데이터
    news_list: List['NewsData'] = field(default_factory=list)

    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def is_positive(self) -> bool:
        return self.change_rate > 0

    @property
    def formatted_price(self) -> str:
        return f"{self.current_price:,}원"

    @property
    def formatted_change_rate(self) -> str:
        sign = "+" if self.change_rate > 0 else ""
        return f"{sign}{self.change_rate:.2f}%"

    @property
    def new_high_days(self) -> List[int]:
        """신고가 달성 일수 리스트"""
        days = []
        if self.is_new_high_20d:
            days.append(20)
        if self.is_new_high_60d:
            days.append(60)
        if self.is_new_high_120d:
            days.append(120)
        if self.is_new_high_200d:
            days.append(200)
        return days

    @property
    def supply_badges(self) -> List[Dict[str, str]]:
        """수급 배지 정보"""
        badges = []

        if self.foreign_buy > 0:
            badges.append({"text": "외인매수", "class": "foreign-buy"})
        if self.institution_buy > 0:
            badges.append({"text": "기관매수", "class": "institution-buy"})
        if self.individual_buy < 0:
            badges.append({"text": "개인매도", "class": "individual-sell"})

        return badges


@dataclass
class NewsData:
    """뉴스 데이터"""
    title: str
    url: str
    source: str = ""
    published_at: datetime = field(default_factory=datetime.now)
    content: str = ""
    sentiment: str = "neutral"  # positive, negative, neutral
    keywords: List[str] = field(default_factory=list)
    is_today: bool = True

    @property
    def time_display(self) -> str:
        """상대 시간 표시"""
        now = datetime.now()
        diff = now - self.published_at

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


@dataclass
class SupplyDemandData:
    """수급 데이터"""
    date: datetime
    foreign_net: int = 0  # 외국인 순매매
    institution_net: int = 0  # 기관 순매매
    individual_net: int = 0  # 개인 순매매
    private_fund_net: int = 0  # 사모펀드 순매매
    credit_balance: int = 0  # 신용잔고

    @property
    def is_foreign_buying(self) -> bool:
        return self.foreign_net > 0

    @property
    def is_institution_buying(self) -> bool:
        return self.institution_net > 0

    @property
    def is_individual_selling(self) -> bool:
        return self.individual_net < 0


@dataclass
class ChartAnalysisData:
    """차트 분석 데이터"""
    stock_code: str
    stock_name: str
    timeframe: str  # daily, weekly, monthly

    # 가격 집중 구간
    concentration_zones: List[Dict] = field(default_factory=list)

    # 수급 차트 데이터
    supply_chart_data: List[SupplyDemandData] = field(default_factory=list)

    # 기술적 지표
    support_levels: List[float] = field(default_factory=list)
    resistance_levels: List[float] = field(default_factory=list)

    analyzed_at: datetime = field(default_factory=datetime.now)


@dataclass
class AIAnalysisResult:
    """AI 분석 결과"""
    summary: str
    key_points: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    supply_analysis: str = ""
    risk_factors: List[str] = field(default_factory=list)
    investment_recommendation: str = ""
    confidence_score: float = 0.0

    analyzed_at: datetime = field(default_factory=datetime.now)


@dataclass
class TopRateAnalysis:
    """등락율상위분석 메인 데이터"""
    analysis_id: str

    # 크롤링 데이터
    top_sectors: List[SectorData] = field(default_factory=list)
    all_stocks: List[StockData] = field(default_factory=list)

    # 분석 결과
    ai_analysis: Optional[AIAnalysisResult] = None
    chart_analyses: List[ChartAnalysisData] = field(default_factory=list)

    # 상태 정보
    crawl_status: str = "pending"  # pending, crawling, completed, error
    analysis_status: str = "pending"

    # 통계
    total_sectors: int = 0
    total_news_stocks: int = 0
    total_analyzed_stocks: int = 0
    new_high_stocks_count: int = 0

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def update_statistics(self):
        """통계 정보 업데이트"""
        self.total_sectors = len(self.top_sectors)
        self.total_news_stocks = sum(len(sector.top_stocks) for sector in self.top_sectors)
        self.total_analyzed_stocks = len(self.all_stocks)
        self.new_high_stocks_count = len([
            stock for stock in self.all_stocks
            if any([stock.is_new_high_20d, stock.is_new_high_60d,
                    stock.is_new_high_120d, stock.is_new_high_200d])
        ])
        self.updated_at = datetime.now()