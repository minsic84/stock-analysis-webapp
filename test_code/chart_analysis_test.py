#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
실전 차트+수급 분석 테스트 파일
- 52주 신고가 필터링
- 신고가 점수 (5일/20일/60일)
- 실전 수급 분석 (외국인 5일 패턴, 개인 역지표)
- 종합 점수 산출
"""

import sys
import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
import re

# 프로젝트 루트 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.top_rate_analysi.database import TopRateDatabase


class ChartSupplyAnalyzer:
    """차트+수급 종합 분석기"""

    def __init__(self):
        self.db = TopRateDatabase()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def run_comprehensive_analysis(self, analysis_date='2025-08-12'):
        """종합 분석 실행"""
        print("🚀 실전 차트+수급 종합 분석 시작")
        print("=" * 80)
        print(f"📅 분석 날짜: {analysis_date}")
        print("🎯 분석 순서: 52주신고가 필터링 → 차트분석 → 수급분석 → 종합점수")
        print("=" * 80)

        try:
            # 1단계: 분석 대상 종목 리스트 조회
            print("\n📋 1단계: 분석 대상 종목 조회")
            print("─" * 60)

            # AI 분석 결과에서 종목 리스트 추출
            ai_results = self.db.get_ai_analysis(analysis_date)
            if not ai_results:
                print(f"❌ {analysis_date} AI 분석 결과가 없습니다")
                return False

            종목_리스트 = [(r['stock_code'], r['stock_name']) for r in ai_results]
            print(f"✅ 총 {len(종목_리스트)}개 종목 발견")

            # 2단계: 52주 신고가 필터링
            print(f"\n📈 2단계: 52주 신고가 필터링")
            print("─" * 60)

            신고가_종목들 = self.filter_52week_high_stocks(종목_리스트)

            if not 신고가_종목들:
                print("❌ 52주 신고가 조건을 만족하는 종목이 없습니다")
                return False

            print(f"✅ 52주 신고가 필터링 완료: {len(신고가_종목들)}개 종목")
            for stock in 신고가_종목들[:5]:  # 상위 5개만 미리보기
                print(f"   • {stock['종목명']} ({stock['종목코드']}): 신고가 달성일 {stock['신고가달성일']}")

            if len(신고가_종목들) > 5:
                print(f"   ... 외 {len(신고가_종목들) - 5}개 종목")

            # 3단계: 차트+수급 종합 분석
            print(f"\n🔍 3단계: 차트+수급 종합 분석")
            print("─" * 60)

            최종_분석_결과들 = []

            for i, stock_info in enumerate(신고가_종목들):
                종목코드 = stock_info['종목코드']
                종목명 = stock_info['종목명']

                print(f"\n[{i + 1}/{len(신고가_종목들)}] {종목명} ({종목코드}) 분석 중...")
                print("─" * 50)

                try:
                    # 차트 분석 + 신고가 점수
                    차트_결과 = self.analyze_chart_and_new_high_score(종목코드, 종목명)

                    # 실전 수급 분석
                    수급_결과 = self.analyze_practical_supply_demand(종목코드, 종목명)

                    # 종합 점수 계산
                    종합_결과 = self.calculate_comprehensive_score(
                        stock_info, 차트_결과, 수급_결과
                    )

                    최종_분석_결과들.append({
                        "종목정보": stock_info,
                        "차트분석": 차트_결과,
                        "수급분석": 수급_결과,
                        "종합평가": 종합_결과
                    })

                    # 결과 출력
                    self._print_single_analysis_result(종목명, 차트_결과, 수급_결과, 종합_결과)

                except Exception as e:
                    print(f"   ❌ {종목명} 분석 실패: {e}")
                    continue

                # 잠시 대기 (API 부하 방지)
                time.sleep(1)

            # 4단계: 최종 결과 요약 및 DB 저장
            print(f"\n🎯 4단계: 최종 분석 결과 및 DB 저장")
            print("=" * 80)

            if 최종_분석_결과들:
                self._print_final_summary(최종_분석_결과들)

                # DB 자동 저장 (필수)
                print(f"\n💾 분석 결과 DB 저장 중...")
                self._save_analysis_results(analysis_date, 최종_분석_결과들)

                return True
            else:
                print("❌ 분석 완료된 종목이 없습니다")
                return False

        except Exception as e:
            print(f"❌ 종합 분석 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

    def filter_52week_high_stocks(self, 종목_리스트: List[tuple]) -> List[Dict]:
        """52주 신고가 종목 필터링"""
        print("🔍 52주 신고가 조건 확인 중...")

        신고가_종목들 = []

        for i, (종목코드, 종목명) in enumerate(종목_리스트):
            try:
                print(f"   [{i + 1}/{len(종목_리스트)}] {종목명} 확인 중...", end="")

                # 1년치 일봉 데이터 가져오기 (모의 데이터)
                일봉_데이터 = self._get_daily_price_data(종목코드, 252)

                if not 일봉_데이터:
                    print(" ❌ 데이터 없음")
                    continue

                # 52주 최고가 계산
                최고가_52주 = max([day['high'] for day in 일봉_데이터])
                현재가 = 일봉_데이터[0]['close']

                # 최근 1년 내 52주 신고가 달성 여부 확인
                신고가_달성일 = None
                for day in 일봉_데이터[:252]:  # 최근 1년
                    if day['high'] >= 최고가_52주 * 0.99:  # 99% 이상도 신고가로 인정
                        신고가_달성일 = day['date']
                        break

                if 신고가_달성일:
                    현재가_vs_52주고가 = (현재가 / 최고가_52주 - 1) * 100

                    신고가_종목들.append({
                        "종목코드": 종목코드,
                        "종목명": 종목명,
                        "52주최고가": 최고가_52주,
                        "현재가": 현재가,
                        "신고가달성일": 신고가_달성일,
                        "현재가_vs_52주고가": 현재가_vs_52주고가
                    })
                    print(f" ✅ 신고가 달성 ({신고가_달성일})")
                else:
                    print(" ❌ 신고가 미달성")

            except Exception as e:
                print(f" ❌ 오류: {e}")
                continue

        # 신고가 달성일 순으로 정렬 (최근순)
        신고가_종목들.sort(key=lambda x: x['신고가달성일'], reverse=True)

        return 신고가_종목들

    def analyze_chart_and_new_high_score(self, 종목코드: str, 종목명: str) -> Dict:
        """차트 분석 + 신고가 점수"""

        # 각 기간별 일봉 데이터
        일봉_5일 = self._get_daily_price_data(종목코드, 5)
        일봉_20일 = self._get_daily_price_data(종목코드, 20)
        일봉_60일 = self._get_daily_price_data(종목코드, 60)

        if not 일봉_60일:
            raise ValueError("차트 데이터를 가져올 수 없습니다")

        현재가 = 일봉_5일[0]['close']

        # 각 기간별 최고가
        최고가_5일 = max([day['high'] for day in 일봉_5일])
        최고가_20일 = max([day['high'] for day in 일봉_20일])
        최고가_60일 = max([day['high'] for day in 일봉_60일])

        # 신고가 여부 및 점수 계산
        신고가_점수 = 0
        신고가_상태 = []

        if 현재가 >= 최고가_5일 * 0.995:  # 99.5% 이상도 신고가로 인정
            신고가_점수 += 5
            신고가_상태.append("5일신고가")

        if 현재가 >= 최고가_20일 * 0.995:
            신고가_점수 += 15
            신고가_상태.append("20일신고가")

        if 현재가 >= 최고가_60일 * 0.995:
            신고가_점수 += 25
            신고가_상태.append("60일신고가")

        # 연속 신고가 보너스
        if len(신고가_상태) >= 3:  # 5일+20일+60일 모두
            신고가_점수 += 10
            신고가_상태.append("완전신고가")

        # 이동평균선 분석
        이동평균_분석 = self._calculate_moving_averages(일봉_60일)

        # 차트 패턴 분석 (간단 버전)
        차트_패턴 = self._analyze_chart_pattern(일봉_60일)

        return {
            "신고가_점수": 신고가_점수,
            "신고가_상태": 신고가_상태,
            "신고가_세부": {
                "5일신고가": 현재가 >= 최고가_5일 * 0.995,
                "20일신고가": 현재가 >= 최고가_20일 * 0.995,
                "60일신고가": 현재가 >= 최고가_60일 * 0.995,
                "현재가": 현재가,
                "5일최고가": 최고가_5일,
                "20일최고가": 최고가_20일,
                "60일최고가": 최고가_60일
            },
            "이동평균_분석": 이동평균_분석,
            "차트_패턴": 차트_패턴
        }

    def analyze_practical_supply_demand(self, 종목코드: str, 종목명: str) -> Dict:
        """실전 수급 분석 (외국인 5일 패턴 + 개인 역지표)"""

        # 수급 데이터 가져오기 (모의 데이터)
        수급_데이터 = self._get_supply_demand_data(종목코드, 365)

        if not 수급_데이터:
            # 수급 데이터가 없으면 기본값 반환
            return self._get_default_supply_analysis()

        # 외국인 패턴 분석
        외국인_분석 = self._analyze_foreign_pattern(수급_데이터)

        # 기관 분석 (고급 vs 일반)
        기관_분석 = self._analyze_institution_pattern(수급_데이터)

        # 개인 역지표 분석
        개인_분석 = self._analyze_retail_pattern(수급_데이터)

        # 수급 위험도 평가
        위험도_평가 = self._assess_supply_risk(외국인_분석, 기관_분석, 개인_분석)

        # 수급 점수 계산
        수급_점수 = self._calculate_supply_score(외국인_분석, 기관_분석, 개인_분석, 위험도_평가)

        return {
            "외국인_분석": 외국인_분석,
            "기관_분석": 기관_분석,
            "개인_분석": 개인_분석,
            "위험도_평가": 위험도_평가,
            "수급_점수": 수급_점수,
            "핵심_시사점": self._get_supply_insights(외국인_분석, 기관_분석, 개인_분석)
        }

    def calculate_comprehensive_score(self, stock_info: Dict, 차트_결과: Dict, 수급_결과: Dict) -> Dict:
        """종합 점수 계산"""

        점수_구성 = {
            "신고가_점수": 차트_결과['신고가_점수'],  # 최대 55점
            "수급_점수": 수급_결과['수급_점수'],  # 최대 50점
            "차트_보너스": self._calculate_chart_bonus(차트_결과),  # 최대 15점
        }

        총점 = sum(점수_구성.values())
        최종점수 = min(100, max(0, 총점))

        # 투자 의견 결정
        if 최종점수 >= 80 and 수급_결과['위험도_평가']['위험도'] == '낮음':
            투자의견 = "강력매수"
        elif 최종점수 >= 65:
            투자의견 = "매수"
        elif 최종점수 >= 45:
            투자의견 = "관심"
        else:
            투자의견 = "관망"

        # 신뢰도 계산
        신뢰도 = self._calculate_confidence(점수_구성, 차트_결과, 수급_결과)

        # 스마트 코멘트 생성
        스마트_코멘트 = self._generate_smart_comment(차트_결과, 수급_결과, 총점, 투자의견)

        return {
            "점수_구성": 점수_구성,
            "총점": 총점,
            "최종점수": 최종점수,
            "투자의견": 투자의견,
            "신뢰도": 신뢰도,
            "스마트_코멘트": 스마트_코멘트,
            "핵심_강점": self._identify_key_strengths(차트_결과, 수급_결과),
            "주의사항": self._identify_risks(차트_결과, 수급_결과)
        }

    def _get_daily_price_data(self, 종목코드: str, days: int) -> List[Dict]:
        """일봉 데이터 가져오기 (크롤링 DB 현재가 활용)"""

        try:
            # 1. 실제 차트 데이터가 있는지 확인 (추후 구현)
            # chart_data = self._fetch_real_chart_data(종목코드, days)
            # if chart_data:
            #     return chart_data

            # 2. 차트 데이터가 없으면 크롤링 DB에서 현재가 가져와서 모의 데이터 생성
            current_price = self._get_current_price_from_crawling_db(종목코드)

            if current_price:
                return self._generate_mock_chart_data(current_price, days)
            else:
                # 3. 크롤링 DB에도 없으면 기본 모의 데이터
                return self._generate_default_mock_data(days)

        except Exception as e:
            print(f"   ⚠️ 차트 데이터 오류 ({종목코드}): {e}")
            return self._generate_default_mock_data(days)

    def _get_current_price_from_crawling_db(self, 종목코드: str) -> Optional[int]:
        """크롤링 DB에서 현재가 가져오기"""

        try:
            # 최신 테마 테이블에서 현재가 조회
            today = datetime.now().strftime('%Y%m%d')
            table_name = f"theme_{today}"

            connection = self.db.get_connection(self.db.crawling_db)
            cursor = connection.cursor()

            query = f"""
            SELECT price, change_rate, volume 
            FROM {table_name} 
            WHERE stock_code = %s 
            LIMIT 1
            """

            cursor.execute(query, (종목코드,))
            result = cursor.fetchone()

            cursor.close()
            connection.close()

            if result:
                print(f" [크롤링DB 현재가: {result[0]:,}원]")
                return result[0]

            return None

        except Exception as e:
            # 오늘 테이블이 없으면 어제 또는 최신 테이블 찾기
            try:
                return self._get_latest_price_from_any_table(종목코드)
            except:
                return None

    def _get_latest_price_from_any_table(self, 종목코드: str) -> Optional[int]:
        """가장 최신 테마 테이블에서 현재가 찾기"""

        try:
            connection = self.db.get_connection(self.db.crawling_db)
            cursor = connection.cursor()

            # 테마 테이블들 조회
            cursor.execute("SHOW TABLES LIKE 'theme_%'")
            tables = [table[0] for table in cursor.fetchall()]

            # 최신 테이블부터 검색
            tables.sort(reverse=True)

            for table in tables[:5]:  # 최근 5개 테이블만 확인
                try:
                    query = f"SELECT price FROM {table} WHERE stock_code = %s LIMIT 1"
                    cursor.execute(query, (종목코드,))
                    result = cursor.fetchone()

                    if result:
                        print(f" [DB테이블 {table}: {result[0]:,}원]")
                        cursor.close()
                        connection.close()
                        return result[0]
                except:
                    continue

            cursor.close()
            connection.close()
            return None

        except Exception as e:
            return None

    def _generate_mock_chart_data(self, current_price: int, days: int) -> List[Dict]:
        """현재가 기준 모의 차트 데이터 생성"""

        import random

        chart_data = []
        base_price = current_price

        # 과거부터 현재까지 역순으로 생성
        for i in range(days - 1, -1, -1):
            date = datetime.now() - timedelta(days=i)

            if i == 0:  # 오늘 (가장 최근)
                close = current_price
                high = close * random.uniform(1.0, 1.02)
                low = close * random.uniform(0.98, 1.0)
                open_price = close * random.uniform(0.99, 1.01)
            else:
                # 현재가 기준으로 역산하여 과거 가격 추정
                variation = random.uniform(0.95, 1.05)
                close = int(base_price * variation)
                high = int(close * random.uniform(1.0, 1.03))
                low = int(close * random.uniform(0.97, 1.0))
                open_price = int(close * random.uniform(0.99, 1.01))
                base_price = close

            volume = random.randint(500000, 3000000)

            chart_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })

        # 최신 날짜부터 정렬 (index 0이 가장 최근)
        chart_data.reverse()
        return chart_data

    def _generate_default_mock_data(self, days: int) -> List[Dict]:
        """기본 모의 데이터 생성"""

        import random

        chart_data = []
        base_price = random.randint(50000, 100000)  # 기본 가격대

        for i in range(days):
            date = datetime.now() - timedelta(days=i)

            variation = random.uniform(0.98, 1.02)
            close = int(base_price * variation)
            high = int(close * random.uniform(1.0, 1.03))
            low = int(close * random.uniform(0.97, 1.0))
            open_price = int(close * random.uniform(0.99, 1.01))
            volume = random.randint(500000, 2000000)

            chart_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })

            base_price = close

        return chart_data

    def _get_supply_demand_data(self, 종목코드: str, days: int) -> List[Dict]:
        """수급 데이터 가져오기 (모의 데이터)"""

        import random

        # 실제로는 여기서 실제 수급 데이터를 가져와야 함
        # 현재는 모의 데이터 생성
        supply_data = []

        for i in range(days):
            date = datetime.now() - timedelta(days=i)

            # 외국인: 간헐적 대량 매수
            if random.random() < 0.3:  # 30% 확률로 매수
                외국인_매수 = random.randint(1000000, 5000000)
                외국인_매도 = random.randint(100000, 1000000)
            else:
                외국인_매수 = random.randint(100000, 1000000)
                외국인_매도 = random.randint(1000000, 3000000)

            # 기관: 지속적 매수
            기관_매수 = random.randint(500000, 2000000)
            기관_매도 = random.randint(300000, 1500000)

            # 개인: 변동성 큰 매매
            개인_매수 = random.randint(2000000, 8000000)
            개인_매도 = random.randint(2000000, 8000000)

            supply_data.append({
                'date': date.strftime('%Y-%m-%d'),
                '외국인_매수': 외국인_매수,
                '외국인_매도': 외국인_매도,
                '기관_매수': 기관_매수,
                '기관_매도': 기관_매도,
                '개인_매수': 개인_매수,
                '개인_매도': 개인_매도,
                # 세분화된 기관 데이터 (모의)
                '연기금_매수': random.randint(100000, 800000),
                '연기금_매도': random.randint(50000, 400000),
                '대형운용사_매수': random.randint(200000, 1000000),
                '대형운용사_매도': random.randint(100000, 500000),
            })

        return supply_data

    def _analyze_foreign_pattern(self, 수급_데이터: List[Dict]) -> Dict:
        """외국인 패턴 분석: 5일 상승 후 차익실현 패턴"""

        외국인_매수_구간들 = []
        현재_매수_구간 = None

        for i, day in enumerate(수급_데이터):
            외국인_순매수 = day['외국인_매수'] - day['외국인_매도']

            if 외국인_순매수 > 0:  # 매수일
                if 현재_매수_구간 is None:
                    현재_매수_구간 = {
                        "시작일": day['date'],
                        "지속일수": 1,
                        "누적매수": 외국인_순매수
                    }
                else:
                    현재_매수_구간["지속일수"] += 1
                    현재_매수_구간["누적매수"] += 외국인_순매수

            elif 외국인_순매수 < 0 and 현재_매수_구간:  # 매도 전환
                현재_매수_구간["종료일"] = day['date']
                외국인_매수_구간들.append(현재_매수_구간)
                현재_매수_구간 = None

        # 최근 30일 외국인 상태
        최근_30일 = 수급_데이터[:30]
        최근_외국인_순매수 = sum([day['외국인_매수'] - day['외국인_매도'] for day in 최근_30일])
        최근_연속_매수일 = self._calculate_consecutive_buying_days(최근_30일, '외국인')

        # 차익실현 위험도 평가
        차익실현_위험도 = "낮음"
        if 최근_연속_매수일 >= 5:
            차익실현_위험도 = "높음"
        elif 최근_연속_매수일 >= 3:
            차익실현_위험도 = "보통"

        return {
            "총_매수구간": len(외국인_매수_구간들),
            "평균_매수지속일": sum([구간["지속일수"] for 구간 in 외국인_매수_구간들]) / len(외국인_매수_구간들) if 외국인_매수_구간들 else 0,
            "최근_30일_순매수": 최근_외국인_순매수,
            "현재_연속_매수일": 최근_연속_매수일,
            "차익실현_위험도": 차익실현_위험도,
            "외국인_상태": "매수세" if 최근_외국인_순매수 > 0 else "매도세"
        }

    def _analyze_institution_pattern(self, 수급_데이터: List[Dict]) -> Dict:
        """기관 패턴 분석: 고급기관 vs 일반기관"""

        고급기관_데이터 = []
        일반기관_데이터 = []

        for day in 수급_데이터:
            # 고급기관 = 연기금 + 대형운용사
            고급기관_순매수 = (
                    day.get('연기금_매수', 0) - day.get('연기금_매도', 0) +
                    day.get('대형운용사_매수', 0) - day.get('대형운용사_매도', 0)
            )

            # 일반기관 = 전체 기관 - 고급기관
            전체_기관_순매수 = day['기관_매수'] - day['기관_매도']
            일반기관_순매수 = 전체_기관_순매수 - 고급기관_순매수

            고급기관_데이터.append(고급기관_순매수)
            일반기관_데이터.append(일반기관_순매수)

        return {
            "고급기관": {
                "30일_순매수": sum(고급기관_데이터[:30]),
                "매수_지속성": self._calculate_consistency(고급기관_데이터[:30]),
                "활동_강도": "높음" if sum(고급기관_데이터[:30]) > 0 else "낮음"
            },
            "일반기관": {
                "30일_순매수": sum(일반기관_데이터[:30]),
                "변동성": self._calculate_volatility(일반기관_데이터[:30]),
                "신뢰도": "낮음" if self._calculate_volatility(일반기관_데이터[:30]) > 0.5 else "보통"
            }
        }

    def _analyze_retail_pattern(self, 수급_데이터: List[Dict]) -> Dict:
        """개인 역지표 분석"""

        개인_데이터 = [(day['개인_매수'] - day['개인_매도']) for day in 수급_데이터]

        # 개인 대량 매수 구간 탐지
        대량_매수_구간 = 0
        for i in range(len(개인_데이터) - 5):
            구간_5일 = 개인_데이터[i:i + 5]
            if all(day > 0 for day in 구간_5일):  # 5일 연속 순매수
                대량_매수_구간 += 1

        최근_개인_순매수 = sum(개인_데이터[:30])

        return {
            "최근_30일_순매수": 최근_개인_순매수,
            "대량_매수_구간": 대량_매수_구간,
            "역지표_신호": "위험" if 최근_개인_순매수 > 0 else "양호",
            "개인_상태": "매수세" if 최근_개인_순매수 > 0 else "매도세",
            "시사점": "조절 위험" if 최근_개인_순매수 > 0 else "건전한 수급"
        }

    def _assess_supply_risk(self, 외국인_분석: Dict, 기관_분석: Dict, 개인_분석: Dict) -> Dict:
        """수급 위험도 종합 평가"""

        위험_요소들 = []

        # 외국인 차익실현 위험
        if 외국인_분석["차익실현_위험도"] == "높음":
            위험_요소들.append("외국인_차익실현_위험")

        # 개인 역매수 위험
        if 개인_분석["역지표_신호"] == "위험":
            위험_요소들.append("개인_역매수_위험")

        # 기관 신뢰도 위험
        if 기관_분석["일반기관"]["신뢰도"] == "낮음":
            위험_요소들.append("기관_변동성_위험")

        # 위험도 등급
        if len(위험_요소들) >= 2:
            위험도 = "높음"
            점수_감점 = -15
        elif len(위험_요소들) == 1:
            위험도 = "보통"
            점수_감점 = -8
        else:
            위험도 = "낮음"
            점수_감점 = 0

        return {
            "위험도": 위험도,
            "위험_요소들": 위험_요소들,
            "점수_감점": 점수_감점
        }

    def _calculate_supply_score(self, 외국인_분석: Dict, 기관_분석: Dict, 개인_분석: Dict, 위험도_평가: Dict) -> int:
        """수급 점수 계산"""

        점수 = 0

        # 외국인 점수 (최대 35점)
        if 외국인_분석["외국인_상태"] == "매수세":
            점수 += 20

            연속일 = 외국인_분석["현재_연속_매수일"]
            if 1 <= 연속일 <= 3:
                점수 += 15  # 최적 구간
            elif 4 <= 연속일 <= 5:
                점수 += 10  # 주의 구간
            elif 연속일 > 5:
                점수 += 5  # 위험 구간

        # 고급기관 점수 (최대 20점)
        if 기관_분석["고급기관"]["30일_순매수"] > 0:
            점수 += 10
            if 기관_분석["고급기관"]["매수_지속성"] > 0.6:
                점수 += 10

        # 개인 역지표 점수 (최대 10점)
        if 개인_분석["개인_상태"] == "매도세":
            점수 += 10
        elif 개인_분석["개인_상태"] == "매수세":
            점수 -= 5

        # 위험도 차감
        점수 += 위험도_평가["점수_감점"]

        return max(0, min(50, 점수))  # 0~50점 범위

    def _calculate_moving_averages(self, 일봉_데이터: List[Dict]) -> Dict:
        """이동평균선 계산"""

        if len(일봉_데이터) < 60:
            return {"정배열": False, "이동평균선": {}}

        close_prices = [day['close'] for day in 일봉_데이터]

        ma5 = sum(close_prices[:5]) / 5
        ma20 = sum(close_prices[:20]) / 20
        ma60 = sum(close_prices[:60]) / 60

        현재가 = close_prices[0]
        정배열 = ma5 > ma20 > ma60 and 현재가 > ma5

        return {
            "정배열": 정배열,
            "이동평균선": {
                "5일선": ma5,
                "20일선": ma20,
                "60일선": ma60
            },
            "현재가_vs_이평": {
                "vs_5일선": (현재가 / ma5 - 1) * 100,
                "vs_20일선": (현재가 / ma20 - 1) * 100,
                "vs_60일선": (현재가 / ma60 - 1) * 100
            }
        }

    def _analyze_chart_pattern(self, 일봉_데이터: List[Dict]) -> Dict:
        """차트 패턴 분석 (간단 버전)"""

        if len(일봉_데이터) < 20:
            return {"패턴": "데이터부족", "신뢰도": 0}

        close_prices = [day['close'] for day in 일봉_데이터[:20]]

        # 간단한 추세 분석
        최근_5일_평균 = sum(close_prices[:5]) / 5
        과거_5일_평균 = sum(close_prices[10:15]) / 5

        if 최근_5일_평균 > 과거_5일_평균 * 1.05:
            패턴 = "강한상승"
            신뢰도 = 0.8
        elif 최근_5일_평균 > 과거_5일_평균:
            패턴 = "상승"
            신뢰도 = 0.6
        elif 최근_5일_평균 < 과거_5일_평균 * 0.95:
            패턴 = "하락"
            신뢰도 = 0.3
        else:
            패턴 = "횡보"
            신뢰도 = 0.4

        return {
            "패턴": 패턴,
            "신뢰도": 신뢰도
        }

    def _calculate_chart_bonus(self, 차트_결과: Dict) -> int:
        """차트 보너스 점수"""

        점수 = 0

        # 정배열 보너스
        if 차트_결과['이동평균_분석'].get('정배열', False):
            점수 += 10

        # 차트 패턴 보너스
        패턴 = 차트_결과['차트_패턴']['패턴']
        if 패턴 == "강한상승":
            점수 += 5
        elif 패턴 == "상승":
            점수 += 3

        return min(15, 점수)

    def _calculate_confidence(self, 점수_구성: Dict, 차트_결과: Dict, 수급_결과: Dict) -> float:
        """신뢰도 계산"""

        신뢰도 = 0.5  # 기본값

        # 신고가 점수가 높으면 신뢰도 증가
        if 점수_구성['신고가_점수'] >= 40:
            신뢰도 += 0.2

        # 수급이 건전하면 신뢰도 증가
        if 수급_결과['위험도_평가']['위험도'] == '낮음':
            신뢰도 += 0.2

        # 외국인 매수세면 신뢰도 증가
        if 수급_결과['외국인_분석']['외국인_상태'] == '매수세':
            신뢰도 += 0.1

        return min(0.95, 신뢰도)

    def _identify_key_strengths(self, 차트_결과: Dict, 수급_결과: Dict) -> List[str]:
        """핵심 강점 식별"""

        강점들 = []

        # 신고가 관련
        신고가_상태 = 차트_결과['신고가_상태']
        if '60일신고가' in 신고가_상태:
            강점들.append("✅ 60일 신고가 달성 - 중기 모멘텀 강함")
        if '완전신고가' in 신고가_상태:
            강점들.append("✅ 완전 신고가 - 모든 기간 최고점")

        # 이동평균 관련
        if 차트_결과['이동평균_분석'].get('정배열', False):
            강점들.append("✅ 이동평균 정배열 - 기술적 상승세")

        # 수급 관련
        if 수급_결과['외국인_분석']['외국인_상태'] == '매수세':
            연속일 = 수급_결과['외국인_분석']['현재_연속_매수일']
            if 1 <= 연속일 <= 3:
                강점들.append("✅ 외국인 건전한 매수세 - 안정적 수급")
            elif 연속일 > 3:
                강점들.append("⚠️ 외국인 지속 매수 - 차익실현 주의")

        if 수급_결과['개인_분석']['개인_상태'] == '매도세':
            강점들.append("✅ 개인 매도세 - 건전한 손바뀜")

        if 수급_결과['기관_분석']['고급기관']['활동_강도'] == '높음':
            강점들.append("✅ 고급기관 매수 - 펀더멘털 인정")

        return 강점들[:4]  # 최대 4개

    def _identify_risks(self, 차트_결과: Dict, 수급_결과: Dict) -> List[str]:
        """주의사항 식별"""

        위험들 = []

        # 수급 위험
        위험_요소들 = 수급_결과['위험도_평가']['위험_요소들']
        for 위험 in 위험_요소들:
            if 위험 == "외국인_차익실현_위험":
                위험들.append("⚠️ 외국인 차익실현 압력 증가")
            elif 위험 == "개인_역매수_위험":
                위험들.append("⚠️ 개인 매수세 - 조절 위험")
            elif 위험 == "기관_변동성_위험":
                위험들.append("⚠️ 기관 매매 변동성 높음")

        # 차트 위험
        패턴 = 차트_결과['차트_패턴']['패턴']
        if 패턴 == "하락":
            위험들.append("⚠️ 차트 패턴 약화")

        return 위험들[:3]  # 최대 3개

    def _generate_smart_comment(self, 차트_결과: Dict, 수급_결과: Dict, 총점: int, 투자의견: str) -> str:
        """스마트 코멘트 생성 (위험 우선 + 쉬운말 + 액션형)"""

        # 1단계: 주요 위험 식별
        주요_위험 = self._identify_main_risk(수급_결과)

        # 2단계: 현재 상황 분석
        현재_상황 = self._analyze_current_situation(차트_결과, 수급_결과)

        # 3단계: 투자 액션 가이드
        투자_액션 = self._get_investment_action(투자의견, 주요_위험)

        # 4단계: 메시지 조합 (50자 내외)
        if 주요_위험:
            코멘트 = f"⚠️ {주요_위험}. {투자_액션}"
        else:
            코멘트 = f"✅ {현재_상황}. {투자_액션}"

        # 길이 제한 (50자 내외)
        if len(코멘트) > 55:
            코멘트 = 코멘트[:52] + "..."

        return 코멘트

    def _identify_main_risk(self, 수급_결과: Dict) -> Optional[str]:
        """주요 위험 요소 식별"""

        위험_요소들 = 수급_결과['위험도_평가']['위험_요소들']

        if "외국인_차익실현_위험" in 위험_요소들:
            연속일 = 수급_결과['외국인_분석']['현재_연속_매수일']
            return f"외국인 {연속일}일 연속 매수로 차익실현 주의"
        elif "개인_역매수_위험" in 위험_요소들:
            return "개인 매수세로 고점 신호"
        elif "기관_변동성_위험" in 위험_요소들:
            return "기관 매매 변동성 증가"
        else:
            return None

    def _analyze_current_situation(self, 차트_결과: Dict, 수급_결과: Dict) -> str:
        """현재 상황 분석"""

        신고가_상태 = 차트_결과['신고가_상태']
        외국인_상태 = 수급_결과['외국인_분석']['외국인_상태']

        # 신고가 + 수급 조합 메시지
        if '완전신고가' in 신고가_상태:
            if 외국인_상태 == '매수세':
                return "완전 신고가 + 스마트머니 유입으로 폭발적 상승세"
            else:
                return "완전 신고가 달성으로 기술적 돌파 확인"
        elif '60일신고가' in 신고가_상태:
            if 외국인_상태 == '매수세':
                return "60일 신고가 돌파 + 외국인 매수로 중기 상승세"
            else:
                return "60일 신고가 돌파로 중기 모멘텀 전환"
        elif '20일신고가' in 신고가_상태:
            if 외국인_상태 == '매수세':
                return "20일 신고가 + 외국인 매수로 단기 상승세"
            else:
                return "20일 신고가로 단기 상승 모멘텀"
        else:
            if 외국인_상태 == '매수세':
                return "외국인 매수로 상승 모멘텀 형성"
            else:
                return "현재 신고가 권역 접근 중"

    def _get_investment_action(self, 투자의견: str, 주요_위험: Optional[str]) -> str:
        """투자 액션 가이드"""

        if 주요_위험:  # 위험이 있을 때
            if 투자의견 == '강력매수':
                return "소폭 조정 후 분할 매수 권장"
            elif 투자의견 == '매수':
                return "수급 안정화까지 관망 후 진입"
            else:
                return "추가 신호 확인 후 재검토"
        else:  # 위험이 없을 때
            if 투자의견 == '강력매수':
                return "적극 매수 검토 시점"
            elif 투자의견 == '매수':
                return "매수 진입 타이밍"
            elif 투자의견 == '관심':
                return "관심 종목 등록 추천"
            else:
                return "현 시점 진입 부담"

    def _get_default_supply_analysis(self) -> Dict:
        """수급 데이터가 없을 때 기본값"""

        return {
            "외국인_분석": {
                "외국인_상태": "데이터없음",
                "현재_연속_매수일": 0,
                "차익실현_위험도": "알수없음"
            },
            "기관_분석": {
                "고급기관": {"활동_강도": "알수없음"},
                "일반기관": {"신뢰도": "알수없음"}
            },
            "개인_분석": {
                "개인_상태": "데이터없음",
                "역지표_신호": "알수없음"
            },
            "위험도_평가": {
                "위험도": "보통",
                "위험_요소들": [],
                "점수_감점": 0
            },
            "수급_점수": 25,  # 중간 점수
            "핵심_시사점": ["📊 수급 데이터 수집 필요"]
        }

    def _calculate_consecutive_buying_days(self, 데이터: List[Dict], 주체: str) -> int:
        """연속 매수일 계산"""

        연속일 = 0

        for day in 데이터:
            if 주체 == '외국인':
                순매수 = day['외국인_매수'] - day['외국인_매도']
            elif 주체 == '기관':
                순매수 = day['기관_매수'] - day['기관_매도']
            elif 주체 == '개인':
                순매수 = day['개인_매수'] - day['개인_매도']
            else:
                순매수 = 0

            if 순매수 > 0:
                연속일 += 1
            else:
                break

        return 연속일

    def _calculate_consistency(self, 데이터_리스트: List[float]) -> float:
        """지속성 계산 (양수 비율)"""

        if not 데이터_리스트:
            return 0

        양수_개수 = len([x for x in 데이터_리스트 if x > 0])
        return 양수_개수 / len(데이터_리스트)

    def _calculate_volatility(self, 데이터_리스트: List[float]) -> float:
        """변동성 계산 (표준편차/평균)"""

        if not 데이터_리스트 or len(데이터_리스트) < 2:
            return 0

        평균 = sum(데이터_리스트) / len(데이터_리스트)
        if 평균 == 0:
            return 1

        분산 = sum([(x - 평균) ** 2 for x in 데이터_리스트]) / len(데이터_리스트)
        표준편차 = 분산 ** 0.5

        return abs(표준편차 / 평균)

    def _get_supply_insights(self, 외국인_분석: Dict, 기관_분석: Dict, 개인_분석: Dict) -> List[str]:
        """수급 핵심 시사점"""

        시사점들 = []

        # 외국인 관련
        if 외국인_분석["외국인_상태"] == "매수세":
            연속일 = 외국인_분석["현재_연속_매수일"]
            if 연속일 >= 5:
                시사점들.append(f"외국인 {연속일}일 연속 매수 - 차익실현 압력 증가")
            else:
                시사점들.append(f"외국인 매수세 - 건전한 수급 흐름")

        # 개인 관련
        if 개인_분석["개인_상태"] == "매도세":
            시사점들.append("개인 매도세 - 건전한 손바뀜 진행")
        elif 개인_분석["개인_상태"] == "매수세":
            시사점들.append("개인 매수세 - 고점 근처 신호 주의")

        return 시사점들[:3]

    def _print_single_analysis_result(self, 종목명: str, 차트_결과: Dict, 수급_결과: Dict, 종합_결과: Dict):
        """개별 종목 분석 결과 출력"""

        print(f"📊 {종목명} 분석 결과:")

        # 신고가 정보
        신고가_상태 = ', '.join(차트_결과['신고가_상태']) if 차트_결과['신고가_상태'] else '신고가 없음'
        print(f"   🎯 신고가 상태: {신고가_상태} ({차트_결과['신고가_점수']}점)")

        # 현재가 정보
        현재가 = 차트_결과['신고가_세부']['현재가']
        print(f"   💰 현재가: {현재가:,}원")

        # 수급 정보
        외국인_상태 = 수급_결과['외국인_분석']['외국인_상태']
        개인_상태 = 수급_결과['개인_분석']['개인_상태']
        print(f"   💰 수급: 외국인 {외국인_상태}, 개인 {개인_상태} ({수급_결과['수급_점수']}점)")

        # 위험도
        위험도 = 수급_결과['위험도_평가']['위험도']
        print(f"   ⚠️ 위험도: {위험도}")

        # 종합 결과
        최종점수 = 종합_결과['최종점수']
        투자의견 = 종합_결과['투자의견']
        신뢰도 = 종합_결과['신뢰도']
        스마트_코멘트 = 종합_결과['스마트_코멘트']
        print(f"   🎯 종합: {최종점수}점 | {투자의견} | 신뢰도 {신뢰도:.1%}")
        print(f"   💬 {스마트_코멘트}")

        # 핵심 강점 (최대 2개)
        강점들 = 종합_결과['핵심_강점'][:2]
        if 강점들:
            print(f"   ✅ 강점: {' / '.join(강점들)}")

        # 주의사항 (최대 1개)
        위험들 = 종합_결과['주의사항'][:1]
        if 위험들:
            print(f"   ⚠️ 주의: {위험들[0]}")

    def _print_final_summary(self, 분석_결과들: List[Dict]):
        """최종 분석 결과 요약"""

        if not 분석_결과들:
            return

        # 투자의견별 분류
        의견별_통계 = {}
        for result in 분석_결과들:
            의견 = result['종합평가']['투자의견']
            의견별_통계[의견] = 의견별_통계.get(의견, 0) + 1

        print(f"📈 총 분석 종목: {len(분석_결과들)}개")
        print(f"💰 투자의견별 분포:")
        for 의견, 개수 in sorted(의견별_통계.items(), key=lambda x: x[1], reverse=True):
            print(f"   {의견}: {개수}개")

        # 고득점 종목 (80점 이상)
        고득점_종목들 = [r for r in 분석_결과들 if r['종합평가']['최종점수'] >= 80]
        if 고득점_종목들:
            print(f"\n⭐ 고득점 종목 (80점 이상): {len(고득점_종목들)}개")
            for result in sorted(고득점_종목들, key=lambda x: x['종합평가']['최종점수'], reverse=True)[:3]:
                종목명 = result['종목정보']['종목명']
                점수 = result['종합평가']['최종점수']
                의견 = result['종합평가']['투자의견']
                print(f"   🏆 {종목명}: {점수}점 ({의견})")

        # 강력매수 추천
        강력매수_종목들 = [r for r in 분석_결과들 if r['종합평가']['투자의견'] == '강력매수']
        if 강력매수_종목들:
            print(f"\n🚀 강력매수 추천: {len(강력매수_종목들)}개")
            for result in 강력매수_종목들:
                종목명 = result['종목정보']['종목명']
                신고가상태 = ', '.join(result['차트분석']['신고가_상태'][:2])
                수급상태 = result['수급분석']['외국인_분석']['외국인_상태']
                print(f"   🎯 {종목명}: {신고가상태} / 외국인 {수급상태}")

        # 평균 점수
        평균_점수 = sum([r['종합평가']['최종점수'] for r in 분석_결과들]) / len(분석_결과들)
        평균_신뢰도 = sum([r['종합평가']['신뢰도'] for r in 분석_결과들]) / len(분석_결과들)

        print(f"\n📊 평균 지표:")
        print(f"   평균 점수: {평균_점수:.1f}점")
        print(f"   평균 신뢰도: {평균_신뢰도:.1%}")

        # 수급 상태 요약
        외국인_매수_종목 = len([r for r in 분석_결과들 if r['수급분석']['외국인_분석']['외국인_상태'] == '매수세'])
        개인_매도_종목 = len([r for r in 분석_결과들 if r['수급분석']['개인_분석']['개인_상태'] == '매도세'])

        print(f"\n💰 수급 현황:")
        print(f"   외국인 매수세: {외국인_매수_종목}개 ({외국인_매수_종목 / len(분석_결과들) * 100:.1f}%)")
        print(f"   개인 매도세: {개인_매도_종목}개 ({개인_매도_종목 / len(분석_결과들) * 100:.1f}%)")

    def _save_analysis_results(self, analysis_date: str, 분석_결과들: List[Dict]):
        """분석 결과 DB 저장"""

        try:
            # 차트+수급 분석 테이블 생성
            table_name = f"chart_supply_analysis_{analysis_date.replace('-', '')}"

            connection = self.db.get_connection(self.db.crawling_db)
            cursor = connection.cursor()

            # 기존 테이블 삭제 후 재생성
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

            create_sql = f"""
            CREATE TABLE {table_name} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                stock_code VARCHAR(10) NOT NULL,
                stock_name VARCHAR(100) NOT NULL,
                current_price INT DEFAULT 0,
                new_high_score INT DEFAULT 0,
                new_high_status JSON,
                supply_score INT DEFAULT 0,
                foreign_status VARCHAR(20),
                retail_status VARCHAR(20),
                risk_level VARCHAR(20),
                final_score INT DEFAULT 0,
                investment_opinion VARCHAR(20),
                confidence_level DECIMAL(3,2),
                smart_comment TEXT,
                key_strengths JSON,
                risk_factors JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_final_score (final_score DESC),
                INDEX idx_investment_opinion (investment_opinion)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """

            cursor.execute(create_sql)

            # 데이터 삽입
            insert_sql = f"""
            INSERT INTO {table_name} 
            (stock_code, stock_name, current_price, new_high_score, new_high_status,
             supply_score, foreign_status, retail_status, risk_level,
             final_score, investment_opinion, confidence_level, smart_comment,
             key_strengths, risk_factors)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            saved_count = 0
            for result in 분석_결과들:
                try:
                    cursor.execute(insert_sql, (
                        result['종목정보']['종목코드'],
                        result['종목정보']['종목명'],
                        result['차트분석']['신고가_세부']['현재가'],
                        result['차트분석']['신고가_점수'],
                        json.dumps(result['차트분석']['신고가_상태'], ensure_ascii=False),
                        result['수급분석']['수급_점수'],
                        result['수급분석']['외국인_분석']['외국인_상태'],
                        result['수급분석']['개인_분석']['개인_상태'],
                        result['수급분석']['위험도_평가']['위험도'],
                        result['종합평가']['최종점수'],
                        result['종합평가']['투자의견'],
                        result['종합평가']['신뢰도'],
                        result['종합평가']['스마트_코멘트'],
                        json.dumps(result['종합평가']['핵심_강점'], ensure_ascii=False),
                        json.dumps(result['종합평가']['주의사항'], ensure_ascii=False)
                    ))
                    saved_count += 1
                except Exception as e:
                    print(f"   ❌ {result['종목정보']['종목명']} 저장 실패: {e}")

            cursor.close()
            connection.close()

            print(f"✅ DB 저장 완료: {saved_count}/{len(분석_결과들)}개 종목")
            print(f"📊 테이블명: {table_name}")
            print(f"🔍 저장된 데이터 확인:")
            print(f"   SELECT stock_name, final_score, investment_opinion, smart_comment")
            print(f"   FROM {table_name} ORDER BY final_score DESC;")

        except Exception as e:
            print(f"❌ DB 저장 실패: {e}")


