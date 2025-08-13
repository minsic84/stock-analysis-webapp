#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
삼성전자 종목 상세 차트 분석 테스트 코드 (완전 재작성)
- 실제 DB 데이터 활용
- 월봉/주봉/일봉 핵심 가격대 분석 (종가 기반 캔들 중첩)
- 세분화된 수급 세력 분석 (백만원 단위)
"""

import sys
import os
import pymysql
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict
import numpy as np
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 프로젝트 루트 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


class SamsungStockAnalyzer:
    """삼성전자 종목 상세 분석기"""

    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'charset': 'utf8mb4',
            'autocommit': True
        }
        self.stock_code = '005930'  # 삼성전자
        self.stock_name = '삼성전자'

    def get_connection(self, database: str = None) -> pymysql.Connection:
        """데이터베이스 연결"""
        config = self.db_config.copy()
        if database:
            config['database'] = database
        return pymysql.connect(**config)

    def analyze_samsung_stock(self) -> Dict:
        """삼성전자 종목 종합 분석"""

        print("🏢 삼성전자 (005930) 종목 상세 분석 시작")
        print("=" * 80)

        try:
            # 1. 일봉 데이터 로드
            daily_data = self.load_daily_price_data()
            if not daily_data:
                print("❌ 일봉 데이터를 찾을 수 없습니다")
                return {}

            print(f"✅ 일봉 데이터 로드: {len(daily_data)}일")

            # 2. 수급 데이터 로드
            supply_data = self.load_supply_demand_data()
            if not supply_data:
                print("❌ 수급 데이터를 찾을 수 없습니다")
                return {}

            # 3. 월봉/주봉/일봉 핵심 가격대 분석
            price_analysis = self.analyze_key_price_levels(daily_data)

            # 4. 세분화된 수급 분석
            supply_analysis = self.analyze_detailed_supply_demand(supply_data)

            # 5. 종합 결과
            result = {
                'stock_info': {
                    'code': self.stock_code,
                    'name': self.stock_name,
                    'current_price': daily_data[0]['close_price'] if daily_data else 0,
                    'analysis_date': datetime.now().strftime('%Y-%m-%d')
                },
                'price_analysis': price_analysis,
                'supply_analysis': supply_analysis
            }

            # 6. 결과 출력
            self.print_analysis_result(result)

            return result

        except Exception as e:
            print(f"❌ 분석 실패: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def load_daily_price_data(self) -> List[Dict]:
        """일봉 데이터 로드"""

        try:
            connection = self.get_connection('daily_prices_db')
            cursor = connection.cursor(pymysql.cursors.DictCursor)

            table_name = f"daily_prices_{self.stock_code}"

            # 테이블 존재 확인
            cursor.execute("SHOW TABLES LIKE %s", (table_name,))
            if not cursor.fetchone():
                print(f"❌ 테이블 {table_name}이 존재하지 않습니다")
                return []

            # 최신 순으로 데이터 조회 (최대 3년치)
            query = f"""
            SELECT date, open_price, high_price, low_price, close_price, volume, trading_value
            FROM {table_name}
            ORDER BY date DESC
            LIMIT 780
            """

            cursor.execute(query)
            result = cursor.fetchall()

            cursor.close()
            connection.close()

            return result if result else []

        except Exception as e:
            print(f"❌ 일봉 데이터 로드 실패: {e}")
            return []

    def load_supply_demand_data(self) -> List[Dict]:
        """수급 데이터 로드"""

        try:
            connection = self.get_connection('supply_demand_db')
            cursor = connection.cursor(pymysql.cursors.DictCursor)

            table_name = f"supply_demand_{self.stock_code}"

            # 테이블 존재 확인
            cursor.execute("SHOW TABLES LIKE %s", (table_name,))
            if not cursor.fetchone():
                print(f"❌ 테이블 {table_name}이 존재하지 않습니다")
                return []

            # 최신 순으로 최근 6개월 데이터 조회
            query = f"""
            SELECT date, current_price, individual_investor, foreign_investment,
                   institution_total, financial_investment, insurance, 
                   investment_trust, pension_fund, private_fund, other_finance,
                   bank, other_corporation, foreign_domestic, government
            FROM {table_name}
            ORDER BY date DESC
            LIMIT 120
            """

            cursor.execute(query)
            result = cursor.fetchall()

            cursor.close()
            connection.close()

            print(f"✅ 수급 데이터 로드: {len(result)}일")
            return result if result else []

        except Exception as e:
            print(f"❌ 수급 데이터 로드 실패: {e}")
            return []

    def analyze_key_price_levels(self, daily_data: List[Dict]) -> Dict:
        """월봉/주봉/일봉 핵심 가격대 분석 (종가 기반 캔들 중첩)"""

        print(f"\n📈 핵심 가격대 분석 (종가 기반 캔들 중첩)")
        print("─" * 60)

        current_price = daily_data[0]['close_price']
        print(f"💰 현재가: {current_price:,}원")

        # 기간별 데이터 분할 및 변환
        print(f"\n🔄 데이터 변환 과정:")

        # 일봉 (최근 1년 = 252일)
        daily_1year = daily_data[:252]
        print(f"   📊 일봉 데이터: {len(daily_1year)}일")

        # 주봉 변환 (최근 3년 = 780일 → 주봉)
        weekly_3year_data = daily_data[:780] if len(daily_data) >= 780 else daily_data
        weekly_3year = self.convert_to_weekly(weekly_3year_data)

        # 월봉 변환 (전체 데이터 → 월봉)
        monthly_all = self.convert_to_monthly(daily_data)

        print(f"\n🎯 변환 결과:")
        print(f"   📅 일봉: {len(daily_1year)}개")
        print(f"   📅 주봉: {len(weekly_3year)}개")
        print(f"   📅 월봉: {len(monthly_all)}개")

        # 각 기간별 핵심 가격대 찾기
        print(f"\n🔍 핵심 가격대 분석 시작:")

        daily_levels = self.find_key_price_level(daily_1year, 'daily')
        weekly_levels = self.find_key_price_level(weekly_3year, 'weekly')
        monthly_levels = self.find_key_price_level(monthly_all, 'monthly')

        return {
            'current_price': current_price,
            'daily_analysis': daily_levels,
            'weekly_analysis': weekly_levels,
            'monthly_analysis': monthly_levels,
            'conversion_summary': {
                'daily_count': len(daily_1year),
                'weekly_count': len(weekly_3year),
                'monthly_count': len(monthly_all)
            }
        }

    def convert_to_weekly(self, daily_data: List[Dict]) -> List[Dict]:
        """일봉을 주봉으로 변환"""

        if not daily_data or len(daily_data) < 5:
            print("   ⚠️ 주봉 변환: 일봉 데이터 부족 (5일 미만)")
            return []

        print(f"   🔄 주봉 변환 시작: {len(daily_data)}일 → 주봉 변환 중...")

        weekly_data = []

        # 5일씩 묶어서 주봉 생성 (최신 데이터부터)
        for i in range(0, len(daily_data), 5):
            week_group = daily_data[i:i + 5]

            if len(week_group) < 2:  # 최소 2일은 있어야 의미있는 주봉
                continue

            # 주봉 캔들 생성
            weekly_candle = self._create_period_candle(week_group, 'weekly')
            if weekly_candle:
                weekly_data.append(weekly_candle)

        print(f"   ✅ 주봉 변환 완료: {len(weekly_data)}개 주봉 생성")
        return weekly_data

    def convert_to_monthly(self, daily_data: List[Dict]) -> List[Dict]:
        """일봉을 월봉으로 변환"""

        if not daily_data or len(daily_data) < 20:
            print("   ⚠️ 월봉 변환: 일봉 데이터 부족 (20일 미만)")
            return []

        print(f"   🔄 월봉 변환 시작: {len(daily_data)}일 → 월봉 변환 중...")

        monthly_data = []
        monthly_groups = {}

        # 날짜별로 월별 그룹핑
        for day in daily_data:
            # 날짜 처리
            date_str = self._extract_date_string(day['date'])
            if not date_str:
                continue

            # YYYY-MM 형태로 월 키 생성
            month_key = date_str[:7]  # '2024-08' 형태

            if month_key not in monthly_groups:
                monthly_groups[month_key] = []
            monthly_groups[month_key].append(day)

        # 월별 데이터를 월봉으로 변환
        sorted_months = sorted(monthly_groups.keys(), reverse=True)  # 최신순

        for month_key in sorted_months:
            month_days = monthly_groups[month_key]

            if len(month_days) < 5:  # 최소 5일은 있어야 의미있는 월봉
                continue

            # 월봉 캔들 생성 (날짜순 정렬 후)
            sorted_month_days = sorted(month_days, key=lambda x: self._extract_date_string(x['date']))
            monthly_candle = self._create_period_candle(sorted_month_days, 'monthly')

            if monthly_candle:
                monthly_data.append(monthly_candle)

        print(f"   ✅ 월봉 변환 완료: {len(monthly_data)}개 월봉 생성")
        return monthly_data

    def _extract_date_string(self, date_field) -> str:
        """날짜 필드에서 문자열 추출"""

        if isinstance(date_field, str):
            return date_field[:10]  # 'YYYY-MM-DD' 부분만
        elif hasattr(date_field, 'strftime'):
            return date_field.strftime('%Y-%m-%d')
        else:
            try:
                return str(date_field)[:10]
            except:
                return ""

    def _create_period_candle(self, period_data: List[Dict], period_type: str) -> Optional[Dict]:
        """기간별 캔들 생성 (주봉/월봉 공통)"""

        if not period_data:
            return None

        try:
            # 기간별 처리 방식
            if period_type == 'weekly':
                # 주봉: 최신순 데이터이므로 첫날=금요일, 마지막날=월요일
                open_price = period_data[-1]['open_price']  # 월요일 시가
                close_price = period_data[0]['close_price']  # 금요일 종가
            else:  # monthly
                # 월봉: 정렬된 데이터이므로 첫날=월초, 마지막날=월말
                open_price = period_data[0]['open_price']  # 월초 시가
                close_price = period_data[-1]['close_price']  # 월말 종가

            # 고가/저가: 기간 중 최고/최저
            high_price = max([day['high_price'] for day in period_data])
            low_price = min([day['low_price'] for day in period_data])

            # 거래량: 기간 합계
            total_volume = sum([day['volume'] for day in period_data])

            # 대표 날짜 (최신 날짜)
            representative_date = period_data[0]['date']

            return {
                'date': representative_date,
                'open_price': open_price,
                'high_price': high_price,
                'low_price': low_price,
                'close_price': close_price,
                'volume': total_volume
            }

        except Exception as e:
            print(f"   ❌ {period_type} 캔들 생성 실패: {e}")
            return None

    def find_key_price_level(self, candle_data: List[Dict], timeframe: str) -> Dict:
        """종가 기반 캔들 중첩도 분석으로 핵심 가격대 찾기"""

        if not candle_data:
            return {'support': None, 'resistance': None}

        current_price = candle_data[0]['close_price']

        # 모든 종가 수집
        all_close_prices = [candle['close_price'] for candle in candle_data]
        unique_close_prices = list(set(all_close_prices))  # 중복 제거

        print(f"   🔍 {timeframe} 분석: {len(candle_data)}개 캔들, {len(unique_close_prices)}개 고유 종가")

        # 각 종가에서 수평선을 그어서 다른 캔들과의 중첩도 계산
        overlap_results = {}

        for close_price in unique_close_prices:
            overlap_count = 0
            overlapping_candles = []

            for i, candle in enumerate(candle_data):
                # 캔들 몸통 범위 (시가와 종가 사이)
                candle_top = max(candle['open_price'], candle['close_price'])
                candle_bottom = min(candle['open_price'], candle['close_price'])

                # 종가 수평선이 캔들 몸통을 지나가는지 확인
                if candle_bottom <= close_price <= candle_top:
                    overlap_count += 1
                    overlapping_candles.append({
                        'index': i,
                        'date': candle.get('date', ''),
                        'body_size': abs(candle['close_price'] - candle['open_price'])
                    })

            # 최소 3개 이상 캔들과 중첩되는 종가만 후보로 선정
            if overlap_count >= 3:
                overlap_results[close_price] = {
                    'price': close_price,
                    'overlap_count': overlap_count,
                    'overlapping_candles': overlapping_candles
                }

        if not overlap_results:
            print(f"   ⚠️ {timeframe}: 3개 이상 중첩되는 종가가 없음")
            return {
                'timeframe': timeframe,
                'data_count': len(candle_data),
                'support': None,
                'resistance': None,
                'total_candidates': 0
            }

        # 현재가 기준으로 지지선/저항선 분류
        support_candidates = {price: data for price, data in overlap_results.items()
                              if price < current_price * 0.99}  # 현재가보다 1% 이상 아래
        resistance_candidates = {price: data for price, data in overlap_results.items()
                                 if price > current_price * 1.01}  # 현재가보다 1% 이상 위

        # 가장 강력한 지지선/저항선 선택 (중첩도 기준)
        strongest_support = None
        strongest_resistance = None

        if support_candidates:
            strongest_support_data = max(support_candidates.values(),
                                         key=lambda x: x['overlap_count'])
            strongest_support = {
                'price': strongest_support_data['price'],
                'overlap_count': strongest_support_data['overlap_count'],
                'distance_percent': ((current_price - strongest_support_data['price']) / current_price * 100)
            }

        if resistance_candidates:
            strongest_resistance_data = max(resistance_candidates.values(),
                                            key=lambda x: x['overlap_count'])
            strongest_resistance = {
                'price': strongest_resistance_data['price'],
                'overlap_count': strongest_resistance_data['overlap_count'],
                'distance_percent': ((strongest_resistance_data['price'] - current_price) / current_price * 100)
            }

        print(f"   📊 후보 종가: {len(overlap_results)}개")
        if strongest_support:
            print(f"   🔻 최강 지지선: {strongest_support['price']:,.0f}원 ({strongest_support['overlap_count']}개 중첩)")
        if strongest_resistance:
            print(f"   🔺 최강 저항선: {strongest_resistance['price']:,.0f}원 ({strongest_resistance['overlap_count']}개 중첩)")

        return {
            'timeframe': timeframe,
            'data_count': len(candle_data),
            'total_candidates': len(overlap_results),
            'support': strongest_support,
            'resistance': strongest_resistance
        }

    def analyze_detailed_supply_demand(self, supply_data: List[Dict]) -> Dict:
        """세분화된 수급 분석 (다양한 기간별 종합 분석)"""

        print(f"\n💰 세분화된 수급 분석 (종합 기간별)")
        print("─" * 60)

        # 다양한 기간별 분석
        periods = {
            '1년': 252,
            '6개월': 126,
            '1달': 30,
            '보름': 15,
            '일주일': 7
        }

        period_analysis = {}

        for period_name, days in periods.items():
            period_data = supply_data[:days] if len(supply_data) >= days else supply_data
            if period_data:
                period_analysis[period_name] = self._analyze_period_supply(period_data, period_name)

        # 기본 분석은 1달 기준
        main_analysis_data = supply_data[:30] if len(supply_data) >= 30 else supply_data

        # 투자주체별 누적 순매수 계산 (백만원 단위)
        investors = {
            'individual': {'name': '개인투자자', 'total': 0, 'field': 'individual_investor'},
            'foreign': {'name': '외국인투자자', 'total': 0, 'field': 'foreign_investment'},
            'financial': {'name': '금융투자', 'total': 0, 'field': 'financial_investment'},
            'insurance': {'name': '보험사', 'total': 0, 'field': 'insurance'},
            'investment_trust': {'name': '투신(펀드)', 'total': 0, 'field': 'investment_trust'},
            'pension': {'name': '연기금', 'total': 0, 'field': 'pension_fund'},
            'private_fund': {'name': '사모펀드', 'total': 0, 'field': 'private_fund'},
            'bank': {'name': '은행', 'total': 0, 'field': 'bank'},
            'other_finance': {'name': '기타금융', 'total': 0, 'field': 'other_finance'},
            'government': {'name': '국가', 'total': 0, 'field': 'government'}
        }

        # 누적 계산
        for day in main_analysis_data:
            for key, investor in investors.items():
                field = investor['field']
                if field in day and day[field] is not None:
                    investors[key]['total'] += day[field]

        # 순위 매기기 (매수 우선, 절댓값 기준)
        sorted_investors = sorted(investors.items(), key=lambda x: x[1]['total'], reverse=True)

        # 수급 단계 진단
        supply_phase = self.diagnose_supply_phase(investors)

        # 세력 분석
        dominant_forces = self.analyze_dominant_forces(main_analysis_data, investors)

        return {
            'analysis_period': len(main_analysis_data),
            'period_analysis': period_analysis,
            'investors_ranking': sorted_investors,
            'supply_phase': supply_phase,
            'dominant_forces': dominant_forces,
            'daily_trends': self.calculate_daily_trends_fixed(main_analysis_data[:7])  # 최근 7일 트렌드
        }

    def _analyze_period_supply(self, period_data: List[Dict], period_name: str) -> Dict:
        """기간별 수급 분석"""

        # 투자주체별 합계 계산
        totals = {}
        fields = ['individual_investor', 'foreign_investment', 'financial_investment',
                  'insurance', 'investment_trust', 'pension_fund', 'private_fund']

        for field in fields:
            totals[field] = sum(day.get(field, 0) for day in period_data if day.get(field) is not None)

        # 스마트머니 vs 개인 비교
        smart_money = totals['foreign_investment'] + totals['pension_fund'] + totals['insurance']
        individual_money = totals['individual_investor']

        return {
            'period': period_name,
            'days': len(period_data),
            'smart_money': smart_money,
            'individual_money': individual_money,
            'net_flow': smart_money + individual_money,
            'totals': totals
        }

    def diagnose_supply_phase(self, investors: Dict) -> Dict:
        """수급 단계 진단 (백만원 단위 기준)"""

        foreign_total = investors['foreign']['total']
        pension_total = investors['pension']['total']
        insurance_total = investors['insurance']['total']
        individual_total = investors['individual']['total']

        # 스마트머니 (외국인 + 연기금 + 보험) - 백만원 단위
        smart_money = foreign_total + pension_total + insurance_total

        if smart_money > 100 and individual_total < 0:  # 100백만원(1억원) 이상, 개인 매도
            phase = "1단계: 스마트머니 유입"
            signal = "적극 매수 타이밍"
            confidence = 0.9
        elif smart_money > 0 and individual_total > -50:  # 개인 소폭 매도(-50백만원 이상)
            phase = "2단계: 상승 진행"
            signal = "추가 매수 고려"
            confidence = 0.7
        elif individual_total > 100:  # 개인 대량 매수(100백만원 이상)
            phase = "3단계: 과열 주의"
            signal = "분할 매도 검토"
            confidence = 0.8
        elif individual_total > 200 and smart_money < 0:  # 개인만 매수(200백만원 이상)
            phase = "4단계: 고점 경고"
            signal = "즉시 매도 검토"
            confidence = 0.9
        else:
            phase = "중립 단계"
            signal = "관망"
            confidence = 0.5

        return {
            'phase': phase,
            'signal': signal,
            'confidence': confidence,
            'smart_money_total': smart_money,
            'individual_total': individual_total
        }

    def analyze_dominant_forces(self, recent_data: List[Dict], investors: Dict) -> Dict:
        """주도 세력 분석"""

        # 최근 5일간 연속 매수 세력 찾기
        consecutive_buyers = {}

        for key, investor in investors.items():
            if key == 'individual':  # 개인 제외
                continue

            field = investor['field']
            consecutive_days = 0

            for day in recent_data[:5]:
                if field in day and day[field] is not None and day[field] > 0:
                    consecutive_days += 1
                else:
                    break

            if consecutive_days >= 3:  # 3일 이상 연속 매수
                consecutive_buyers[key] = {
                    'name': investor['name'],
                    'consecutive_days': consecutive_days,
                    'total_amount': investor['total']
                }

        # 최대 순매수 세력 (개인 제외)
        non_individual_investors = {k: v for k, v in investors.items() if k != 'individual'}
        if non_individual_investors:
            max_buyer = max(non_individual_investors.items(), key=lambda x: x[1]['total'])
            max_buyer_info = {
                'name': max_buyer[1]['name'],
                'amount': max_buyer[1]['total']
            } if max_buyer[1]['total'] > 0 else None
        else:
            max_buyer_info = None

        return {
            'consecutive_buyers': consecutive_buyers,
            'max_buyer': max_buyer_info
        }

    def calculate_daily_trends_fixed(self, recent_days: List[Dict]) -> List[Dict]:
        """최근 일별 트렌드 (날짜 수정 버전)"""

        trends = []

        for day in recent_days:
            # 실제 DB 날짜 필드 직접 사용
            raw_date = day.get('date', '')

            # 날짜 추출 및 변환
            if isinstance(raw_date, str):
                # "2025-08-13" 형식에서 "08-13" 추출
                if len(raw_date) >= 10 and '-' in raw_date:
                    try:
                        parts = raw_date[:10].split('-')  # YYYY-MM-DD
                        if len(parts) == 3:
                            display_date = f"{parts[1]}-{parts[2]}"  # MM-DD
                        else:
                            display_date = raw_date[-5:] if len(raw_date) >= 5 else raw_date
                    except:
                        display_date = raw_date[-5:] if len(raw_date) >= 5 else "??-??"
                else:
                    display_date = str(raw_date)[-5:] if raw_date else "??-??"
            else:
                # datetime 객체인 경우
                try:
                    display_date = raw_date.strftime('%m-%d')
                except:
                    display_date = "??-??"

            day_trend = {
                'date': display_date,
                'foreign': day.get('foreign_investment', 0),
                'pension': day.get('pension_fund', 0),
                'investment_trust': day.get('investment_trust', 0),
                'individual': day.get('individual_investor', 0)
            }
            trends.append(day_trend)

        return trends

    def print_analysis_result(self, result: Dict):
        """분석 결과 출력"""

        stock_info = result['stock_info']
        price_analysis = result['price_analysis']
        supply_analysis = result['supply_analysis']

        print(f"\n🎯 {stock_info['name']} ({stock_info['code']}) 종합 분석 결과")
        print("=" * 80)
        print(f"💰 현재가: {stock_info['current_price']:,}원")
        print(f"📅 분석일: {stock_info['analysis_date']}")

        # 핵심 가격대 분석
        print(f"\n📈 핵심 가격대 분석")
        print("=" * 60)

        conversion_summary = price_analysis.get('conversion_summary', {})
        print(f"📊 변환 요약:")
        print(f"   일봉: {conversion_summary.get('daily_count', 0)}개")
        print(f"   주봉: {conversion_summary.get('weekly_count', 0)}개")
        print(f"   월봉: {conversion_summary.get('monthly_count', 0)}개")

        timeframes = ['daily', 'weekly', 'monthly']
        timeframe_names = {'daily': '일봉(1년)', 'weekly': '주봉(3년)', 'monthly': '월봉(전체)'}

        for tf in timeframes:
            analysis = price_analysis[f'{tf}_analysis']
            data_count = analysis.get('data_count', 0)
            total_candidates = analysis.get('total_candidates', 0)
            print(f"\n📊 {timeframe_names[tf]} 분석 ({data_count}개 캔들)")

            if analysis.get('resistance'):
                res = analysis['resistance']
                print(
                    f"   🔺 저항선: {res['price']:,.0f}원 (+{res['distance_percent']:.1f}%, {res['overlap_count']}개 캔들 중첩)")
            else:
                print("   🔺 저항선: 중첩도 3개 미만 (의미있는 저항선 없음)")

            if analysis.get('support'):
                sup = analysis['support']
                print(
                    f"   🔻 지지선: {sup['price']:,.0f}원 (-{sup['distance_percent']:.1f}%, {sup['overlap_count']}개 캔들 중첩)")
            else:
                print("   🔻 지지선: 중첩도 3개 미만 (의미있는 지지선 없음)")

            if total_candidates > 0:
                print(f"   💡 분석된 종가 후보: {total_candidates}개")

        # 세분화된 수급 분석
        print(f"\n💰 세분화된 수급 분석 (최근 {supply_analysis['analysis_period']}일)")
        print("=" * 60)

        # 기간별 종합 분석 출력
        if 'period_analysis' in supply_analysis and supply_analysis['period_analysis']:
            print(f"\n📊 기간별 수급 추세 종합 (단위: 백만원):")
            print("─" * 60)
            print("기간     스마트머니        개인          순흐름")
            print("─" * 60)

            for period_name, period_data in supply_analysis['period_analysis'].items():
                smart_money = period_data['smart_money']
                individual_money = period_data['individual_money']
                net_flow = period_data['net_flow']

                # 백만원 단위 포맷팅
                if abs(smart_money) >= 1000:
                    smart_str = f"{smart_money / 1000:+6.1f}십억"
                else:
                    smart_str = f"{smart_money:+6.0f}백만"

                if abs(individual_money) >= 1000:
                    individual_str = f"{individual_money / 1000:+6.1f}십억"
                else:
                    individual_str = f"{individual_money:+6.0f}백만"

                if abs(net_flow) >= 1000:
                    net_str = f"{net_flow / 1000:+6.1f}십억"
                else:
                    net_str = f"{net_flow:+6.0f}백만"

                print(f"{period_name:>4s}   {smart_str:>10s}   {individual_str:>10s}   {net_str:>10s}")

            print("─" * 60)
            print("💡 스마트머니 = 외국인 + 연기금 + 보험")
        else:
            print(f"\n⚠️ 기간별 수급 분석 데이터 부족")

        # 수급 단계
        phase = supply_analysis['supply_phase']
        print(f"\n🎯 {phase['phase']}")
        print(f"💡 투자전략: {phase['signal']}")
        print(f"🎲 신뢰도: {phase['confidence']:.0%}")

        # 세력별 순매수 순위 (1달 기준)
        print(f"\n📊 투자주체별 1달 순매수 순위 (단위: 백만원):")
        print("─" * 50)

        for i, (key, investor) in enumerate(supply_analysis['investors_ranking'], 1):
            amount = investor['total']  # 이미 백만원 단위

            # 백만원 단위 그대로 표시
            if abs(amount) >= 1000:
                amount_str = f"{amount / 1000:+.1f}십억"
            elif abs(amount) >= 100:
                amount_str = f"{amount:+.0f}백만"
            else:
                amount_str = f"{amount:+.0f}백만"

            if amount > 0:
                emoji = "🟢"
            elif amount < 0:
                emoji = "🔴"
            else:
                emoji = "⚪"

            print(f"{i:2d}. {emoji} {investor['name']:<12s}: {amount_str:>10s}")

        # 주도 세력 분석
        dominant = supply_analysis['dominant_forces']
        if dominant['consecutive_buyers']:
            print(f"\n🔥 연속 매수 세력:")
            for key, buyer in dominant['consecutive_buyers'].items():
                print(f"   • {buyer['name']}: {buyer['consecutive_days']}일 연속 매수")

        if dominant['max_buyer']:
            max_buyer = dominant['max_buyer']
            max_amount = max_buyer['amount']  # 백만원 단위
            if abs(max_amount) >= 1000:
                max_amount_str = f"{max_amount / 1000:.1f}십억원"
            else:
                max_amount_str = f"{max_amount:.0f}백만원"
            print(f"\n👑 최대 순매수: {max_buyer['name']} ({max_amount_str})")

        # 최근 7일 트렌드 (날짜 수정)
        print(f"\n📈 최근 7일 일별 순매수 트렌드 (단위: 백만원)")
        print("─" * 70)
        print("날짜    외국인    연기금    투신      개인")
        print("─" * 70)

        for trend in supply_analysis['daily_trends']:
            print(f"{trend['date']}   {trend['foreign']:+6.0f}   {trend['pension']:+6.0f}   "
                  f"{trend['investment_trust']:+6.0f}   {trend['individual']:+6.0f}")

        print("=" * 80)


def main():
    """메인 테스트 함수"""

    print("🚀 삼성전자 종목 상세 차트 분석 테스트")
    print("💡 실제 DB 데이터를 활용한 종합 분석")
    print("=" * 80)

    try:
        analyzer = SamsungStockAnalyzer()
        result = analyzer.analyze_samsung_stock()

        if result:
            print(f"\n✅ 삼성전자 분석 완료!")
            print("💡 이 데이터를 Chart.js로 시각화하면 완벽한 종목 상세 페이지가 됩니다.")
        else:
            print("❌ 분석 실패")

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()