#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
캔들 중첩도 기반 지지선/저항선 탐지
- 캔들 몸통(실체)이 많이 겹치는 가격대 찾기
- 월봉: 모든 데이터, 주봉: 3년, 일봉: 1년
- 가장 많은 캔들이 지나가는 수평선 찾기
"""

import random
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from collections import defaultdict


class CandleOverlapDetector:
    """캔들 중첩도 기반 지지선/저항선 탐지"""

    def __init__(self):
        self.price_step_ratio = 0.005  # 0.5% 단위로 가격대 나누기

    def find_most_overlapped_lines(self, price_data: List[Dict], timeframe: str) -> Dict:
        """캔들이 가장 많이 중첩되는 선 찾기"""

        # 기간별 데이터 필터링
        filtered_data = self._filter_data_by_timeframe(price_data, timeframe)

        if not filtered_data or len(filtered_data) < 10:
            return self._get_empty_result()

        current_price = filtered_data[0]['close']

        # 1단계: 가격대별 캔들 중첩 횟수 계산
        overlap_counts = self._calculate_candle_overlaps(filtered_data)

        # 2단계: 가장 중첩도가 높은 가격대들 찾기
        resistance_line = self._find_strongest_overlap_line(overlap_counts, current_price, 'resistance')
        support_line = self._find_strongest_overlap_line(overlap_counts, current_price, 'support')

        return {
            'timeframe': timeframe,
            'data_period': self._get_data_period_info(timeframe, len(filtered_data)),
            'current_price': current_price,
            'strongest_resistance': resistance_line,
            'strongest_support': support_line,
            'analysis': self._analyze_position(current_price, support_line, resistance_line)
        }

    def _filter_data_by_timeframe(self, price_data: List[Dict], timeframe: str) -> List[Dict]:
        """기간별 데이터 필터링"""

        if timeframe == 'monthly':
            # 월봉: 모든 데이터 사용
            return price_data
        elif timeframe == 'weekly':
            # 주봉: 3년치 데이터 (156주)
            return price_data[:156] if len(price_data) > 156 else price_data
        elif timeframe == 'daily':
            # 일봉: 1년치 데이터 (252일)
            return price_data[:252] if len(price_data) > 252 else price_data
        else:
            return price_data

    def _get_data_period_info(self, timeframe: str, data_count: int) -> Dict:
        """데이터 기간 정보"""

        if timeframe == 'monthly':
            years = data_count / 12
            return {'period': f"{years:.1f}년치 월봉", 'count': data_count}
        elif timeframe == 'weekly':
            years = data_count / 52
            return {'period': f"{years:.1f}년치 주봉", 'count': data_count}
        elif timeframe == 'daily':
            years = data_count / 252
            return {'period': f"{years:.1f}년치 일봉", 'count': data_count}
        else:
            return {'period': f"{data_count}개 데이터", 'count': data_count}

    def _calculate_candle_overlaps(self, candle_data: List[Dict]) -> Dict:
        """가격대별 캔들 중첩 횟수 계산"""

        # 전체 가격 범위 파악
        all_prices = []
        for candle in candle_data:
            all_prices.extend([candle['open'], candle['close'], candle['high'], candle['low']])

        min_price = min(all_prices)
        max_price = max(all_prices)

        # 가격대를 작은 단위로 나누기
        price_step = min_price * self.price_step_ratio
        price_levels = {}

        # 각 가격대에서 캔들 중첩 횟수 계산
        current_level = min_price
        while current_level <= max_price:
            overlap_count = 0
            overlapping_candles = []

            for i, candle in enumerate(candle_data):
                # 캔들 몸통(실체) 범위
                candle_top = max(candle['open'], candle['close'])
                candle_bottom = min(candle['open'], candle['close'])

                # 현재 가격 레벨이 캔들 몸통을 지나가는지 확인
                if candle_bottom <= current_level <= candle_top:
                    overlap_count += 1
                    overlapping_candles.append({
                        'date': candle['date'],
                        'candle_index': i,
                        'body_size': abs(candle['close'] - candle['open'])
                    })

            # 최소 3개 이상 캔들이 중첩된 경우만 유효한 라인으로 간주
            if overlap_count >= 3:
                price_levels[current_level] = {
                    'price': current_level,
                    'overlap_count': overlap_count,
                    'overlapping_candles': overlapping_candles,
                    'strength': self._calculate_overlap_strength(overlap_count, overlapping_candles)
                }

            current_level += price_step

        return price_levels

    def _calculate_overlap_strength(self, overlap_count: int, overlapping_candles: List[Dict]) -> float:
        """중첩 강도 계산"""

        # 기본 점수: 중첩 횟수
        base_score = overlap_count

        # 보너스: 캔들 몸통 크기 (큰 몸통일수록 의미있는 중첩)
        body_size_bonus = 0
        if overlapping_candles:
            avg_body_size = sum(c['body_size'] for c in overlapping_candles) / len(overlapping_candles)
            body_size_bonus = min(avg_body_size / 1000, 5)  # 최대 5점 보너스

        # 보너스: 시간적 분산 (여러 시점에 걸쳐 중첩되면 더 강력)
        time_distribution_bonus = min(len(set(c['date'][:7] for c in overlapping_candles)), 10)  # 월별 분산, 최대 10점

        total_strength = base_score + body_size_bonus + time_distribution_bonus
        return round(total_strength, 2)

    def _find_strongest_overlap_line(self, overlap_counts: Dict, current_price: float, line_type: str) -> Dict:
        """가장 강력한 중첩 라인 찾기"""

        if not overlap_counts:
            return None

        candidates = []

        for price_level, overlap_info in overlap_counts.items():
            if line_type == 'resistance':
                # 저항선: 현재가보다 위에 있어야 함
                if price_level > current_price * 1.01:  # 최소 1% 이상 위
                    candidates.append(overlap_info)
            else:  # support
                # 지지선: 현재가보다 아래에 있어야 함
                if price_level < current_price * 0.99:  # 최소 1% 이상 아래
                    candidates.append(overlap_info)

        if not candidates:
            return None

        # 강도(strength)가 가장 높은 라인 선택
        strongest = max(candidates, key=lambda x: x['strength'])

        # 추가 정보 계산
        distance_percent = abs(strongest['price'] - current_price) / current_price * 100

        return {
            'price': strongest['price'],
            'overlap_count': strongest['overlap_count'],
            'strength': strongest['strength'],
            'distance_percent': distance_percent,
            'type': line_type,
            'overlapping_candles': strongest['overlapping_candles'],
            'strength_grade': self._get_strength_grade(strongest['strength'])
        }

    def _get_strength_grade(self, strength: float) -> str:
        """강도 등급"""
        if strength >= 20:
            return "S급"
        elif strength >= 15:
            return "A급"
        elif strength >= 10:
            return "B급"
        elif strength >= 7:
            return "C급"
        else:
            return "D급"

    def _analyze_position(self, current_price: float, support: Dict, resistance: Dict) -> Dict:
        """현재 위치 분석"""

        analysis = {
            'position': '미확정',
            'box_position_ratio': 0.5,
            'nearest_line': None,
            'strategy': '관망',
            'breakout_probability': 0.5
        }

        if resistance and support:
            # 박스권 내부
            box_height = resistance['price'] - support['price']
            position_in_box = (current_price - support['price']) / box_height

            analysis['box_position_ratio'] = position_in_box

            if position_in_box > 0.8:
                analysis['position'] = '저항선근접'
                analysis['nearest_line'] = resistance
                analysis['strategy'] = '돌파 확인 후 매수'
                analysis['breakout_probability'] = 0.75
            elif position_in_box < 0.2:
                analysis['position'] = '지지선근접'
                analysis['nearest_line'] = support
                analysis['strategy'] = '반발매수 타이밍'
                analysis['breakout_probability'] = 0.25
            else:
                analysis['position'] = '박스권중간'
                analysis['strategy'] = '방향성 대기'
                analysis['breakout_probability'] = 0.5

        elif resistance:
            analysis['position'] = '저항선하단'
            analysis['nearest_line'] = resistance
            analysis['strategy'] = '돌파시 추격매수'

        elif support:
            analysis['position'] = '지지선상단'
            analysis['nearest_line'] = support
            analysis['strategy'] = '지지선 사수 필수'

        return analysis

    def _get_empty_result(self):
        """빈 결과"""
        return {
            'timeframe': 'unknown',
            'data_period': {'period': '데이터없음', 'count': 0},
            'current_price': 0,
            'strongest_resistance': None,
            'strongest_support': None,
            'analysis': {'position': '데이터부족', 'strategy': '분석불가'}
        }


def generate_overlapping_candle_data(timeframe: str, current_price: int = 75000) -> List[Dict]:
    """캔들 중첩이 잘 보이는 테스트 데이터 생성"""

    # 기간별 데이터 개수
    base_periods = {
        'monthly': 120,  # 10년치 월봉 (모든 데이터 시뮬레이션)
        'weekly': 156,  # 3년치 주봉
        'daily': 252  # 1년치 일봉
    }

    days = base_periods.get(timeframe, 252)
    data = []

    # 주요 중첩 가격대 설정 (여러 개)
    overlap_zones = [
        current_price * 1.20,  # +20% 강력한 저항
        current_price * 1.10,  # +10% 보조 저항
        current_price * 0.90,  # -10% 보조 지지
        current_price * 0.80  # -20% 강력한 지지
    ]

    price = current_price

    for i in range(days):
        date = datetime.now() - timedelta(days=i)

        # 중첩 구간에서 캔들 몸통이 머무를 확률 증가
        in_overlap_zone = False
        for zone_price in overlap_zones:
            if abs(price - zone_price) / zone_price < 0.05:  # 5% 범위
                in_overlap_zone = True
                break

        if in_overlap_zone:
            # 중첩 구간에서는 작은 몸통, 적은 변동
            change_rate = random.uniform(-0.01, 0.01)  # ±1%
            body_size_ratio = random.uniform(0.005, 0.015)  # 작은 몸통
        else:
            # 일반 구간에서는 큰 변동
            change_rate = random.uniform(-0.03, 0.03)  # ±3%
            body_size_ratio = random.uniform(0.01, 0.03)  # 큰 몸통

        # 새로운 가격 계산
        new_price = price * (1 + change_rate)

        # 중첩 구간으로 유도
        nearest_zone = min(overlap_zones, key=lambda x: abs(new_price - x))
        if abs(new_price - nearest_zone) / nearest_zone < 0.1:  # 10% 범위 내
            # 50% 확률로 중첩 구간으로 끌어당기기
            if random.random() < 0.5:
                new_price = new_price * 0.7 + nearest_zone * 0.3

        # OHLC 생성
        open_price = price
        close_price = new_price

        # 몸통 크기 조정
        body_size = abs(close_price - open_price)
        target_body_size = close_price * body_size_ratio

        if body_size < target_body_size:
            # 몸통 키우기
            if close_price > open_price:
                close_price = open_price + target_body_size
            else:
                close_price = open_price - target_body_size

        # 고가/저가 설정
        high_price = max(open_price, close_price) * random.uniform(1.005, 1.02)
        low_price = min(open_price, close_price) * random.uniform(0.98, 0.995)

        data.append({
            'date': date.strftime('%Y-%m-%d'),
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': random.randint(1000000, 10000000)
        })

        price = close_price

    return data


def print_overlap_result(result: Dict, stock_name: str = "삼성전자"):
    """캔들 중첩 분석 결과 출력"""

    print(f"\n{'=' * 80}")
    print(f"📊 {stock_name} - {result['timeframe'].upper()} 캔들 중첩 분석")
    print(f"{'=' * 80}")

    period_info = result['data_period']
    print(f"📅 분석 기간: {period_info['period']} ({period_info['count']}개 캔들)")

    current = result['current_price']
    print(f"💰 현재가: {current:,}원")

    analysis = result['analysis']
    print(f"📍 현재 위치: {analysis['position']}")

    if 'box_position_ratio' in analysis:
        ratio = analysis['box_position_ratio'] * 100
        print(f"📊 박스권 내 위치: {ratio:.0f}% 지점")

    print(f"🎯 돌파 가능성: {analysis['breakout_probability']:.0%}")
    print(f"💡 투자 전략: {analysis['strategy']}")

    print(f"\n{'─' * 60}")
    print("🔺 가장 강력한 저항선 (캔들 중첩도 기준)")
    print(f"{'─' * 60}")

    resistance = result['strongest_resistance']
    if resistance:
        print(f"💎 저항선: {resistance['price']:,.0f}원 (+{resistance['distance_percent']:.1f}%)")
        print(f"🔄 중첩 캔들 수: {resistance['overlap_count']}개")
        print(f"💪 중첩 강도: {resistance['strength']} ({resistance['strength_grade']})")

        # 중첩된 캔들들의 날짜 정보
        dates = [c['date'] for c in resistance['overlapping_candles']]
        print(f"📅 중첩 기간: {min(dates)} ~ {max(dates)}")

    else:
        print("❌ 명확한 저항선 없음")

    print(f"\n{'─' * 60}")
    print("🔻 가장 강력한 지지선 (캔들 중첩도 기준)")
    print(f"{'─' * 60}")

    support = result['strongest_support']
    if support:
        print(f"💎 지지선: {support['price']:,.0f}원 (-{support['distance_percent']:.1f}%)")
        print(f"🔄 중첩 캔들 수: {support['overlap_count']}개")
        print(f"💪 중첩 강도: {support['strength']} ({support['strength_grade']})")

        # 중첩된 캔들들의 날짜 정보
        dates = [c['date'] for c in support['overlapping_candles']]
        print(f"📅 중첩 기간: {min(dates)} ~ {max(dates)}")

    else:
        print("❌ 명확한 지지선 없음")

    # 가장 가까운 라인 정보
    if analysis['nearest_line']:
        nearest = analysis['nearest_line']
        print(f"\n🎯 가장 가까운 핵심 라인:")
        print(f"   {nearest['type']}: {nearest['price']:,.0f}원")
        print(f"   중첩강도: {nearest['strength']} ({nearest['strength_grade']})")


def main():
    """메인 테스트 함수"""

    print("🚀 캔들 중첩도 기반 지지선/저항선 탐지!")
    print("🎯 목표: 캔들 몸통이 가장 많이 겹치는 수평선 찾기")
    print("📊 데이터 기간: 월봉(전체), 주봉(3년), 일봉(1년)")

    detector = CandleOverlapDetector()

    test_stocks = [
        ("삼성전자", 75000),
        ("SK하이닉스", 142000),
        ("NAVER", 178000)
    ]

    timeframes = ["daily", "weekly", "monthly"]

    for stock_name, current_price in test_stocks:
        print(f"\n\n🏢 {stock_name} ({current_price:,}원)")
        print("=" * 100)

        for timeframe in timeframes:
            # 캔들 중첩이 잘 보이는 데이터 생성
            candle_data = generate_overlapping_candle_data(timeframe, current_price)

            # 캔들 중첩 기반 지지선/저항선 탐지
            result = detector.find_most_overlapped_lines(candle_data, timeframe)

            # 결과 출력
            print_overlap_result(result, stock_name)

    print(f"\n\n{'=' * 80}")
    print("✅ 캔들 중첩 분석 완료!")
    print("💡 중첩 강도가 높을수록 강력한 지지/저항선입니다.")
    print("🎯 여러 시점에 걸쳐 캔들 몸통이 겹치는 가격대를 찾았습니다.")
    print("📊 실제 차트에서는 이 라인들이 명확하게 보일 것입니다.")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()