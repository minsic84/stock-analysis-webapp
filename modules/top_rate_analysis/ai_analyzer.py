#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import openai
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
import os

from .models import NewsData, StockData, SectorData, AIAnalysisResult, SupplyDemandData
from common.utils import clean_text


class AIAnalyzer:
    """OpenAI GPT를 이용한 AI 분석 클래스"""

    def __init__(self, api_key: Optional[str] = None):
        """AI 분석기 초기화"""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다")

        openai.api_key = self.api_key

        # 분석 프롬프트 템플릿
        self.analysis_prompt_template = self._load_analysis_prompt()

    def analyze_stock_news(self, sectors: List[SectorData], news_dict: Dict[str, List[NewsData]]) -> AIAnalysisResult:
        """종목 뉴스 종합 분석"""
        try:
            # 분석용 데이터 준비
            analysis_data = self._prepare_analysis_data(sectors, news_dict)

            # GPT 프롬프트 생성
            prompt = self._create_analysis_prompt(analysis_data)

            # OpenAI GPT 호출
            response = openai.ChatCompletion.create(
                model="gpt-4",  # 또는 "gpt-3.5-turbo"
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 한국 주식시장 전문 애널리스트입니다. 당일 뉴스와 재료를 바탕으로 투자 분석을 수행합니다."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=2000,
                temperature=0.3,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )

            # 응답 파싱
            analysis_text = response.choices[0].message.content
            analysis_result = self._parse_gpt_response(analysis_text)

            logging.info("AI 분석 완료")
            return analysis_result

        except Exception as e:
            logging.error(f"AI 분석 실패: {e}")
            return self._create_fallback_analysis()

    def analyze_supply_demand(self, supply_data: List[SupplyDemandData]) -> str:
        """수급 데이터 AI 분석"""
        try:
            # 수급 데이터 요약
            supply_summary = self._summarize_supply_data(supply_data)

            prompt = f"""
다음 수급 데이터를 분석하여 투자 관점에서 해석해주세요:

{supply_summary}

분석 요점:
1. 외국인의 선제적 움직임 (예지 능력)
2. 기관 (사모펀드, 투신) 동참 여부
3. 개인 투자자의 연착매수 위험성
4. 신용잔고 과열 여부
5. 수급 단계 (기반→투신→개인) 진단

200자 이내로 핵심만 요약해주세요.
"""

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 주식 수급 분석 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.2
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logging.error(f"수급 AI 분석 실패: {e}")
            return "수급 분석을 수행할 수 없습니다."

    def _prepare_analysis_data(self, sectors: List[SectorData], news_dict: Dict[str, List[NewsData]]) -> Dict:
        """분석용 데이터 준비"""
        analysis_data = {
            "sectors": [],
            "total_news": 0,
            "key_keywords": [],
            "today_materials": []
        }

        all_keywords = []

        for sector in sectors:
            sector_info = {
                "name": sector.sector_name,
                "change_rate": sector.change_rate,
                "stocks": []
            }

            for stock in sector.top_stocks:
                stock_news = news_dict.get(stock.stock_code, [])

                stock_info = {
                    "name": stock.stock_name,
                    "code": stock.stock_code,
                    "change_rate": stock.change_rate,
                    "news_count": len(stock_news),
                    "news_titles": [news.title for news in stock_news if news.is_today],
                    "keywords": []
                }

                # 뉴스 키워드 수집
                for news in stock_news:
                    if news.is_today:  # 당일 뉴스만
                        stock_info["keywords"].extend(news.keywords)
                        all_keywords.extend(news.keywords)
                        analysis_data["today_materials"].append({
                            "stock": stock.stock_name,
                            "title": news.title,
                            "time": news.time_display,
                            "keywords": news.keywords
                        })

                sector_info["stocks"].append(stock_info)
                analysis_data["total_news"] += len([n for n in stock_news if n.is_today])

            analysis_data["sectors"].append(sector_info)

        # 주요 키워드 빈도 계산
        keyword_counts = {}
        for keyword in all_keywords:
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1

        # 상위 키워드 추출
        analysis_data["key_keywords"] = sorted(
            keyword_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        return analysis_data

    def _create_analysis_prompt(self, data: Dict) -> str:
        """GPT 분석 프롬프트 생성"""
        prompt = f"""
오늘({datetime.now().strftime('%Y-%m-%d')}) 주식시장 등락율 상위 분석을 수행합니다.

## 📊 상위 업종 현황
"""

        for sector in data["sectors"]:
            prompt += f"\n**{sector['name']}** ({sector['change_rate']:+.2f}%)\n"
            for stock in sector["stocks"]:
                if stock["news_count"] > 0:
                    prompt += f"- {stock['name']}: {stock['change_rate']:+.2f}%, 당일뉴스 {stock['news_count']}건\n"

        prompt += f"\n## 📰 주요 당일 재료 ({len(data['today_materials'])}건)\n"

        for material in data["today_materials"][:10]:  # 상위 10개만
            prompt += f"- **{material['stock']}**: {material['title']} ({material['time']})\n"

        prompt += f"\n## 🔑 키워드 빈도\n"
        for keyword, count in data["key_keywords"][:5]:
            prompt += f"- {keyword}: {count}회\n"

        prompt += f"""

## 🎯 분석 요청사항

다음 관점에서 종합 분석해주세요:

### 1. 핵심 투자 포인트 (당일 재료 중심)
- 새로운 혁신 재료 (시대개막, AI혁신 등)
- 글로벌 대기업 이슈 (투자, CEO발언, 협업)
- 대박 실적 (100%+ 증가, 글로벌 진출)
- 세계최초/FDA승인/조단위 이슈
- 복합 시너지 효과

### 2. 수급 종합 판단
- 외국인의 선제적 움직임 (예지 능력)
- 기관 (사모펀드, 투신) 동참도
- 개인 연착매수 위험도
- 수급 단계 진단

### 3. 위험 요소
- 개인 연착매수 징후
- 신용잔고 과열 가능성
- 단기 조정 리스크

### 4. 투자 전략 제언
- 단기 vs 중장기 관점
- 섹터 로테이션 전망
- 타이밍 전략

응답 형식:
JSON 형태로 다음 구조에 맞춰 답변해주세요:
{{
    "summary": "핵심 요약 (2-3문장)",
    "key_points": ["핵심포인트1", "핵심포인트2", "핵심포인트3"],
    "keywords": ["추출된키워드1", "키워드2", "키워드3"],
    "supply_analysis": "수급 분석 요약",
    "risk_factors": ["위험요소1", "위험요소2"],
    "investment_recommendation": "투자 전략 제언",
    "confidence_score": 85
}}
"""

        return prompt

    def _parse_gpt_response(self, response_text: str) -> AIAnalysisResult:
        """GPT 응답 파싱"""
        try:
            # JSON 부분 추출
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                analysis_json = json.loads(json_text)

                return AIAnalysisResult(
                    summary=analysis_json.get("summary", ""),
                    key_points=analysis_json.get("key_points", []),
                    keywords=analysis_json.get("keywords", []),
                    supply_analysis=analysis_json.get("supply_analysis", ""),
                    risk_factors=analysis_json.get("risk_factors", []),
                    investment_recommendation=analysis_json.get("investment_recommendation", ""),
                    confidence_score=analysis_json.get("confidence_score", 0.0)
                )
            else:
                # JSON 파싱 실패시 텍스트 그대로 사용
                return AIAnalysisResult(
                    summary=response_text[:200],
                    key_points=[response_text],
                    keywords=["분석완료"],
                    confidence_score=50.0
                )

        except Exception as e:
            logging.error(f"GPT 응답 파싱 실패: {e}")
            return self._create_fallback_analysis()

    def _create_fallback_analysis(self) -> AIAnalysisResult:
        """분석 실패시 기본 응답"""
        return AIAnalysisResult(
            summary="AI 분석을 수행할 수 없습니다. 수동으로 뉴스와 수급을 확인해주세요.",
            key_points=[
                "뉴스 재료 직접 확인 필요",
                "수급 동향 모니터링 필요",
                "기술적 분석 병행 권장"
            ],
            keywords=["수동분석"],
            supply_analysis="수급 데이터를 직접 확인해주세요.",
            risk_factors=["AI 분석 불가"],
            investment_recommendation="신중한 접근이 필요합니다.",
            confidence_score=0.0
        )

    def _summarize_supply_data(self, supply_data: List[SupplyDemandData]) -> str:
        """수급 데이터 요약"""
        if not supply_data:
            return "수급 데이터가 없습니다."

        # 최근 5일 데이터 요약
        recent_data = supply_data[-5:] if len(supply_data) >= 5 else supply_data

        summary = "최근 수급 현황:\n"

        total_foreign = sum(d.foreign_net for d in recent_data)
        total_institution = sum(d.institution_net for d in recent_data)
        total_individual = sum(d.individual_net for d in recent_data)

        summary += f"- 외국인: {total_foreign:+,}억원\n"
        summary += f"- 기관: {total_institution:+,}억원\n"
        summary += f"- 개인: {total_individual:+,}억원\n"

        if recent_data:
            latest = recent_data[-1]
            summary += f"- 최근 신용잔고: {latest.credit_balance:,}억원\n"

        return summary

    def _load_analysis_prompt(self) -> str:
        """분석 프롬프트 템플릿 로드"""
        return """
당신은 한국 주식시장의 전문 애널리스트입니다.
당일 발생한 뉴스와 재료를 중심으로 투자 분석을 수행합니다.

특히 다음 요소들을 중점적으로 분석합니다:
1. 혁신 재료의 임팩트
2. 글로벌 이슈의 파급효과  
3. 수급 흐름의 변화
4. 시장 타이밍과 위험 요소

당일성과 실시간성을 최우선으로 고려하여 분석해주세요.
"""

    def calculate_stock_score(self, stock: StockData, news_list: List[NewsData],
                              supply_data: Optional[SupplyDemandData] = None) -> int:
        """개별 종목 종합 점수 계산"""
        try:
            score = 50  # 기본 점수

            # 1. 등락률 점수 (30점)
            if stock.change_rate > 10:
                score += 30
            elif stock.change_rate > 5:
                score += 20
            elif stock.change_rate > 0:
                score += 10

            # 2. 뉴스 재료 점수 (25점)
            today_news = [n for n in news_list if n.is_today]
            score += min(len(today_news) * 5, 15)  # 뉴스 개수

            # 키워드 보너스
            all_keywords = []
            for news in today_news:
                all_keywords.extend(news.keywords)

            premium_keywords = ['AI', '글로벌대기업', 'FDA승인', '조단위이슈']
            keyword_bonus = len(set(all_keywords) & set(premium_keywords)) * 2
            score += min(keyword_bonus, 10)

            # 3. 신고가 점수 (20점)
            if stock.is_new_high_200d:
                score += 20
            elif stock.is_new_high_120d:
                score += 15
            elif stock.is_new_high_60d:
                score += 10
            elif stock.is_new_high_20d:
                score += 5

            # 4. 수급 점수 (25점)
            if supply_data:
                if supply_data.is_foreign_buying:
                    score += 10
                if supply_data.is_institution_buying:
                    score += 8
                if supply_data.is_individual_selling:
                    score += 7  # 개인 매도는 긍정적

            return min(score, 100)  # 최대 100점

        except Exception as e:
            logging.error(f"종목 점수 계산 실패: {e}")
            return 50