#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI 분석기 - OpenAI GPT를 활용한 뉴스 분석
개별 이슈 vs 테마 이슈 구분
"""

import openai
import json
import logging
from typing import List, Dict, Optional
import os

from .database import TopRateDatabase


class AIAnalyzer:
    """AI 뉴스 분석 클래스"""

    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다")

        openai.api_key = self.api_key
        self.db = TopRateDatabase()

    def analyze_and_save(self, analysis_date: str, theme_data: List[Dict]) -> bool:
        """테마 데이터를 AI 분석 후 DB 저장"""
        try:
            logging.info(f"🤖 {analysis_date} AI 분석 시작...")

            # AI 분석 테이블 설정 (덮어쓰기)
            ai_table = self.db.setup_ai_analysis_table(analysis_date)

            # 종목별 AI 분석 실행
            analysis_results = []
            total_stocks = len(theme_data)

            for i, stock_data in enumerate(theme_data):
                try:
                    logging.info(f"[{i + 1}/{total_stocks}] {stock_data['stock_name']} AI 분석 중...")

                    # 개별 종목 AI 분석
                    analysis_result = self._analyze_single_stock(stock_data)
                    if analysis_result:
                        analysis_results.append(analysis_result)
                        logging.info(
                            f"    ✅ {stock_data['stock_name']}: {analysis_result['issue_type']} 이슈, {analysis_result['ai_score']}점")
                    else:
                        logging.warning(f"    ❌ {stock_data['stock_name']}: 분석 실패")

                except Exception as e:
                    logging.error(f"종목 분석 실패 ({stock_data.get('stock_name', 'Unknown')}): {e}")
                    continue

            # DB 저장
            if analysis_results:
                success = self.db.save_ai_analysis(ai_table, analysis_results)
                if success:
                    logging.info(f"🎯 AI 분석 완료: {len(analysis_results)}/{total_stocks}개 종목")
                    self._print_analysis_summary(analysis_results)
                    return True
                else:
                    logging.error("AI 분석 결과 저장 실패")
                    return False
            else:
                logging.error("AI 분석 결과가 없습니다")
                return False

        except Exception as e:
            logging.error(f"AI 분석 실패: {e}")
            return False

    def _analyze_single_stock(self, stock_data: Dict) -> Optional[Dict]:
        """개별 종목 AI 분석"""
        try:
            # 뉴스 데이터 파싱
            import json as json_lib
            news_list = json_lib.loads(stock_data['news']) if isinstance(stock_data['news'], str) else stock_data[
                'news']
            themes = json_lib.loads(stock_data['themes']) if isinstance(stock_data['themes'], str) else stock_data[
                'themes']

            if not news_list:
                return None

            # 뉴스 제목들 합치기
            news_titles = [news['title'] for news in news_list if news.get('title')]
            if not news_titles:
                return None

            # GPT 분석 요청
            gpt_result = self._call_gpt_analysis(
                stock_name=stock_data['stock_name'],
                themes=themes,
                news_titles=news_titles,
                change_rate=stock_data['change_rate']
            )

            if not gpt_result:
                return None

            # 결과 구조화
            analysis_result = {
                'stock_code': stock_data['stock_code'],
                'stock_name': stock_data['stock_name'],
                'primary_theme': themes[0] if themes else '기타',
                'issue_type': gpt_result.get('issue_type', 'INDIVIDUAL'),
                'issue_category': gpt_result.get('issue_category', ''),
                'ai_score': gpt_result.get('ai_score', 50),
                'confidence_level': gpt_result.get('confidence_level', 0.5),
                'key_factors': gpt_result.get('key_factors', []),
                'news_summary': gpt_result.get('news_summary', ''),
                'ai_reasoning': gpt_result.get('ai_reasoning', ''),
                'investment_opinion': gpt_result.get('investment_opinion', '관망')
            }

            return analysis_result

        except Exception as e:
            logging.error(f"개별 종목 분석 실패: {e}")
            return None

    def _call_gpt_analysis(self, stock_name: str, themes: List[str], news_titles: List[str], change_rate: float) -> \
    Optional[Dict]:
        """GPT API 호출"""
        try:
            # 뉴스 제목들을 문자열로 합치기
            news_text = "\n".join([f"- {title}" for title in news_titles])
            themes_text = ", ".join(themes)

            prompt = f"""
다음 종목의 뉴스를 분석하여 투자 관점에서 평가해주세요.

**종목명**: {stock_name}
**소속 테마**: {themes_text}
**등락률**: {change_rate:+.2f}%

**당일 뉴스**:
{news_text}

다음 기준으로 분석해주세요:

1. **이슈 타입 판단**:
   - THEME: 해당 테마 전체에 영향을 주는 이슈 (예: AI반도체 전반의 호황, 바이오 섹터의 FDA 승인 러시)
   - INDIVIDUAL: 해당 기업만의 고유한 이슈 (예: 특정 회사의 실적 발표, 계약 체결, 신제품 출시)

2. **중요도 점수**: 1-100점 (높을수록 투자 관심도 높음)

3. **핵심 재료**: 주요 키워드들 (최대 5개)

4. **투자 의견**: 강력매수, 매수, 보유, 관망, 매도 중 선택

