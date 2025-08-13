#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
수급 분석 차트 & AI 분석 차트 테스트 코드
콘솔에서 바로 실행하여 결과 확인 가능
"""

import random
import json
from datetime import datetime, timedelta
from typing import List, Dict
import numpy as np


class SupplyDemandChartAnalyzer:
    """수급 분석 차트 클래스"""

    def __init__(self):
        self.analysis_period = 30  # 30일 분석

    def analyze_supply_demand_pattern(self, supply_data: List[Dict]) -> Dict:
        """수급 패턴 분석"""

        if not supply_data:
            return self._get_empty_supply_result()

        # 최근 30일 데이터만 사용
        recent_data = supply_data[:self.analysis_period]

        # 1단계: 투자주체별 순매수 분석
        foreign_analysis = self._analyze_foreign_investment(recent_data)
        institution_analysis = self._analyze_institution_investment(recent_data)
        retail_analysis = self._analyze_retail_investment(recent_data)

        # 2단계: 수급 강도 및 지속성 분석
        supply_intensity = self._calculate_supply_intensity(recent_data)
        supply_sustainability = self._calculate_supply_sustainability(recent_data)

        # 3단계: 수급 단계 진단
        supply_phase = self._diagnose_supply_phase(
            foreign_analysis, institution_analysis, retail_analysis
        )

        # 4단계: 차트 데이터 생성
        chart_data = self._generate_supply_chart_data(recent_data)

        return {
            'foreign_analysis': foreign_analysis,
            'institution_analysis': institution_analysis,
            'retail_analysis': retail_analysis,
            'supply_intensity': supply_intensity,
            'supply_sustainability': supply_sustainability,
            'supply_phase': supply_phase,
            'chart_data': chart_data,
            'summary': self._generate_supply_summary(supply_phase, foreign_analysis)
        }

    def _analyze_foreign_investment(self, data: List[Dict]) -> Dict:
        """외국인 투자 패턴 분석"""

        net_purchases = []
        consecutive_days = 0
        total_net = 0

        for day in data:
            net = day['foreign_buy'] - day['foreign_sell']
            net_purchases.append(net)
            total_net += net

            if net > 0:
                consecutive_days += 1
            else:
                break

        avg_daily_net = total_net / len(data)
        volatility = np.std(net_purchases) if len(net_purchases) > 1 else 0

        # 외국인 상태 판단
        if consecutive_days >= 5:
            status = "장기매수세"
            risk_level = "차익실현주의"
        elif consecutive_days >= 3:
            status = "단기매수세"
            risk_level = "보통"
        elif avg_daily_net > 0:
            status = "순매수우위"
            risk_level = "낮음"
        else:
            status = "순매도우위"
            risk_level = "낮음"

        return {
            'status': status,
            'consecutive_buying_days': consecutive_days,
            'total_net_30days': total_net,
            'avg_daily_net': avg_daily_net,
            'volatility': volatility,
            'risk_level': risk_level,
            'trend': "상승세" if avg_daily_net > 0 else "하락세"
        }

    def _analyze_institution_investment(self, data: List[Dict]) -> Dict:
        """기관 투자 패턴 분석"""

        pension_net = sum(day['pension_buy'] - day['pension_sell'] for day in data)
        fund_net = sum(day['fund_buy'] - day['fund_sell'] for day in data)

        # 기관별 활동 강도
        pension_activity = "적극적" if abs(pension_net) > 1000000 else "소극적"
        fund_activity = "적극적" if abs(fund_net) > 2000000 else "소극적"

        return {
            'pension_net_30days': pension_net,
            'fund_net_30days': fund_net,
            'pension_activity': pension_activity,
            'fund_activity': fund_activity,
            'dominant_institution': "연기금" if abs(pension_net) > abs(fund_net) else "펀드",
            'overall_trend': "매수세" if (pension_net + fund_net) > 0 else "매도세"
        }

    def _analyze_retail_investment(self, data: List[Dict]) -> Dict:
        """개인 투자 패턴 분석 (역지표)"""

        retail_net_total = sum(day['retail_buy'] - day['retail_sell'] for day in data)

        # 개인 대량 매수 구간 탐지
        large_buying_days = 0
        for day in data[:10]:  # 최근 10일
            net = day['retail_buy'] - day['retail_sell']
            if net > 3000000:  # 30억 이상 순매수
                large_buying_days += 1

        # 역지표 신호
        if large_buying_days >= 3:
            reverse_signal = "강한위험신호"
            risk_description = "개인 대량매수 - 조정 임박"
        elif retail_net_total > 10000000:  # 100억 이상
            reverse_signal = "위험신호"
            risk_description = "개인 순매수 증가 - 주의"
        elif retail_net_total < -5000000:  # 50억 이상 순매도
            reverse_signal = "긍정신호"
            risk_description = "개인 매도세 - 건전한 수급"
        else:
            reverse_signal = "중립"
            risk_description = "개인 매매 균형"

        return {
            'net_30days': retail_net_total,
            'large_buying_days': large_buying_days,
            'reverse_signal': reverse_signal,
            'risk_description': risk_description,
            'market_sentiment': "과열" if retail_net_total > 5000000 else "정상"
        }

    def _calculate_supply_intensity(self, data: List[Dict]) -> Dict:
        """수급 강도 계산"""

        daily_volumes = [day['total_volume'] for day in data]
        avg_volume = sum(daily_volumes) / len(daily_volumes)
        recent_volume = sum(daily_volumes[:5]) / 5  # 최근 5일 평균

        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1

        if volume_ratio >= 1.5:
            intensity = "매우높음"
        elif volume_ratio >= 1.2:
            intensity = "높음"
        elif volume_ratio >= 0.8:
            intensity = "보통"
        else:
            intensity = "낮음"

        return {
            'intensity_level': intensity,
            'volume_ratio': volume_ratio,
            'avg_volume_30days': avg_volume,
            'recent_volume_5days': recent_volume
        }

    def _calculate_supply_sustainability(self, data: List[Dict]) -> Dict:
        """수급 지속성 계산"""

        # 주요 투자주체들의 일관성 체크
        foreign_consistency = self._calculate_consistency([
            day['foreign_buy'] - day['foreign_sell'] for day in data
        ])

        institution_consistency = self._calculate_consistency([
            (day['pension_buy'] - day['pension_sell']) + (day['fund_buy'] - day['fund_sell'])
            for day in data
        ])

        overall_sustainability = (foreign_consistency + institution_consistency) / 2

        if overall_sustainability >= 0.7:
            sustainability = "매우안정"
        elif overall_sustainability >= 0.5:
            sustainability = "안정"
        elif overall_sustainability >= 0.3:
            sustainability = "불안정"
        else:
            sustainability = "매우불안정"

        return {
            'sustainability_level': sustainability,
            'foreign_consistency': foreign_consistency,
            'institution_consistency': institution_consistency,
            'overall_score': overall_sustainability
        }

    def _calculate_consistency(self, values: List[float]) -> float:
        """일관성 점수 계산 (같은 방향 유지 비율)"""

        if not values or len(values) < 2:
            return 0

        positive_count = len([v for v in values if v > 0])
        negative_count = len([v for v in values if v < 0])

        return max(positive_count, negative_count) / len(values)

    def _diagnose_supply_phase(self, foreign_analysis, institution_analysis, retail_analysis) -> Dict:
        """수급 단계 진단"""

        # 수급 단계 매트릭스
        if (foreign_analysis['status'] in ['장기매수세', '단기매수세'] and
                institution_analysis['overall_trend'] == '매수세' and
                retail_analysis['reverse_signal'] in ['긍정신호', '중립']):

            phase = "1단계: 스마트머니 유입"
            description = "외국인+기관 동반 매수, 개인 참여 제한적"
            recommendation = "적극 매수 타이밍"

        elif (foreign_analysis['status'] in ['순매수우위'] and
              retail_analysis['reverse_signal'] == '중립'):

            phase = "2단계: 상승 진행"
            description = "외국인 주도 상승, 기관 선별적 참여"
            recommendation = "추가 매수 고려"

        elif retail_analysis['reverse_signal'] == '강한위험신호':

            phase = "4단계: 고점 경고"
            description = "개인 대량매수, 외국인 차익실현 가능성"
            recommendation = "즉시 매도 검토"

        else:
            phase = "중립 단계"
            description = "명확한 수급 방향성 없음"
            recommendation = "관망 또는 소량 매수"

        return {
            'phase': phase,
            'description': description,
            'recommendation': recommendation,
            'confidence': self._calculate_phase_confidence(foreign_analysis, institution_analysis, retail_analysis)
        }

    def _calculate_phase_confidence(self, foreign_analysis, institution_analysis, retail_analysis) -> float:
        """수급 단계 신뢰도 계산"""

        confidence = 0.5  # 기본값

        # 외국인 신뢰도
        if foreign_analysis['consecutive_buying_days'] >= 3:
            confidence += 0.2

        # 기관 신뢰도
        if institution_analysis['overall_trend'] == '매수세':
            confidence += 0.15

        # 개인 역지표 신뢰도
        if retail_analysis['reverse_signal'] in ['긍정신호', '강한위험신호']:
            confidence += 0.15

        return min(0.95, confidence)

    def _generate_supply_chart_data(self, data: List[Dict]) -> Dict:
        """차트용 데이터 생성"""

        chart_data = {
            'dates': [],
            'foreign_net': [],
            'institution_net': [],
            'retail_net': [],
            'volume': [],
            'cumulative_foreign': [],
            'cumulative_institution': []
        }

        cumulative_foreign = 0
        cumulative_institution = 0

        for day in reversed(data):  # 시간순 정렬
            chart_data['dates'].append(day['date'])

            foreign_net = day['foreign_buy'] - day['foreign_sell']
            institution_net = (day['pension_buy'] - day['pension_sell']) + (day['fund_buy'] - day['fund_sell'])
            retail_net = day['retail_buy'] - day['retail_sell']

            chart_data['foreign_net'].append(foreign_net)
            chart_data['institution_net'].append(institution_net)
            chart_data['retail_net'].append(retail_net)
            chart_data['volume'].append(day['total_volume'])

            cumulative_foreign += foreign_net
            cumulative_institution += institution_net

            chart_data['cumulative_foreign'].append(cumulative_foreign)
            chart_data['cumulative_institution'].append(cumulative_institution)

        return chart_data

    def _generate_supply_summary(self, supply_phase, foreign_analysis) -> str:
        """수급 요약 메시지 생성"""

        phase_name = supply_phase['phase'].split(':')[0]
        foreign_status = foreign_analysis['status']

        return f"{phase_name} | {foreign_status} | {supply_phase['recommendation']}"

    def _get_empty_supply_result(self):
        """빈 수급 결과"""
        return {
            'foreign_analysis': {'status': '데이터없음'},
            'institution_analysis': {'overall_trend': '데이터없음'},
            'retail_analysis': {'reverse_signal': '데이터없음'},
            'supply_intensity': {'intensity_level': '알수없음'},
            'supply_sustainability': {'sustainability_level': '알수없음'},
            'supply_phase': {'phase': '분석불가', 'recommendation': '데이터 필요'},
            'chart_data': {},
            'summary': '수급 데이터 부족'
        }


class AIAnalysisChartGenerator:
    """AI 분석 차트 생성 클래스"""

    def __init__(self):
        self.score_weights = {
            'keyword_score': 0.35,  # 키워드 점수 35%
            'complex_score': 0.25,  # 복합 분석 25%
            'market_score': 0.20,  # 시장 환경 20%
            'sustainability': 0.10,  # 지속성 10%
            'volume_bonus': 0.10  # 거래량 보너스 10%
        }

    def generate_ai_analysis_chart(self, ai_result: Dict) -> Dict:
        """AI 분석 결과를 차트용 데이터로 변환"""

        # 1단계: AI 점수 구성 분석
        score_breakdown = self._analyze_score_breakdown(ai_result)

        # 2단계: 키워드 강도 분석
        keyword_analysis = self._analyze_keyword_strength(ai_result)

        # 3단계: 뉴스 감정 분석
        sentiment_analysis = self._analyze_news_sentiment(ai_result)

        # 4단계: 투자 신뢰도 계산
        confidence_analysis = self._calculate_investment_confidence(ai_result)

        # 5단계: 차트 데이터 구성
        chart_data = self._generate_ai_chart_data(
            score_breakdown, keyword_analysis, sentiment_analysis, confidence_analysis
        )

        return {
            'score_breakdown': score_breakdown,
            'keyword_analysis': keyword_analysis,
            'sentiment_analysis': sentiment_analysis,
            'confidence_analysis': confidence_analysis,
            'chart_data': chart_data,
            'summary': self._generate_ai_summary(ai_result)
        }

    def _analyze_score_breakdown(self, ai_result: Dict) -> Dict:
        """AI 점수 구성 분석"""

        total_score = ai_result.get('ai_score', 0)

        # 점수 구성 역산 (가상)
        keyword_score = min(35, total_score * 0.4)
        complex_score = min(25, total_score * 0.3)
        market_score = min(20, total_score * 0.25)
        sustainability = min(10, total_score * 0.1)
        volume_bonus = min(10, max(0, total_score - 90))

        return {
            'total_score': total_score,
            'keyword_score': keyword_score,
            'complex_score': complex_score,
            'market_score': market_score,
            'sustainability': sustainability,
            'volume_bonus': volume_bonus,
            'grade': self._calculate_grade(total_score),
            'percentile': self._calculate_percentile(total_score)
        }

    def _analyze_keyword_strength(self, ai_result: Dict) -> Dict:
        """키워드 강도 분석"""

        key_factors = ai_result.get('key_factors', [])

        # 키워드별 강도 계산 (가상)
        keyword_strength = {}
        for keyword in key_factors:
            if keyword in ['AI', '반도체', '전기차']:
                strength = random.uniform(0.8, 1.0)
            elif keyword in ['혁신', '성장', '확장']:
                strength = random.uniform(0.6, 0.8)
            else:
                strength = random.uniform(0.4, 0.6)

            keyword_strength[keyword] = strength

        return {
            'keyword_count': len(key_factors),
            'keyword_strength': keyword_strength,
            'dominant_theme': key_factors[0] if key_factors else '없음',
            'diversity_score': len(set(key_factors)) / max(len(key_factors), 1)
        }

    def _analyze_news_sentiment(self, ai_result: Dict) -> Dict:
        """뉴스 감정 분석"""

        news_summary = ai_result.get('news_summary', '')

        # 감정 분석 (단순 키워드 기반)
        positive_words = ['상승', '성장', '확대', '증가', '개선', '호조', '수혜']
        negative_words = ['하락', '감소', '우려', '리스크', '부담', '악화']

        positive_count = sum(1 for word in positive_words if word in news_summary)
        negative_count = sum(1 for word in negative_words if word in news_summary)

        sentiment_score = (positive_count - negative_count) / max(positive_count + negative_count, 1)

        if sentiment_score > 0.3:
            sentiment = "매우긍정"
        elif sentiment_score > 0:
            sentiment = "긍정"
        elif sentiment_score > -0.3:
            sentiment = "중립"
        else:
            sentiment = "부정"

        return {
            'sentiment': sentiment,
            'sentiment_score': sentiment_score,
            'positive_signals': positive_count,
            'negative_signals': negative_count,
            'news_reliability': random.uniform(0.6, 0.9)
        }

    def _calculate_investment_confidence(self, ai_result: Dict) -> Dict:
        """투자 신뢰도 계산"""

        ai_score = ai_result.get('ai_score', 0)
        investment_opinion = ai_result.get('investment_opinion', '')

        # 기본 신뢰도
        base_confidence = ai_score / 100

        # 의견별 가중치
        opinion_weights = {
            '강력매수': 0.9,
            '매수': 0.7,
            '관심': 0.5,
            '관망': 0.3
        }

        opinion_confidence = opinion_weights.get(investment_opinion, 0.5)

        # 최종 신뢰도
        final_confidence = (base_confidence + opinion_confidence) / 2

        return {
            'confidence_score': final_confidence,
            'confidence_level': self._get_confidence_level(final_confidence),
            'risk_factors': self._identify_risk_factors(ai_result),
            'strength_factors': self._identify_strength_factors(ai_result)
        }

    def _get_confidence_level(self, score: float) -> str:
        """신뢰도 레벨"""
        if score >= 0.8:
            return "매우높음"
        elif score >= 0.6:
            return "높음"
        elif score >= 0.4:
            return "보통"
        else:
            return "낮음"

    def _identify_risk_factors(self, ai_result: Dict) -> List[str]:
        """리스크 요인 식별"""

        risk_factors = []

        if ai_result.get('ai_score', 0) < 60:
            risk_factors.append("AI 점수 낮음")

        if '개인' in ai_result.get('issue_category', ''):
            risk_factors.append("개별 이슈 의존")

        if ai_result.get('investment_opinion') == '관망':
            risk_factors.append("투자 매력도 부족")

        return risk_factors

    def _identify_strength_factors(self, ai_result: Dict) -> List[str]:
        """강점 요인 식별"""

        strength_factors = []

        if ai_result.get('ai_score', 0) >= 80:
            strength_factors.append("높은 AI 점수")

        if ai_result.get('issue_type') == 'THEME':
            strength_factors.append("테마 수혜 종목")

        key_factors = ai_result.get('key_factors', [])
        if 'AI' in key_factors or '반도체' in key_factors:
            strength_factors.append("핵심 테마 보유")

        return strength_factors

    def _generate_ai_chart_data(self, score_breakdown, keyword_analysis, sentiment_analysis,
                                confidence_analysis) -> Dict:
        """AI 차트 데이터 생성"""

        return {
            'radar_chart': {
                'labels': ['키워드', '복합분석', '시장환경', '지속성', '거래량'],
                'values': [
                    score_breakdown['keyword_score'],
                    score_breakdown['complex_score'],
                    score_breakdown['market_score'],
                    score_breakdown['sustainability'],
                    score_breakdown['volume_bonus']
                ],
                'max_values': [35, 25, 20, 10, 10]
            },
            'gauge_chart': {
                'total_score': score_breakdown['total_score'],
                'grade': score_breakdown['grade'],
                'percentile': score_breakdown['percentile']
            },
            'keyword_chart': {
                'keywords': list(keyword_analysis['keyword_strength'].keys()),
                'strengths': list(keyword_analysis['keyword_strength'].values())
            },
            'sentiment_chart': {
                'sentiment': sentiment_analysis['sentiment'],
                'score': sentiment_analysis['sentiment_score'],
                'positive': sentiment_analysis['positive_signals'],
                'negative': sentiment_analysis['negative_signals']
            },
            'confidence_chart': {
                'confidence': confidence_analysis['confidence_score'],
                'level': confidence_analysis['confidence_level'],
                'risks': confidence_analysis['risk_factors'],
                'strengths': confidence_analysis['strength_factors']
            }
        }

    def _calculate_grade(self, score: int) -> str:
        """점수를 등급으로 변환"""
        if score >= 90:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B+"
        elif score >= 60:
            return "B"
        elif score >= 50:
            return "C+"
        else:
            return "C"

    def _calculate_percentile(self, score: int) -> int:
        """상위 몇 % 계산"""
        return max(5, min(95, 100 - score))

    def _generate_ai_summary(self, ai_result: Dict) -> str:
        """AI 분석 요약"""

        score = ai_result.get('ai_score', 0)
        opinion = ai_result.get('investment_opinion', '')
        primary_theme = ai_result.get('primary_theme', '')

        return f"{score}점 {self._calculate_grade(score)}등급 | {opinion} | {primary_theme} 테마"


def generate_test_supply_data(days: int = 30) -> List[Dict]:
    """테스트용 수급 데이터 생성"""

    data = []

    for i in range(days):
        date = datetime.now() - timedelta(days=i)

        # 외국인: 간헐적 대량 매수 패턴
        if random.random() < 0.4:
            foreign_buy = random.randint(2000000, 8000000)
            foreign_sell = random.randint(500000, 2000000)
        else:
            foreign_buy = random.randint(500000, 2000000)
            foreign_sell = random.randint(2000000, 5000000)

        # 연기금: 안정적 매수
        pension_buy = random.randint(1000000, 3000000)
        pension_sell = random.randint(500000, 2000000)

        # 펀드: 변동성 있는 매매
        fund_buy = random.randint(1000000, 4000000)
        fund_sell = random.randint(1000000, 4000000)

        # 개인: 높은 변동성
        retail_buy = random.randint(5000000, 15000000)
        retail_sell = random.randint(5000000, 15000000)

        data.append({
            'date': date.strftime('%Y-%m-%d'),
            'foreign_buy': foreign_buy,
            'foreign_sell': foreign_sell,
            'pension_buy': pension_buy,
            'pension_sell': pension_sell,
            'fund_buy': fund_buy,
            'fund_sell': fund_sell,
            'retail_buy': retail_buy,
            'retail_sell': retail_sell,
            'total_volume': random.randint(20000000, 50000000)
        })

    return data


def generate_test_ai_data() -> Dict:
    """테스트용 AI 분석 결과 생성"""

    test_themes = ['AI반도체', '전기차', '바이오', 'K-뷰티', '게임']
    test_keywords = ['AI', '반도체', '성장', '혁신', '글로벌', '확장']

    return {
        'ai_score': random.randint(65, 95),
        'investment_opinion': random.choice(['강력매수', '매수', '관심']),
        'primary_theme': random.choice(test_themes),
        'issue_type': 'THEME',
        'issue_category': '글로벌 트렌드',
        'key_factors': random.sample(test_keywords, 3),
        'news_summary': 'AI 반도체 수요 급증으로 매출 성장 전망이 밝아지고 있음. 글로벌 확장 가속화.',
        'ai_reasoning': '키워드:35, 복합:23, 시장:18, 지속:8, 거래량:7'
    }


def print_supply_analysis(result: Dict, stock_name: str = "삼성전자"):
    """수급 분석 결과 출력"""

    print(f"\n{'=' * 80}")
    print(f"💰 {stock_name} - 수급 분석 결과")
    print(f"{'=' * 80}")

    # 수급 단계
    phase = result['supply_phase']
    print(f"🎯 {phase['phase']}")
    print(f"📝 {phase['description']}")
    print(f"💡 투자전략: {phase['recommendation']}")
    print(f"🎲 신뢰도: {phase['confidence']:.1%}")

    print(f"\n{'─' * 60}")
    print("🌍 외국인 분석")
    print(f"{'─' * 60}")

    foreign = result['foreign_analysis']
    print(f"📊 상태: {foreign['status']}")
    print(f"📅 연속매수일: {foreign['consecutive_buying_days']}일")
    print(f"💸 30일 순매수: {foreign['total_net_30days']:,}주")
    print(f"⚠️ 위험도: {foreign['risk_level']}")

    print(f"\n{'─' * 60}")
    print("🏢 기관 분석")
    print(f"{'─' * 60}")

    institution = result['institution_analysis']
    print(f"📊 전체 동향: {institution['overall_trend']}")
    print(f"🏛️ 연기금: {institution['pension_activity']} ({institution['pension_net_30days']:,}주)")
    print(f"💼 펀드: {institution['fund_activity']} ({institution['fund_net_30days']:,}주)")
    print(f"👑 주도기관: {institution['dominant_institution']}")

    print(f"\n{'─' * 60}")
    print("👥 개인 분석 (역지표)")
    print(f"{'─' * 60}")

    retail = result['retail_analysis']
    print(f"🚨 역지표 신호: {retail['reverse_signal']}")
    print(f"📝 위험 설명: {retail['risk_description']}")
    print(f"📊 30일 순매수: {retail['net_30days']:,}주")
    print(f"🔥 대량매수일: {retail['large_buying_days']}일")
    print(f"🌡️ 시장 온도: {retail['market_sentiment']}")

    print(f"\n{'─' * 60}")
    print("⚡ 수급 강도 & 지속성")
    print(f"{'─' * 60}")

    intensity = result['supply_intensity']
    sustainability = result['supply_sustainability']

    print(f"⚡ 거래 강도: {intensity['intensity_level']} (거래량 비율: {intensity['volume_ratio']:.1f}배)")
    print(f"🔄 지속성: {sustainability['sustainability_level']} (점수: {sustainability['overall_score']:.1%})")

    print(f"\n💬 한줄 요약: {result['summary']}")


def print_ai_analysis(result: Dict, stock_name: str = "삼성전자"):
    """AI 분석 결과 출력"""

    print(f"\n{'=' * 80}")
    print(f"🤖 {stock_name} - AI 분석 결과")
    print(f"{'=' * 80}")

    # AI 점수 구성
    score = result['score_breakdown']
    print(f"🎯 총점: {score['total_score']}점 ({score['grade']}등급)")
    print(f"📊 상위: {score['percentile']}%")

    print(f"\n{'─' * 60}")
    print("📊 점수 구성")
    print(f"{'─' * 60}")

    print(f"🔑 키워드 분석: {score['keyword_score']:.0f}/35점")
    print(f"🧩 복합 분석: {score['complex_score']:.0f}/25점")
    print(f"📈 시장 환경: {score['market_score']:.0f}/20점")
    print(f"⏰ 지속성: {score['sustainability']:.0f}/10점")
    print(f"📊 거래량 보너스: {score['volume_bonus']:.0f}/10점")

    print(f"\n{'─' * 60}")
    print("🏷️ 키워드 분석")
    print(f"{'─' * 60}")

    keyword = result['keyword_analysis']
    print(f"📝 키워드 개수: {keyword['keyword_count']}개")
    print(f"🎯 주요 테마: {keyword['dominant_theme']}")
    print(f"🌈 다양성 점수: {keyword['diversity_score']:.1%}")

    print("💪 키워드 강도:")
    for kw, strength in keyword['keyword_strength'].items():
        bar = "█" * int(strength * 10)
        print(f"   {kw}: {bar} {strength:.1%}")

    print(f"\n{'─' * 60}")
    print("😊 뉴스 감정 분석")
    print(f"{'─' * 60}")

    sentiment = result['sentiment_analysis']
    print(f"💭 감정: {sentiment['sentiment']}")
    print(f"📊 감정 점수: {sentiment['sentiment_score']:.2f}")
    print(f"✅ 긍정 신호: {sentiment['positive_signals']}개")
    print(f"❌ 부정 신호: {sentiment['negative_signals']}개")
    print(f"🎯 뉴스 신뢰도: {sentiment['news_reliability']:.1%}")

    print(f"\n{'─' * 60}")
    print("🎯 투자 신뢰도")
    print(f"{'─' * 60}")

    confidence = result['confidence_analysis']
    print(f"🎲 신뢰도: {confidence['confidence_level']} ({confidence['confidence_score']:.1%})")

    if confidence['strength_factors']:
        print("💪 강점 요인:")
        for factor in confidence['strength_factors']:
            print(f"   ✅ {factor}")

    if confidence['risk_factors']:
        print("⚠️ 리스크 요인:")
        for factor in confidence['risk_factors']:
            print(f"   ❌ {factor}")

    print(f"\n💬 한줄 요약: {result['summary']}")


def main():
    """메인 테스트 함수"""

    print("🚀 수급 & AI 분석 차트 테스트 시작!")
    print("=" * 100)

    test_stocks = [
        "삼성전자",
        "SK하이닉스",
        "NAVER"
    ]

    # 수급 분석기
    supply_analyzer = SupplyDemandChartAnalyzer()

    # AI 분석기
    ai_analyzer = AIAnalysisChartGenerator()

    for stock_name in test_stocks:
        print(f"\n\n🏢 {stock_name} 종합 분석")
        print("=" * 100)

        # 1. 수급 분석
        supply_data = generate_test_supply_data(30)
        supply_result = supply_analyzer.analyze_supply_demand_pattern(supply_data)
        print_supply_analysis(supply_result, stock_name)

        # 2. AI 분석
        ai_data = generate_test_ai_data()
        ai_result = ai_analyzer.generate_ai_analysis_chart(ai_data)
        print_ai_analysis(ai_result, stock_name)

    print(f"\n\n{'=' * 80}")
    print("✅ 수급 & AI 분석 차트 테스트 완료!")
    print("💡 실제 웹 구현시 Chart.js로 시각화됩니다.")
    print("🎯 수급은 4단계 진단, AI는 5개 구성요소로 분석합니다.")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
