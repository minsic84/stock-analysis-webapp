#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
개선된 AI 분석기 - 거래량 고려 + 임계치 50%/1% + 전체 데이터 분석 + 무조건 DB 저장
"""

import sys
import os
import json
import time
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.top_rate_analysis.database import TopRateDatabase


class ImprovedVolumeAIAnalyzer:
    """거래량 고려 + 개선된 임계치 AI 분석기"""

    def __init__(self):
        self.db = TopRateDatabase()

        # 키워드 가중치 정의
        self.keyword_weights = {
            # 최고등급 (50점)
            'supreme': {
                '세계 최초': 50, '세계최초': 50, 'world first': 50,
                'FDA 승인': 50, 'FDA승인': 50, 'FDA approval': 50,
                '대통령': 50, '미국 대통령': 50,
                '100%': 50, '완벽': 50, '절대': 50
            },

            # 고등급 (30-40점)
            'high': {
                '글로벌': 40, 'global': 40, '해외': 35,
                'K푸드': 40, 'K-푸드': 40, 'K팝': 40, 'K-팝': 40,
                'K뷰티': 40, 'K-뷰티': 40, 'K드라마': 40, 'K게임': 40,
                '한류': 40, '불닭볶음면': 40, 'BTS': 40, '블랙핑크': 40,
                'CEO': 30, '회장': 30,
                '애플': 35, '테슬라': 35, '구글': 35, '마이크로소프트': 35,
                '국제기구': 35, '유엔': 35, 'WHO': 35
            },

            # 중등급 (20점)
            'medium': {
                '혁신': 20, '혁신적': 20, 'innovation': 20,
                '급증': 20, '급등': 20, '폭등': 20, '폭증': 20,
                '진출': 20, '확장': 20, '개척': 20,
                '협업': 20, '파트너십': 20, '제휴': 20,
                '독점': 20, '선도': 20, '1위': 20, '주도': 20
            },

            # 기본등급 (10점)
            'basic': {
                '개발': 10, '신규': 10, '관심': 10,
                '계약': 10, '투자': 10, '성장': 10,
                '특허': 10, '기술': 10, '연구': 10
            }
        }

    def run_full_analysis(self, analysis_date='2025-08-12'):
        """전체 데이터 분석 실행 (무조건 DB 저장)"""
        print("🚀 개선된 AI 분석기 - 거래량 고려 + 전체 분석")
        print("현재 시간:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        print("=" * 80)

        try:
            # 1. 데이터 조회
            print(f"📅 {analysis_date} 테마 데이터 조회 중...")
            raw_data = self.db.get_theme_data(analysis_date)

            if not raw_data:
                print(f"❌ {analysis_date} 데이터가 없습니다")
                return False

            # 뉴스가 있는 종목들만 필터링
            stocks_with_news = self._filter_stocks_with_news(raw_data)
            print(f"✅ 전체 분석 대상: {len(stocks_with_news)}개 종목 (뉴스 보유)")

            # 2. 테마별 시장 반응 분석 (거래량 포함)
            print(f"\n{'=' * 60}")
            print("📈 1단계: 테마별 시장 반응 분석 (거래량 포함)")
            print(f"{'=' * 60}")

            theme_market_analysis = self._analyze_theme_market_reaction_with_volume(stocks_with_news)

            # 3. DB 저장 준비 (무조건 저장)
            print(f"\n🗄️ DB 저장 준비 중...")
            try:
                table_name = self.db.setup_ai_analysis_table(analysis_date)
                print(f"✅ 테이블 준비 완료: {table_name}")
            except Exception as e:
                print(f"❌ DB 테이블 준비 실패: {e}")
                return False

            # 4. 전체 종목 개별 분석
            print(f"\n{'=' * 60}")
            print(f"🔍 2단계: 전체 {len(stocks_with_news)}개 종목 개별 분석")
            print(f"{'=' * 60}")

            analysis_results = []

            for i, stock in enumerate(stocks_with_news):
                print(f"\n[{i + 1}/{len(stocks_with_news)}] {stock['stock_name']} ({stock['stock_code']}) 분석")
                print("─" * 70)

                result = self._analyze_single_stock_enhanced(stock, theme_market_analysis)

                if result:
                    # 분석 요약 생성
                    result['analysis_summary'] = self._generate_analysis_summary(result, stock)
                    analysis_results.append(result)
                    self._print_single_analysis_result(result, stock)
                else:
                    print("❌ 분석 실패")

                # 진행률 표시
                if (i + 1) % 10 == 0:
                    print(f"\n⏳ 진행률: {i + 1}/{len(stocks_with_news)} ({((i + 1) / len(stocks_with_news)) * 100:.1f}%)")

            # 5. DB 저장 (무조건 실행)
            print(f"\n{'=' * 60}")
            print("💾 DB 저장 중...")
            print(f"{'=' * 60}")

            try:
                success = self.db.save_ai_analysis(table_name, analysis_results)
                if success:
                    print(f"✅ DB 저장 완료: {len(analysis_results)}개 종목")
                    self._verify_db_save(table_name, analysis_results)
                else:
                    print("❌ DB 저장 실패")
                    return False

            except Exception as e:
                print(f"❌ DB 저장 오류: {e}")
                return False

            # 6. 최종 결과 요약
            print(f"\n{'=' * 80}")
            print("📋 최종 분석 결과 요약")
            print(f"{'=' * 80}")

            self._print_final_summary(analysis_results)
            return True

        except Exception as e:
            print(f"❌ 분석 실행 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _filter_stocks_with_news(self, raw_data):
        """뉴스가 있는 종목들만 필터링"""
        stocks_with_news = []
        for stock in raw_data:
            try:
                news_data = json.loads(stock['news']) if isinstance(stock['news'], str) else stock['news']
                if news_data and len(news_data) > 0:
                    stocks_with_news.append({
                        'stock_code': stock['stock_code'],
                        'stock_name': stock['stock_name'],
                        'themes': json.loads(stock['themes']) if isinstance(stock['themes'], str) else stock['themes'],
                        'price': stock['price'],
                        'change_rate': stock['change_rate'],
                        'volume': stock['volume'],
                        'news': news_data,
                        'theme_stocks': json.loads(stock['theme_stocks']) if isinstance(stock['theme_stocks'], str) else
                        stock['theme_stocks']
                    })
            except:
                continue
        return stocks_with_news

    def _analyze_theme_market_reaction_with_volume(self, stocks_data):
        """테마별 시장 반응 분석 (거래량 포함)"""
        theme_analysis = {}

        for stock in stocks_data:
            try:
                themes = stock['themes']
                theme_stocks = stock['theme_stocks']

                for theme_name in themes:
                    if theme_name not in theme_analysis:
                        theme_analysis[theme_name] = {
                            'stocks': [],
                            'total_stocks': 0,
                            'rising_stocks': 0,
                            'avg_change_rate': 0.0,
                            'strong_rising_stocks': 0,
                            'high_volume_stocks': 0,  # 거래량 기준 추가
                            'volume_weighted_change': 0.0  # 거래량 가중 등락률
                        }

                    # 테마 내 모든 종목 정보 추가
                    if theme_name in theme_stocks:
                        total_volume = 0
                        volume_weighted_sum = 0

                        for theme_stock in theme_stocks[theme_name]:
                            change_rate = theme_stock.get('change_rate', 0)
                            volume = theme_stock.get('volume', 0)

                            theme_analysis[theme_name]['stocks'].append({
                                'code': theme_stock.get('code'),
                                'name': theme_stock.get('name'),
                                'change_rate': change_rate,
                                'volume': volume
                            })

                            # 기존 기준
                            if change_rate > 0:
                                theme_analysis[theme_name]['rising_stocks'] += 1
                            if change_rate >= 5.0:
                                theme_analysis[theme_name]['strong_rising_stocks'] += 1

                            # 거래량 기준 추가 (평균 거래량의 2배 이상)
                            if volume > 0:
                                total_volume += volume
                                volume_weighted_sum += change_rate * volume

                        # 거래량 가중 등락률 계산
                        if total_volume > 0:
                            theme_analysis[theme_name]['volume_weighted_change'] = volume_weighted_sum / total_volume

                        # 고거래량 종목 계산 (상위 30% 거래량)
                        if len(theme_analysis[theme_name]['stocks']) > 0:
                            volumes = [s['volume'] for s in theme_analysis[theme_name]['stocks'] if s['volume'] > 0]
                            if volumes:
                                volumes.sort(reverse=True)
                                high_volume_threshold = volumes[int(len(volumes) * 0.3)] if len(volumes) > 3 else 0
                                theme_analysis[theme_name]['high_volume_stocks'] = len(
                                    [v for v in volumes if v >= high_volume_threshold])

            except Exception as e:
                continue

        # 테마별 통계 계산 및 출력 (개선된 기준)
        for theme_name, data in theme_analysis.items():
            total = len(data['stocks'])
            if total > 0:
                data['total_stocks'] = total
                data['rising_ratio'] = data['rising_stocks'] / total
                data['strong_rising_ratio'] = data['strong_rising_stocks'] / total
                data['avg_change_rate'] = sum(s['change_rate'] for s in data['stocks']) / total

                # 거래량 비율 계산
                data['high_volume_ratio'] = data['high_volume_stocks'] / total if total > 0 else 0

                # 개선된 테마 이슈 판단 기준
                # 1) 50% 이상 상승 + 평균 1% 이상 (기본)
                # 2) 거래량 가중 등락률이 2% 이상 (거래량 고려)
                # 3) 고거래량 종목 중 70% 이상 상승 (거래량 + 상승률)
                basic_criteria = data['rising_ratio'] >= 0.5 and data['avg_change_rate'] >= 1.0
                volume_criteria = data['volume_weighted_change'] >= 2.0
                high_volume_criteria = data['high_volume_ratio'] >= 0.3 and data['rising_ratio'] >= 0.7

                data['is_theme_issue'] = basic_criteria or volume_criteria or high_volume_criteria

                # 상세 출력
                print(f"📊 {theme_name}")
                print(f"   종목수: {total}개 | 상승률: {data['rising_ratio']:.1%} | 평균등락률: {data['avg_change_rate']:+.2f}%")
                print(f"   거래량가중등락률: {data['volume_weighted_change']:+.2f}% | 고거래량비율: {data['high_volume_ratio']:.1%}")

                # 판단 근거 표시
                criteria_met = []
                if basic_criteria:
                    criteria_met.append("기본기준")
                if volume_criteria:
                    criteria_met.append("거래량가중")
                if high_volume_criteria:
                    criteria_met.append("고거래량")

                criteria_text = f" ({', '.join(criteria_met)})" if criteria_met else " (기준미달)"
                print(f"   테마이슈: {'✅ YES' if data['is_theme_issue'] else '❌ NO'}{criteria_text}")

        return theme_analysis

    def _analyze_single_stock_enhanced(self, stock_data, theme_market_analysis):
        """개별 종목 개선된 분석 (거래량 고려)"""
        try:
            news_titles = [news['title'] for news in stock_data['news'] if news.get('title')]
            if not news_titles:
                return None

            # 1. 키워드 점수 계산
            keyword_score, found_keywords = self._calculate_keyword_score(news_titles)

            # 2. 복합 재료 보너스 계산
            combo_bonus, found_categories = self._calculate_combo_bonus(news_titles)

            # 3. 시장 반응 점수 계산 (거래량 고려)
            market_score, issue_type = self._calculate_market_reaction_score_with_volume(
                stock_data, stock_data['themes'], theme_market_analysis
            )

            # 4. 지속성 점수 계산
            sustainability_score = self._calculate_sustainability_score(news_titles)

            # 5. 거래량 보너스 계산 (신규)
            volume_bonus = self._calculate_volume_bonus(stock_data)

            # 6. 최종 점수 및 투자 의견
            total_score = keyword_score + combo_bonus + market_score + sustainability_score + volume_bonus
            final_score = min(100, max(1, total_score))
            investment_opinion = self._determine_investment_opinion(final_score)

            # 7. 이슈 카테고리 결정
            issue_category = self._determine_issue_category(found_keywords, found_categories)

            return {
                'stock_code': stock_data['stock_code'],
                'stock_name': stock_data['stock_name'],
                'primary_theme': stock_data['themes'][0] if stock_data['themes'] else '기타',
                'issue_type': issue_type,
                'issue_category': issue_category,
                'ai_score': final_score,
                'confidence_level': 0.8 if final_score >= 80 else 0.6 if final_score >= 60 else 0.4,
                'investment_opinion': investment_opinion,

                # 상세 점수 정보
                'keyword_score': keyword_score,
                'combo_bonus': combo_bonus,
                'market_score': market_score,
                'sustainability_score': sustainability_score,
                'volume_bonus': volume_bonus,  # 거래량 보너스 추가
                'total_calculated_score': total_score,

                # 상세 분석 정보
                'found_keywords': found_keywords,
                'found_categories': found_categories,
                'key_factors': self._extract_key_factors(found_keywords, found_categories),
                'news_summary': self._summarize_news(news_titles),
                'ai_reasoning': f"키워드:{keyword_score}, 복합:{combo_bonus}, 시장:{market_score}, 지속:{sustainability_score}, 거래량:{volume_bonus}"
            }

        except Exception as e:
            print(f"   ❌ 분석 오류: {e}")
            return None

    def _calculate_market_reaction_score_with_volume(self, stock_data, themes, theme_market_analysis):
        """시장 반응 점수 및 이슈 타입 계산 (거래량 고려)"""
        market_score = 0
        issue_type = "INDIVIDUAL"

        theme_issue_count = 0
        total_themes = len(themes)

        for theme_name in themes:
            if theme_name in theme_market_analysis:
                theme_data = theme_market_analysis[theme_name]

                if theme_data['is_theme_issue']:
                    theme_issue_count += 1

                    # 거래량 가중 등락률에 따른 추가 점수
                    base_score = 20
                    if theme_data['volume_weighted_change'] >= 5.0:
                        base_score += 15  # 거래량 가중 등락률이 높으면 추가 점수
                    elif theme_data['volume_weighted_change'] >= 3.0:
                        base_score += 10
                    elif theme_data['volume_weighted_change'] >= 2.0:
                        base_score += 5

                    market_score += base_score

        # 테마 이슈 판단 (50% 이상에서 테마 이슈)
        if theme_issue_count > 0 and theme_issue_count / total_themes >= 0.5:
            issue_type = "THEME"
            market_score += 15  # 테마 이슈 추가 보너스

        return market_score, issue_type

    def _calculate_volume_bonus(self, stock_data):
        """거래량 보너스 계산 (신규)"""
        volume = stock_data.get('volume', 0)
        change_rate = stock_data.get('change_rate', 0)

        # 거래량이 없으면 보너스 없음
        if volume <= 0:
            return 0

        # 거래량 기준 (임의 기준, 실제로는 과거 평균과 비교해야 함)
        volume_bonus = 0

        # 거래량이 매우 높은 경우 (1억 이상)
        if volume >= 100000000:
            volume_bonus = 15
        # 거래량이 높은 경우 (5천만 이상)
        elif volume >= 50000000:
            volume_bonus = 10
        # 거래량이 보통 이상인 경우 (1천만 이상)
        elif volume >= 10000000:
            volume_bonus = 5

        # 등락률과 거래량이 함께 높으면 추가 보너스
        if change_rate >= 5.0 and volume >= 50000000:
            volume_bonus += 10  # 급등 + 고거래량 시너지
        elif change_rate >= 3.0 and volume >= 30000000:
            volume_bonus += 5

        return min(volume_bonus, 25)  # 최대 25점

    def _calculate_keyword_score(self, news_titles):
        """키워드 점수 계산"""
        score = 0
        found_keywords = []

        all_text = ' '.join(news_titles)

        for grade, keywords in self.keyword_weights.items():
            for keyword, weight in keywords.items():
                if keyword in all_text:
                    score += weight
                    found_keywords.append(f"{keyword}({weight}점)")

        return min(score, 200), found_keywords

    def _calculate_combo_bonus(self, news_titles):
        """복합 재료 보너스 계산"""
        all_text = ' '.join(news_titles)

        categories = {
            'global': ['글로벌', '세계', '해외'],
            'first': ['최초', '첫', '처음'],
            'k_wave': ['K푸드', 'K팝', 'K뷰티', 'K드라마', '한류', '불닭볶음면'],
            'innovation': ['혁신', '개발', '기술'],
            'authority': ['대통령', 'CEO', 'FDA', '국제기구'],
            'perfect': ['100%', '완벽', '절대']
        }

        found_categories = []
        for category, keywords in categories.items():
            if any(keyword in all_text for keyword in keywords):
                found_categories.append(category)

        combo_count = len(found_categories)

        if combo_count >= 3:
            bonus = 50  # 슈퍼 조합
        elif combo_count == 2:
            bonus = 30  # 강력 조합
        else:
            bonus = 0

        return bonus, found_categories

    def _calculate_sustainability_score(self, news_titles):
        """지속성 점수 계산"""
        all_text = ' '.join(news_titles)

        long_term_keywords = [
            '구조적', '시대', '트렌드', '미래', '성장',
            'K열풍', '글로벌', '혁신', '디지털'
        ]

        short_term_keywords = [
            '분기', '실적', '배당', '일회성'
        ]

        long_term_count = sum(1 for keyword in long_term_keywords if keyword in all_text)
        short_term_count = sum(1 for keyword in short_term_keywords if keyword in all_text)

        if long_term_count > short_term_count and long_term_count >= 2:
            score = 20
        elif long_term_count > 0:
            score = 10
        else:
            score = 5

        return score

    def _determine_investment_opinion(self, final_score):
        """투자 의견 결정"""
        if final_score >= 90:
            return "강력매수"
        elif final_score >= 70:
            return "매수"
        elif final_score >= 50:
            return "관심"
        else:
            return "관망"

    def _determine_issue_category(self, found_keywords, found_categories):
        """이슈 카테고리 결정"""
        if any('세계 최초' in kw for kw in found_keywords):
            return "세계최초혁신"
        elif 'k_wave' in found_categories:
            return "K-열풍"
        elif 'global' in found_categories and 'authority' in found_categories:
            return "글로벌대기업관심"
        elif any('FDA' in kw for kw in found_keywords):
            return "FDA승인"
        elif any('100%' in kw for kw in found_keywords):
            return "완벽성능"
        elif 'global' in found_categories:
            return "글로벌진출"
        elif 'innovation' in found_categories:
            return "기술혁신"
        else:
            return "기타"

    def _extract_key_factors(self, found_keywords, found_categories):
        """핵심 요인 추출"""
        factors = []

        # 키워드에서 추출
        for kw in found_keywords[:3]:  # 상위 3개
            factor = kw.split('(')[0]
            factors.append(factor)

        # 카테고리에서 추출
        category_map = {
            'global': '글로벌확장',
            'first': '세계최초',
            'k_wave': 'K-열풍',
            'innovation': '혁신기술',
            'authority': '권위자관심',
            'perfect': '완벽성능'
        }

        for cat in found_categories:
            if cat in category_map and len(factors) < 5:
                factor_name = category_map[cat]
                if factor_name not in factors:
                    factors.append(factor_name)

        return factors[:5]  # 최대 5개

    def _summarize_news(self, news_titles):
        """뉴스 요약"""
        if not news_titles:
            return "관련 뉴스 없음"

        # 주요 키워드 추출하여 요약
        summary = f"{len(news_titles)}개 뉴스에서 "

        if any('세계 최초' in title for title in news_titles):
            summary += "세계 최초 기술 개발, "
        if any('글로벌' in title for title in news_titles):
            summary += "글로벌 진출 소식, "
        if any('100%' in title for title in news_titles):
            summary += "완벽한 성능 입증, "

        summary = summary.rstrip(', ') + " 등이 주요 이슈"
        return summary

    def _generate_analysis_summary(self, result, stock_data):
        """분석 요약 생성 (자연스러운 문장)"""
        try:
            summary_parts = []

            # 1. 주요 강점 설명
            if result['keyword_score'] >= 50:
                top_keywords = [kw for kw in result['found_keywords'] if '50점' in kw or '40점' in kw or '35점' in kw]
                if top_keywords:
                    keyword_text = ', '.join([kw.split('(')[0] for kw in top_keywords[:2]])
                    summary_parts.append(f"{keyword_text}로 높은 혁신성과 성장성을 보유")

            # 2. 복합 재료 설명
            if result['combo_bonus'] >= 50:
                summary_parts.append("여러 핵심 재료가 결합된 슈퍼 조합으로 폭발적 성장 가능성")
            elif result['combo_bonus'] >= 30:
                summary_parts.append("복합 재료 조합으로 시너지 효과 기대")

            # 3. 시장 반응 설명
            if result['issue_type'] == 'THEME':
                summary_parts.append("테마 전체 상승으로 섹터 수혜 확실")
            else:
                summary_parts.append("개별 이슈로 독립적 성장 가능")

            # 4. 거래량 설명 (신규)
            if result['volume_bonus'] >= 15:
                summary_parts.append("폭발적 거래량으로 관심도 급증")
            elif result['volume_bonus'] >= 10:
                summary_parts.append("높은 거래량으로 시장 관심 집중")

            # 5. 지속성 설명
            if result['sustainability_score'] >= 20:
                summary_parts.append("장기 트렌드 반영으로 지속 성장 기대")
            elif result['sustainability_score'] >= 10:
                summary_parts.append("중기적 성장 모멘텀 보유")

            # 6. 최종 결론
            if result['ai_score'] >= 90:
                conclusion = "따라서 강력매수 추천"
            elif result['ai_score'] >= 70:
                conclusion = "따라서 매수 적극 검토 권장"
            elif result['ai_score'] >= 50:
                conclusion = "관심 종목으로 모니터링 필요"
            else:
                conclusion = "현재 시점에서는 관망 권장"

            # 문장 조합
            if summary_parts:
                summary = ". ".join(summary_parts) + f". {conclusion}."
            else:
                summary = f"기본적인 투자 매력도를 보유하며 {conclusion.lower()}."

            return summary

        except Exception as e:
            return f"분석 완료. AI 점수 {result['ai_score']}점으로 {result['investment_opinion']} 의견."

    def _print_single_analysis_result(self, result, stock_data):
        """개별 종목 분석 결과 출력 (거래량 포함)"""
        print(f"💰 가격: {stock_data['price']:,}원 ({stock_data['change_rate']:+.2f}%)")
        print(f"📊 거래량: {stock_data['volume']:,}주")
        print(f"🏷️ 테마: {', '.join(stock_data['themes'])}")
        print(f"📰 뉴스: {len(stock_data['news'])}개")

        for i, news in enumerate(stock_data['news'][:2]):  # 상위 2개만 표시
            print(f"   {i + 1}. {news['title'][:60]}...")

        print(f"\n🎯 분석 결과:")
        print(f"   키워드 점수: {result['keyword_score']}점")
        if result['found_keywords']:
            print(f"   발견 키워드: {', '.join(result['found_keywords'][:3])}")

        print(f"   복합 보너스: {result['combo_bonus']}점")
        if result['found_categories']:
            category_names = {
                'global': '글로벌', 'first': '세계최초', 'k_wave': 'K-열풍',
                'innovation': '혁신', 'authority': '권위자', 'perfect': '완벽성'
            }
            readable_categories = [category_names.get(cat, cat) for cat in result['found_categories']]
            print(f"   발견 카테고리: {', '.join(readable_categories)}")

        print(f"   시장 반응: {result['market_score']}점 ({result['issue_type']})")
        print(f"   지속성: {result['sustainability_score']}점")
        print(f"   거래량 보너스: {result['volume_bonus']}점")  # 거래량 보너스 표시

        print(f"\n📊 최종 결과:")
        print(f"   총 점수: {result['total_calculated_score']}점 → 최종: {result['ai_score']}점")
        print(f"   투자 의견: {result['investment_opinion']}")
        print(f"   이슈 카테고리: {result['issue_category']}")

        print(f"\n💬 분석 요약:")
        print(f"   {result['analysis_summary']}")

    def _verify_db_save(self, table_name, analysis_results):
        """DB 저장 결과 검증"""
        try:
            saved_data = self.db.get_ai_analysis('2025-08-12')

            if saved_data:
                print(f"📊 DB 저장 검증:")
                print(f"   저장된 레코드: {len(saved_data)}개")
                print(f"   원본 결과: {len(analysis_results)}개")

                if len(saved_data) == len(analysis_results):
                    print("   ✅ 모든 데이터 정상 저장됨")

                    # 샘플 데이터 확인
                    sample = saved_data[0]
                    print(f"\n   📋 샘플 저장 데이터:")
                    print(f"   종목명: {sample['stock_name']}")
                    print(f"   AI점수: {sample['ai_score']}")
                    print(f"   투자의견: {sample['investment_opinion']}")
                    print(f"   이슈타입: {sample['issue_type']}")
                else:
                    print(f"   ⚠️ 저장 개수 불일치")
            else:
                print("   ❌ 저장된 데이터 조회 실패")

        except Exception as e:
            print(f"   ❌ DB 검증 오류: {e}")

    def _print_final_summary(self, results):
        """최종 요약 출력 (거래량 관련 통계 포함)"""
        if not results:
            print("❌ 분석 결과가 없습니다")
            return

        # 투자 의견별 통계
        opinion_stats = {}
        issue_type_stats = {}
        category_stats = {}

        for result in results:
            opinion = result['investment_opinion']
            issue_type = result['issue_type']
            category = result['issue_category']

            opinion_stats[opinion] = opinion_stats.get(opinion, 0) + 1
            issue_type_stats[issue_type] = issue_type_stats.get(issue_type, 0) + 1
            category_stats[category] = category_stats.get(category, 0) + 1

        print(f"📊 총 분석 종목: {len(results)}개")
        print(f"💾 DB 저장: ✅ 완료")

        print(f"\n💰 투자 의견별:")
        for opinion, count in sorted(opinion_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"   {opinion}: {count}개")

        print(f"\n🎯 이슈 타입별:")
        for issue_type, count in issue_type_stats.items():
            print(f"   {issue_type}: {count}개")

        print(f"\n📋 이슈 카테고리별:")
        for category, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"   {category}: {count}개")

        # 점수 분포
        score_ranges = {
            '90점 이상 (강력매수급)': len([r for r in results if r['ai_score'] >= 90]),
            '70-89점 (매수급)': len([r for r in results if 70 <= r['ai_score'] < 90]),
            '50-69점 (관심급)': len([r for r in results if 50 <= r['ai_score'] < 70]),
            '50점 미만 (관망급)': len([r for r in results if r['ai_score'] < 50])
        }

        print(f"\n📈 점수 분포:")
        for range_name, count in score_ranges.items():
            if count > 0:
                print(f"   {range_name}: {count}개")

        # 거래량 보너스 통계 (신규)
        volume_bonus_stats = {
            '거래량 고득점 (15점 이상)': len([r for r in results if r['volume_bonus'] >= 15]),
            '거래량 중득점 (10-14점)': len([r for r in results if 10 <= r['volume_bonus'] < 15]),
            '거래량 저득점 (5-9점)': len([r for r in results if 5 <= r['volume_bonus'] < 10]),
            '거래량 보너스 없음 (0-4점)': len([r for r in results if r['volume_bonus'] < 5])
        }

        print(f"\n📊 거래량 보너스 분포:")
        for range_name, count in volume_bonus_stats.items():
            if count > 0:
                print(f"   {range_name}: {count}개")

        # 고득점 종목
        high_score_stocks = sorted([r for r in results if r['ai_score'] >= 80],
                                   key=lambda x: x['ai_score'], reverse=True)
        if high_score_stocks:
            print(f"\n⭐ 고득점 종목 (80점 이상): {len(high_score_stocks)}개")
            for stock in high_score_stocks[:5]:  # 상위 5개만
                print(
                    f"   {stock['stock_name']}: {stock['ai_score']}점 ({stock['investment_opinion']}) - {stock['issue_category']}")

        # 강력매수 추천
        strong_buy = [r for r in results if r['investment_opinion'] == '강력매수']
        if strong_buy:
            print(f"\n🚀 강력매수 추천: {len(strong_buy)}개")
            for stock in strong_buy:
                print(f"   📈 {stock['stock_name']}")
                print(f"      점수: {stock['ai_score']}점 ({stock['issue_type']} 이슈)")
                print(f"      거래량보너스: {stock['volume_bonus']}점")
                print(f"      요약: {stock['analysis_summary'][:80]}...")

        # 복합 재료 조합
        super_combo = [r for r in results if r['combo_bonus'] >= 50]
        if super_combo:
            print(f"\n💎 슈퍼 조합 (복합재료 50점): {len(super_combo)}개")
            for stock in super_combo:
                categories = ', '.join(stock['found_categories'])
                print(f"   {stock['stock_name']}: {categories}")

        # 거래량 폭발 종목 (거래량 보너스 15점 이상)
        volume_explosion = [r for r in results if r['volume_bonus'] >= 15]
        if volume_explosion:
            print(f"\n💥 거래량 폭발 종목 (거래량보너스 15점 이상): {len(volume_explosion)}개")
            for stock in volume_explosion:
                print(f"   {stock['stock_name']}: {stock['volume_bonus']}점 거래량보너스")

        # 평균 점수
        avg_score = sum(r['ai_score'] for r in results) / len(results)
        avg_keyword = sum(r['keyword_score'] for r in results) / len(results)
        avg_combo = sum(r['combo_bonus'] for r in results) / len(results)
        avg_market = sum(r['market_score'] for r in results) / len(results)
        avg_volume = sum(r['volume_bonus'] for r in results) / len(results)

        print(f"\n📊 평균 점수:")
        print(f"   AI 점수: {avg_score:.1f}점")
        print(f"   키워드: {avg_keyword:.1f}점")
        print(f"   복합보너스: {avg_combo:.1f}점")
        print(f"   시장반응: {avg_market:.1f}점")
        print(f"   거래량보너스: {avg_volume:.1f}점")

        # 테마별 우수 종목
        theme_analysis = {}
        for result in results:
            theme = result['primary_theme']
            if theme not in theme_analysis:
                theme_analysis[theme] = []
            theme_analysis[theme].append(result)

        print(f"\n🏆 테마별 최고 종목:")
        for theme, stocks in theme_analysis.items():
            if len(stocks) >= 2:  # 2개 이상 종목이 있는 테마만
                best_stock = max(stocks, key=lambda x: x['ai_score'])
                print(f"   {theme}: {best_stock['stock_name']} ({best_stock['ai_score']}점)")


def main():
    """메인 실행"""
    print("🚀 개선된 AI 분석기 - 거래량 고려 + 임계치 개선 + 전체 분석")
    print("📋 개선사항:")
    print("   • 거래량 보너스 점수 추가 (최대 25점)")
    print("   • 테마 이슈 임계치: 50% 상승 + 1% 등락률")
    print("   • 거래량 가중 등락률 고려")
    print("   • 고거래량 종목 비율 분석")
    print("   • 전체 데이터 분석 + 무조건 DB 저장")
    print("=" * 80)

    analyzer = ImprovedVolumeAIAnalyzer()

    try:
        # 분석 날짜 입력
        analysis_date = input("분석할 날짜를 입력하세요 (YYYY-MM-DD, 기본값: 2025-08-12): ").strip()
        if not analysis_date:
            analysis_date = '2025-08-12'

        success = analyzer.run_full_analysis(analysis_date)

        if success:
            print(f"\n{'=' * 80}")
            print("✅ 전체 분석 완료!")
            print("💡 저장된 데이터는 다음 명령으로 확인할 수 있습니다:")
            print(f"   SELECT * FROM crawling_db.ai_analysis_{analysis_date.replace('-', '')} ORDER BY ai_score DESC;")
            print(f"{'=' * 80}")
        else:
            print(f"\n{'=' * 80}")
            print("❌ 분석 실패!")
            print(f"{'=' * 80}")

    except KeyboardInterrupt:
        print(f"\n{'=' * 80}")
        print("⏹️ 사용자에 의해 중단되었습니다.")
        print(f"{'=' * 80}")
    except Exception as e:
        print(f"\n{'=' * 80}")
        print(f"❌ 예상치 못한 오류 발생: {e}")
        print(f"{'=' * 80}")


if __name__ == "__main__":
    main()