JSON 형태로 응답해주세요:
{{
    "issue_type": "THEME" or "INDIVIDUAL",
    "issue_category": "구체적 카테고리 (예: FDA승인, 실적발표, 계약체결)",
    "ai_score": 숫자 (1-100),
    "confidence_level": 숫자 (0.0-1.0),
    "key_factors": ["키워드1", "키워드2", ...],
    "news_summary": "뉴스 요약 (2-3문장)",
    "ai_reasoning": "판단 근거 설명",
    "investment_opinion": "투자의견"
}}
"""

            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 한국 주식시장 전문 애널리스트입니다. 뉴스를 분석하여 테마 이슈와 개별 이슈를 정확히 구분하고, 투자 관점에서 평가합니다."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1000,
                temperature=0.3
            )

            # 응답 파싱
            response_text = response.choices[0].message.content.strip()

            # JSON 부분 추출
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                result = json.loads(json_text)

                # 유효성 검증
                if self._validate_gpt_result(result):
                    return result
                else:
                    logging.warning(f"GPT 응답 유효성 검증 실패: {stock_name}")
                    return None
            else:
                logging.warning(f"GPT 응답에서 JSON을 찾을 수 없음: {stock_name}")
                return None

        except Exception as e:
            logging.error(f"GPT API 호출 실패 ({stock_name}): {e}")
            return None

    def _validate_gpt_result(self, result: Dict) -> bool:
        """GPT 응답 유효성 검증"""
        try:
            # 필수 필드 확인
            required_fields = ['issue_type', 'ai_score', 'investment_opinion']
            for field in required_fields:
                if field not in result:
                    return False

            # 값 범위 확인
            if result['issue_type'] not in ['THEME', 'INDIVIDUAL']:
                return False

            if not (1 <= result['ai_score'] <= 100):
                return False

            if result['investment_opinion'] not in ['강력매수', '매수', '보유', '관망', '매도']:
                return False

            return True

        except Exception:
            return False

    def _print_analysis_summary(self, analysis_results: List[Dict]):
        """AI 분석 결과 요약 출력"""
        if not analysis_results:
            return

        # 이슈 타입별 분류
        theme_issues = [r for r in analysis_results if r['issue_type'] == 'THEME']
        individual_issues = [r for r in analysis_results if r['issue_type'] == 'INDIVIDUAL']

        # 투자 의견별 분류
        buy_recommendations = [r for r in analysis_results if r['investment_opinion'] in ['강력매수', '매수']]

        logging.info(f"\n🤖 AI 분석 결과 요약:")
        logging.info(f"   📊 총 분석 종목: {len(analysis_results)}개")
        logging.info(f"   🎯 테마 이슈: {len(theme_issues)}개")
        logging.info(f"   🏢 개별 이슈: {len(individual_issues)}개")
        logging.info(f"   💰 매수 추천: {len(buy_recommendations)}개")

        # 고득점 종목 (80점 이상)
        high_score_stocks = [r for r in analysis_results if r['ai_score'] >= 80]
        if high_score_stocks:
            logging.info(f"\n⭐ 고득점 종목 (80점 이상):")
            for stock in sorted(high_score_stocks, key=lambda x: x['ai_score'], reverse=True):
                logging.info(
                    f"   {stock['stock_name']}: {stock['ai_score']}점 ({stock['issue_type']}) - {stock['investment_opinion']}")

        # 테마 이슈 종목
        if theme_issues:
            logging.info(f"\n🎯 테마 이슈 종목:")
            for stock in sorted(theme_issues, key=lambda x: x['ai_score'], reverse=True):
                logging.info(f"   {stock['stock_name']}: {stock['issue_category']} ({stock['ai_score']}점)")

    def get_analysis_results(self, analysis_date: str) -> Dict:
        """AI 분석 결과 조회 및 분류"""
        try:
            ai_results = self.db.get_ai_analysis(analysis_date)

            if not ai_results:
                return {
                    'success': False,
                    'message': f'{analysis_date} 날짜의 AI 분석 결과가 없습니다.'
                }

            # 테마 이슈 vs 개별 이슈 분류
            theme_issues = []
            individual_issues = []

            for result in ai_results:
                # JSON 파싱
                if isinstance(result['key_factors'], str):
                    result['key_factors'] = json.loads(result['key_factors'])

                if result['issue_type'] == 'THEME':
                    theme_issues.append(result)
                else:
                    individual_issues.append(result)

            # 점수순 정렬
            theme_issues.sort(key=lambda x: x['ai_score'], reverse=True)
            individual_issues.sort(key=lambda x: x['ai_score'], reverse=True)

            return {
                'success': True,
                'total_analyzed': len(ai_results),
                'theme_issues': theme_issues,
                'individual_issues': individual_issues,
                'high_score_stocks': [r for r in ai_results if r['ai_score'] >= 80],
                'buy_recommendations': [r for r in ai_results if r['investment_opinion'] in ['강력매수', '매수']]
            }

        except Exception as e:
            logging.error(f"AI 분석 결과 조회 실패: {e}")
            return {
                'success': False,
                'message': f'AI 분석 결과 조회 실패: {str(e)}'
            }