def main():
    """메인 실행 함수"""

    print("🚀 실전 차트+수급 종합 분석 테스트")
    print("=" * 80)
    print("📋 분석 프로세스:")
    print("   1️⃣ 52주 신고가 종목 필터링")
    print("   2️⃣ 신고가 점수 (5일/20일/60일)")
    print("   3️⃣ 실전 수급 분석 (외국인 5일 패턴)")
    print("   4️⃣ 개인 역지표 분석")
    print("   5️⃣ 종합 점수 산출")
    print("=" * 80)

    analyzer = ChartSupplyAnalyzer()

    try:
        # 분석 날짜 입력
        analysis_date = input("분석 날짜를 입력하세요 (YYYY-MM-DD, 기본값: 2025-08-12): ").strip()
        if not analysis_date:
            analysis_date = '2025-08-12'

        # 분석 실행
        success = analyzer.run_comprehensive_analysis(analysis_date)

        if success:
            print(f"\n{'=' * 80}")
            print("✅ 차트+수급 종합 분석 완료!")
            print("💡 저장된 분석 결과를 확인하려면:")
            print(
                f"   SELECT * FROM crawling_db.chart_supply_analysis_{analysis_date.replace('-', '')} ORDER BY final_score DESC;")
            print(f"{'=' * 80}")
        else:
            print(f"\n{'=' * 80}")
            print("❌ 분석 실패 또는 조건 미충족")
            print(f"{'=' * 80}")

    except KeyboardInterrupt:
        print(f"\n{'=' * 80}")
        print("⏹️ 사용자에 의해 중단되었습니다.")
        print(f"{'=' * 80}")
    except Exception as e:
        print(f"\n{'=' * 80}")
        print(f"❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        print(f"{'=' * 80}")


if __name__ == "__main__":
    main()