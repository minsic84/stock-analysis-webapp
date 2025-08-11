#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from .models import StockData, ChartAnalysisData, SupplyDemandData
from common.database import execute_query, get_stock_table_name, check_table_exists
from common.utils import calculate_high_days, get_price_concentration_zones


class ChartAnalyzer:
    """차트 기술적 분석 클래스"""

    def __init__(self):
        self.daily_schema = "daily"  # realtime_daily_db
        self.program_schema = "program"  # realtime_program_db

    def analyze_new_high_stocks(self, stocks: List[StockData]) -> List[StockData]:
        """신고가 종목 필터링 및 분석"""
        new_high_stocks = []

        for stock in stocks:
            try:
                # 신고가 여부 확인
                if self._check_new_highs(stock):
                    new_high_stocks.append(stock)
                    logging.info(f"신고가 종목 발견: {stock.stock_name} ({stock.stock_code})")

            except Exception as e:
                logging.error(f"신고가 분석 실패 ({stock.stock_name}): {e}")
                continue

        logging.info(f"신고가 종목 총 {len(new_high_stocks)}개 발견")
        return new_high_stocks

    def create_chart_analysis(self, stock: StockData) -> Optional[ChartAnalysisData]:
        """개별 종목 차트 분석"""
        try:
            # 일봉, 주봉, 월봉 데이터 조회
            daily_data = self._get_daily_data(stock.stock_code, 365)  # 1년
            weekly_data = self._get_weekly_data(stock.stock_code, 156)  # 3년 (주단위)
            monthly_data = self._get_monthly_data(stock.stock_code)  # 전체 (월단위)

            if not daily_data:
                return None

            chart_analysis = ChartAnalysisData(
                stock_code=stock.stock_code,
                stock_name=stock.stock_name,
                timeframe="combined"
            )

            # 1. 가격 집중 구간 분석
            chart_analysis.concentration_zones = self._analyze_concentration_zones(
                daily_data, weekly_data, monthly_data
            )

            # 2. 수급 차트 데이터
            chart_analysis.supply_chart_data = self._get_supply_data(stock.stock_code, 60)  # 2개월

            # 3. 지지/저항선 계산
            chart_analysis.support_levels, chart_analysis.resistance_levels = \
                self._calculate_support_resistance(daily_data)

            return chart_analysis

        except Exception as e:
            logging.error(f"차트 분석 실패 ({stock.stock_name}): {e}")
            return None

    def _check_new_highs(self, stock: StockData) -> bool:
        """신고가 여부 확인"""
        try:
            # 일봉 데이터 조회
            daily_data = self._get_daily_data(stock.stock_code, 250)  # 약 1년

            if not daily_data or len(daily_data) < 20:
                return False

            # 최근 가격
            current_price = daily_data[0]['high_price']  # 최신 데이터가 첫 번째

            # 각 기간별 신고가 확인
            periods = [20, 60, 120, 200]
            new_highs = []

            for period in periods:
                if len(daily_data) >= period:
                    period_data = daily_data[:period]
                    max_price = max(row['high_price'] for row in period_data)

                    is_new_high = current_price >= max_price
                    new_highs.append(is_new_high)

                    # 종목 데이터에 신고가 정보 업데이트
                    if period == 20:
                        stock.is_new_high_20d = is_new_high
                    elif period == 60:
                        stock.is_new_high_60d = is_new_high
                    elif period == 120:
                        stock.is_new_high_120d = is_new_high
                    elif period == 200:
                        stock.is_new_high_200d = is_new_high
                else:
                    new_highs.append(False)

            # 하나라도 신고가면 True
            return any(new_highs)

        except Exception as e:
            logging.error(f"신고가 확인 실패 ({stock.stock_code}): {e}")
            return False

    def _get_daily_data(self, stock_code: str, days: int) -> List[Dict]:
        """일봉 데이터 조회"""
        try:
            table_name = get_stock_table_name(stock_code, 'daily')

            if not check_table_exists(table_name, self.daily_schema):
                return []

            query = f"""
            SELECT date, open_price, high_price, low_price, close_price, 
                   volume, trading_value, prev_day_diff, change_rate
            FROM {table_name}
            ORDER BY date DESC
            LIMIT %s
            """

            result = execute_query(query, self.daily_schema, (days,))
            return result if result else []

        except Exception as e:
            logging.error(f"일봉 데이터 조회 실패 ({stock_code}): {e}")
            return []

    def _get_weekly_data(self, stock_code: str, weeks: int) -> List[Dict]:
        """주봉 데이터 생성 (일봉에서 변환)"""
        try:
            # 더 많은 일봉 데이터 조회 (주말 제외 고려)
            daily_data = self._get_daily_data(stock_code, weeks * 7)

            if not daily_data:
                return []

            # 일봉을 주봉으로 변환
            weekly_data = []
            current_week = []
            current_week_start = None

            for row in reversed(daily_data):  # 오래된 것부터 처리
                # 딕셔너리에서 date 접근
                date = row['date'] if isinstance(row['date'], datetime) else datetime.strptime(str(row['date']),
                                                                                               '%Y-%m-%d')
                week_start = date - timedelta(days=date.weekday())  # 월요일

                if current_week_start != week_start:
                    # 새로운 주 시작
                    if current_week:
                        weekly_data.append(self._create_weekly_row(current_week))

                    current_week = [row]
                    current_week_start = week_start
                else:
                    current_week.append(row)

            # 마지막 주 처리
            if current_week:
                weekly_data.append(self._create_weekly_row(current_week))

            return list(reversed(weekly_data))  # 최신순으로 정렬

        except Exception as e:
            logging.error(f"주봉 데이터 생성 실패 ({stock_code}): {e}")
            return []

    def _get_monthly_data(self, stock_code: str) -> List[Dict]:
        """월봉 데이터 생성"""
        try:
            # 전체 일봉 데이터 조회
            daily_data = self._get_daily_data(stock_code, 3000)  # 충분한 데이터

            if not daily_data:
                return []

            # 일봉을 월봉으로 변환
            monthly_data = []
            current_month = []
            current_month_key = None

            for row in reversed(daily_data):
                # 딕셔너리에서 date 접근
                date = row['date'] if isinstance(row['date'], datetime) else datetime.strptime(str(row['date']),
                                                                                               '%Y-%m-%d')
                month_key = (date.year, date.month)

                if current_month_key != month_key:
                    if current_month:
                        monthly_data.append(self._create_monthly_row(current_month))

                    current_month = [row]
                    current_month_key = month_key
                else:
                    current_month.append(row)

            if current_month:
                monthly_data.append(self._create_monthly_row(current_month))

            return list(reversed(monthly_data))

        except Exception as e:
            logging.error(f"월봉 데이터 생성 실패 ({stock_code}): {e}")
            return []

    def _create_weekly_row(self, week_data: List[Dict]) -> Dict:
        """주봉 데이터 생성"""
        return {
            'date': week_data[-1]['date'],  # 주의 마지막 날
            'open_price': week_data[0]['open_price'],
            'high_price': max(row['high_price'] for row in week_data),
            'low_price': min(row['low_price'] for row in week_data),
            'close_price': week_data[-1]['close_price'],
            'volume': sum(row['volume'] for row in week_data),
            'trading_value': sum(row.get('trading_value', 0) for row in week_data)
        }

    def _create_monthly_row(self, month_data: List[Dict]) -> Dict:
        """월봉 데이터 생성"""
        return {
            'date': month_data[-1]['date'],
            'open_price': month_data[0]['open_price'],
            'high_price': max(row['high_price'] for row in month_data),
            'low_price': min(row['low_price'] for row in month_data),
            'close_price': month_data[-1]['close_price'],
            'volume': sum(row['volume'] for row in month_data),
            'trading_value': sum(row.get('trading_value', 0) for row in month_data)
        }

    def _analyze_concentration_zones(self, daily_data: List[Dict], weekly_data: List[Dict], monthly_data: List[Dict]) -> \
    List[Dict]:
        """가격 집중 구간 분석"""
        try:
            concentration_zones = []

            # 1. 일봉 집중구간 (1년)
            if daily_data:
                daily_prices = [row['close_price'] for row in daily_data]
                daily_volumes = [row['volume'] for row in daily_data]
                daily_zones = get_price_concentration_zones(daily_prices, daily_volumes)

                concentration_zones.append({
                    'timeframe': 'daily',
                    'period': '1년 일봉',
                    'zones': daily_zones[:3]  # 상위 3개
                })

            # 2. 주봉 집중구간 (3년)
            if weekly_data:
                weekly_prices = [row['close_price'] for row in weekly_data]
                weekly_volumes = [row['volume'] for row in weekly_data]
                weekly_zones = get_price_concentration_zones(weekly_prices, weekly_volumes)

                concentration_zones.append({
                    'timeframe': 'weekly',
                    'period': '3년 주봉',
                    'zones': weekly_zones[:3]
                })

            # 3. 월봉 집중구간 (전체)
            if monthly_data:
                monthly_prices = [row['close_price'] for row in monthly_data]
                monthly_volumes = [row['volume'] for row in monthly_data]
                monthly_zones = get_price_concentration_zones(monthly_prices, monthly_volumes)

                concentration_zones.append({
                    'timeframe': 'monthly',
                    'period': '전체 월봉',
                    'zones': monthly_zones[:3]
                })

            return concentration_zones

        except Exception as e:
            logging.error(f"가격 집중구간 분석 실패: {e}")
            return []

    def _get_supply_data(self, stock_code: str, days: int) -> List[SupplyDemandData]:
        """수급 데이터 조회"""
        try:
            table_name = get_stock_table_name(stock_code, 'supply')

            if not check_table_exists(table_name, self.program_schema):
                return []

            query = f"""
            SELECT date, current_price, prev_day_diff, trading_value,
                   individual_inv, foreign_invest, institution_total, financial_invest
            FROM {table_name}
            ORDER BY date DESC
            LIMIT %s
            """

            result = execute_query(query, self.program_schema, (days,))

            supply_data = []
            for row in result:
                supply_data.append(SupplyDemandData(
                    date=row['date'],
                    foreign_net=row['foreign_invest'] or 0,
                    institution_net=row['institution_total'] or 0,
                    individual_net=row['individual_inv'] or 0,
                    private_fund_net=row['financial_invest'] or 0
                ))

            return supply_data

        except Exception as e:
            logging.error(f"수급 데이터 조회 실패 ({stock_code}): {e}")
            return []

    def _calculate_support_resistance(self, daily_data: List[Dict]) -> Tuple[List[float], List[float]]:
        """지지선/저항선 계산"""
        try:
            if not daily_data or len(daily_data) < 20:
                return [], []

            prices = [row['close_price'] for row in daily_data]
            highs = [row['high_price'] for row in daily_data]
            lows = [row['low_price'] for row in daily_data]

            # 단순한 지지/저항선 계산 (피벗 포인트 기반)
            support_levels = []
            resistance_levels = []

            # 최근 20일 평균
            recent_avg = sum(prices[:20]) / 20

            # 52주 고가/저가
            year_high = max(highs)
            year_low = min(lows)

            # 지지선 후보들
            support_candidates = [
                year_low,
                recent_avg * 0.9,
                recent_avg * 0.95
            ]

            # 저항선 후보들
            resistance_candidates = [
                year_high,
                recent_avg * 1.05,
                recent_avg * 1.1
            ]

            # 현재가 기준으로 유효한 지지/저항선만 선택
            current_price = prices[0]

            support_levels = [level for level in support_candidates if level < current_price]
            resistance_levels = [level for level in resistance_candidates if level > current_price]

            return sorted(support_levels, reverse=True)[:3], sorted(resistance_levels)[:3]

        except Exception as e:
            logging.error(f"지지/저항선 계산 실패: {e}")
            return [], []

    def create_chart_data_for_frontend(self, chart_analysis: ChartAnalysisData) -> Dict:
        """프론트엔드용 차트 데이터 생성"""
        try:
            chart_data = {
                'stock_code': chart_analysis.stock_code,
                'stock_name': chart_analysis.stock_name,
                'price_chart': self._create_price_chart_data(chart_analysis),
                'supply_chart': self._create_supply_chart_data(chart_analysis),
                'concentration_zones': chart_analysis.concentration_zones
            }

            return chart_data

        except Exception as e:
            logging.error(f"차트 데이터 생성 실패: {e}")
            return {}

    def _create_price_chart_data(self, chart_analysis: ChartAnalysisData) -> Dict:
        """가격 차트 데이터 생성"""
        try:
            # 최근 일봉 데이터 조회 (차트용)
            daily_data = self._get_daily_data(chart_analysis.stock_code, 30)  # 최근 30일

            if not daily_data:
                return {
                    'labels': [],
                    'datasets': []
                }

            # 날짜순으로 정렬 (오래된 것부터)
            daily_data = sorted(daily_data, key=lambda x: x['date'])

            # Chart.js 용 데이터 구조로 변환
            price_data = {
                'labels': [data['date'].strftime('%m/%d') for data in daily_data],
                'datasets': [
                    {
                        'label': '종가',
                        'data': [data['close_price'] for data in daily_data],
                        'borderColor': '#3498db',
                        'backgroundColor': 'rgba(52, 152, 219, 0.1)',
                        'tension': 0.4,
                        'fill': False
                    },
                    {
                        'label': '고가',
                        'data': [data['high_price'] for data in daily_data],
                        'borderColor': '#e74c3c',
                        'backgroundColor': 'rgba(231, 76, 60, 0.1)',
                        'tension': 0.4,
                        'fill': False,
                        'borderDash': [2, 2]
                    }
                ]
            }

            # 집중구간 추가
            for zone_group in chart_analysis.concentration_zones:
                for i, zone in enumerate(zone_group['zones'][:2]):  # 상위 2개 집중구간
                    price_data['datasets'].append({
                        'label': f'{zone_group["period"]} 집중구간 {i + 1}',
                        'data': [zone['price']] * len(daily_data),  # 가로선
                        'borderColor': '#f39c12' if i == 0 else '#9b59b6',
                        'borderDash': [5, 5],
                        'fill': False,
                        'pointRadius': 0,
                        'borderWidth': 2
                    })

            return price_data

        except Exception as e:
            logging.error(f"가격 차트 데이터 생성 실패: {e}")
            return {
                'labels': [],
                'datasets': []
            }

    def _create_supply_chart_data(self, chart_analysis: ChartAnalysisData) -> Dict:
        """수급 차트 데이터 생성"""
        if not chart_analysis.supply_chart_data:
            return {}

        # 최근 30일 데이터
        recent_supply = chart_analysis.supply_chart_data[:30]

        supply_data = {
            'labels': [data.date.strftime('%m/%d') for data in reversed(recent_supply)],
            'datasets': [
                {
                    'label': '외국인',
                    'data': [data.foreign_net for data in reversed(recent_supply)],
                    'backgroundColor': '#27ae60',
                    'borderColor': '#27ae60'
                },
                {
                    'label': '기관',
                    'data': [data.institution_net for data in reversed(recent_supply)],
                    'backgroundColor': '#3498db',
                    'borderColor': '#3498db'
                },
                {
                    'label': '개인',
                    'data': [data.individual_net for data in reversed(recent_supply)],
                    'backgroundColor': '#e74c3c',
                    'borderColor': '#e74c3c'
                }
            ]
        }

        return supply_data