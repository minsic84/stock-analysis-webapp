#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, request, jsonify, current_app
import logging
import uuid
from datetime import datetime
from typing import Dict, List
import threading
import time

from .models import TopRateAnalysis, ScoreGrade
from .crawler import NaverFinanceCrawler
from .news_crawler import NewsCrawler
from .ai_analyzer import AIAnalyzer
from .chart_analyzer import ChartAnalyzer

# 블루프린트 생성
top_rate_bp = Blueprint(
    'top_rate_analysis',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/top_rate_analysis/static'
)

# 전역 변수로 분석 상태 관리
analysis_cache: Dict[str, TopRateAnalysis] = {}
current_analysis_id = None


@top_rate_bp.route('/')
def index():
    """등락율상위분석 메인 페이지"""
    return render_template('top_rate_analysis.html')


@top_rate_bp.route('/crawl-sectors', methods=['POST'])
def crawl_sectors():
    """업종 데이터 크롤링 시작"""
    try:
        global current_analysis_id

        # 새로운 분석 세션 생성
        analysis_id = str(uuid.uuid4())
        current_analysis_id = analysis_id

        analysis = TopRateAnalysis(
            analysis_id=analysis_id,
            crawl_status="crawling"
        )
        analysis_cache[analysis_id] = analysis

        # 백그라운드에서 크롤링 실행
        thread = threading.Thread(
            target=background_crawling,
            args=(analysis_id,)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'message': '업종 데이터 크롤링을 시작했습니다.',
            'analysis_id': analysis_id
        })

    except Exception as e:
        logging.error(f"크롤링 시작 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'크롤링 시작 실패: {str(e)}'
        }), 500


@top_rate_bp.route('/analyze-ai', methods=['POST'])
def analyze_ai():
    """AI 분석 시작"""
    try:
        global current_analysis_id

        if not current_analysis_id or current_analysis_id not in analysis_cache:
            return jsonify({
                'success': False,
                'message': '먼저 업종 데이터를 크롤링해주세요.'
            }), 400

        analysis = analysis_cache[current_analysis_id]

        if analysis.crawl_status != "completed":
            return jsonify({
                'success': False,
                'message': '크롤링이 완료된 후 AI 분석을 시작할 수 있습니다.'
            }), 400

        # 백그라운드에서 AI 분석 실행
        thread = threading.Thread(
            target=background_ai_analysis,
            args=(current_analysis_id,)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'message': 'AI 분석을 시작했습니다.'
        })

    except Exception as e:
        logging.error(f"AI 분석 시작 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'AI 분석 시작 실패: {str(e)}'
        }), 500


@top_rate_bp.route('/generate-charts', methods=['POST'])
def generate_charts():
    """차트 분석 시작"""
    try:
        global current_analysis_id

        if not current_analysis_id or current_analysis_id not in analysis_cache:
            return jsonify({
                'success': False,
                'message': '먼저 업종 데이터를 크롤링해주세요.'
            }), 400

        analysis = analysis_cache[current_analysis_id]

        # 백그라운드에서 차트 분석 실행
        thread = threading.Thread(
            target=background_chart_analysis,
            args=(current_analysis_id,)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'message': '차트 분석을 시작했습니다.'
        })

    except Exception as e:
        logging.error(f"차트 분석 시작 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'차트 분석 시작 실패: {str(e)}'
        }), 500


@top_rate_bp.route('/status')
def get_status():
    """분석 상태 조회"""
    try:
        global current_analysis_id

        if not current_analysis_id or current_analysis_id not in analysis_cache:
            return jsonify({
                'analysis_id': None,
                'crawl_status': 'pending',
                'analysis_status': 'pending',
                'statistics': {
                    'total_sectors': 0,
                    'total_news_stocks': 0,
                    'total_analyzed_stocks': 0,
                    'new_high_stocks_count': 0
                }
            })

        analysis = analysis_cache[current_analysis_id]
        analysis.update_statistics()

        return jsonify({
            'analysis_id': analysis.analysis_id,
            'crawl_status': analysis.crawl_status,
            'analysis_status': analysis.analysis_status,
            'statistics': {
                'total_sectors': analysis.total_sectors,
                'total_news_stocks': analysis.total_news_stocks,
                'total_analyzed_stocks': analysis.total_analyzed_stocks,
                'new_high_stocks_count': analysis.new_high_stocks_count
            },
            'updated_at': analysis.updated_at.isoformat()
        })

    except Exception as e:
        logging.error(f"상태 조회 실패: {e}")
        return jsonify({'error': str(e)}), 500


@top_rate_bp.route('/results')
def get_results():
    """분석 결과 조회"""
    try:
        global current_analysis_id

        if not current_analysis_id or current_analysis_id not in analysis_cache:
            return jsonify({
                'success': False,
                'message': '분석 결과가 없습니다.'
            })

        analysis = analysis_cache[current_analysis_id]

        # 업종 데이터 변환
        sectors_data = []
        for sector in analysis.top_sectors:
            sector_dict = {
                'sector_name': sector.sector_name,
                'change_rate': sector.change_rate,
                'formatted_change_rate': sector.formatted_change_rate,
                'is_positive': sector.is_positive,
                'top_stocks': []
            }

            for stock in sector.top_stocks:
                stock_dict = {
                    'stock_code': stock.stock_code,
                    'stock_name': stock.stock_name,
                    'current_price': stock.current_price,
                    'formatted_price': stock.formatted_price,
                    'change_rate': stock.change_rate,
                    'formatted_change_rate': stock.formatted_change_rate,
                    'is_positive': stock.is_positive,
                    'volume': stock.volume,
                    'new_high_days': stock.new_high_days,
                    'supply_badges': stock.supply_badges,
                    'supply_stage': stock.supply_stage.value,
                    'total_score': stock.total_score,
                    'score_grade': stock.score_grade.value,
                    'news_list': [
                        {
                            'title': news.title,
                            'url': news.url,
                            'source': news.source,
                            'time_display': news.time_display,
                            'keywords': news.keywords
                        }
                        for news in stock.news_list
                    ]
                }
                sector_dict['top_stocks'].append(stock_dict)

            sectors_data.append(sector_dict)

        # AI 분석 결과
        ai_result = None
        if analysis.ai_analysis:
            ai_result = {
                'summary': analysis.ai_analysis.summary,
                'key_points': analysis.ai_analysis.key_points,
                'keywords': analysis.ai_analysis.keywords,
                'supply_analysis': analysis.ai_analysis.supply_analysis,
                'risk_factors': analysis.ai_analysis.risk_factors,
                'investment_recommendation': analysis.ai_analysis.investment_recommendation,
                'confidence_score': analysis.ai_analysis.confidence_score
            }

        # 차트 데이터
        charts_data = []
        for chart in analysis.chart_analyses:
            chart_analyzer = ChartAnalyzer()
            chart_data = chart_analyzer.create_chart_data_for_frontend(chart)
            if chart_data:
                charts_data.append(chart_data)

        return jsonify({
            'success': True,
            'data': {
                'sectors': sectors_data,
                'ai_analysis': ai_result,
                'charts': charts_data,
                'statistics': {
                    'total_sectors': analysis.total_sectors,
                    'total_news_stocks': analysis.total_news_stocks,
                    'total_analyzed_stocks': analysis.total_analyzed_stocks,
                    'new_high_stocks_count': analysis.new_high_stocks_count
                }
            }
        })

    except Exception as e:
        logging.error(f"결과 조회 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'결과 조회 실패: {str(e)}'
        }), 500


def background_crawling(analysis_id: str):
    """백그라운드 크롤링 작업"""
    try:
        analysis = analysis_cache[analysis_id]
        analysis.crawl_status = "crawling"

        # 1. 네이버 금융 크롤링
        crawler = NaverFinanceCrawler()

        # 상위 5개 업종 크롤링
        logging.info("상위 업종 크롤링 시작")
        top_sectors = crawler.crawl_top_sectors(limit=5)
        analysis.top_sectors = top_sectors

        # 2. 뉴스 크롤링
        news_crawler = NewsCrawler()

        logging.info("뉴스 크롤링 시작")
        all_news_stocks = []
        for sector in top_sectors:
            all_news_stocks.extend(sector.top_stocks)

        # 뉴스 수집
        news_dict = news_crawler.crawl_multiple_stocks_news(all_news_stocks, limit_per_stock=3)

        # 뉴스를 종목에 할당
        for sector in analysis.top_sectors:
            for stock in sector.top_stocks:
                stock.news_list = news_dict.get(stock.stock_code, [])

        # 3. 모든 업종의 전체 종목 크롤링 (신고가 분석용)
        logging.info("전체 종목 크롤링 시작")
        all_stocks = []
        for sector in top_sectors:
            sector_stocks = crawler.crawl_all_sector_stocks(sector.sector_code)
            for stock in sector_stocks:
                stock.sector = sector.sector_name
            all_stocks.extend(sector_stocks)

        analysis.all_stocks = all_stocks
        analysis.crawl_status = "completed"
        analysis.update_statistics()

        logging.info(f"크롤링 완료: 업종 {len(top_sectors)}개, 전체 종목 {len(all_stocks)}개")

    except Exception as e:
        logging.error(f"백그라운드 크롤링 실패: {e}")
        if analysis_id in analysis_cache:
            analysis_cache[analysis_id].crawl_status = "error"


def background_ai_analysis(analysis_id: str):
    """백그라운드 AI 분석 작업"""
    try:
        analysis = analysis_cache[analysis_id]
        analysis.analysis_status = "analyzing"

        # AI 분석기 초기화
        ai_analyzer = AIAnalyzer()

        # 뉴스 데이터 준비
        news_dict = {}
        for sector in analysis.top_sectors:
            for stock in sector.top_stocks:
                news_dict[stock.stock_code] = stock.news_list

        # AI 분석 실행
        logging.info("AI 분석 시작")
        ai_result = ai_analyzer.analyze_stock_news(analysis.top_sectors, news_dict)
        analysis.ai_analysis = ai_result

        # 개별 종목 점수 계산
        for sector in analysis.top_sectors:
            for stock in sector.top_stocks:
                stock.total_score = ai_analyzer.calculate_stock_score(
                    stock, stock.news_list
                )

                # 점수에 따른 등급 부여
                if stock.total_score >= 90:
                    stock.score_grade = ScoreGrade.A_PLUS
                elif stock.total_score >= 80:
                    stock.score_grade = ScoreGrade.A
                elif stock.total_score >= 70:
                    stock.score_grade = ScoreGrade.B_PLUS
                elif stock.total_score >= 60:
                    stock.score_grade = ScoreGrade.B
                elif stock.total_score >= 50:
                    stock.score_grade = ScoreGrade.C
                else:
                    stock.score_grade = ScoreGrade.D

        analysis.analysis_status = "completed"
        logging.info("AI 분석 완료")

    except Exception as e:
        logging.error(f"AI 분석 실패: {e}")
        if analysis_id in analysis_cache:
            analysis_cache[analysis_id].analysis_status = "error"


def background_chart_analysis(analysis_id: str):
    """백그라운드 차트 분석 작업"""
    try:
        analysis = analysis_cache[analysis_id]

        chart_analyzer = ChartAnalyzer()

        # 신고가 종목 필터링
        logging.info("신고가 종목 분석 시작")
        new_high_stocks = chart_analyzer.analyze_new_high_stocks(analysis.all_stocks)

        # 신고가 종목들의 차트 분석
        chart_analyses = []
        for stock in new_high_stocks[:10]:  # 상위 10개만
            try:
                chart_analysis = chart_analyzer.create_chart_analysis(stock)
                if chart_analysis:
                    chart_analyses.append(chart_analysis)

                time.sleep(0.1)  # DB 부하 방지

            except Exception as e:
                logging.error(f"종목 차트 분석 실패 ({stock.stock_name}): {e}")
                continue

        analysis.chart_analyses = chart_analyses
        logging.info(f"차트 분석 완료: {len(chart_analyses)}개 종목")

    except Exception as e:
        logging.error(f"차트 분석 실패: {e}")


@top_rate_bp.route('/test-crawling')
def test_crawling():
    """크롤링 테스트용 엔드포인트"""
    try:
        crawler = NaverFinanceCrawler()

        # 더 상세한 테스트
        logging.info("크롤링 테스트 시작...")
        test_result = crawler.crawl_rising_stocks(limit=5)

        # 실패시 대안 URL 테스트
        if not test_result:
            logging.warning("기본 크롤링 실패, 대안 방법 시도...")

            # 네이버 금융 메인 페이지 접근 테스트
            import requests
            test_url = "https://finance.naver.com"
            try:
                response = requests.get(test_url, timeout=10)
                logging.info(f"네이버 금융 접근 테스트 - 상태코드: {response.status_code}")
            except Exception as e:
                logging.error(f"네이버 금융 접근 실패: {e}")

        return jsonify({
            'success': True,
            'message': f'테스트 완료: {len(test_result)}개 종목 크롤링',
            'debug_info': {
                'total_stocks': len(test_result),
                'has_data': len(test_result) > 0,
                'sample_stocks': [
                    {
                        'name': stock.stock_name,
                        'code': stock.stock_code,
                        'change_rate': stock.change_rate,
                        'price': stock.current_price
                    }
                    for stock in test_result[:3]
                ]
            },
            'data': [
                {
                    'name': stock.stock_name,
                    'code': stock.stock_code,
                    'change_rate': stock.change_rate
                }
                for stock in test_result
            ]
        })

    except Exception as e:
        logging.error(f"크롤링 테스트 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'테스트 실패: {str(e)}',
            'error_type': type(e).__name__
        }), 500


# routes.py에 추가할 디버깅 엔드포인트들

@top_rate_bp.route('/test-simple')
def test_simple():
    """가장 간단한 테스트"""
    try:
        return jsonify({
            'success': True,
            'message': '기본 라우트 정상 작동',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@top_rate_bp.route('/test-crawler-only')
def test_crawler_only():
    """크롤러만 단순 테스트"""
    try:
        from .crawler import NaverFinanceCrawler

        crawler = NaverFinanceCrawler()

        # 매우 간단한 크롤링 테스트
        test_stocks = crawler.crawl_rising_stocks(limit=3)

        return jsonify({
            'success': True,
            'message': f'크롤링 테스트 완료: {len(test_stocks)}개 종목',
            'stocks': [
                {
                    'name': stock.stock_name,
                    'code': stock.stock_code,
                    'change_rate': stock.change_rate
                }
                for stock in test_stocks
            ]
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@top_rate_bp.route('/test-sync-crawl-get')
def test_sync_crawl_get():
    """동기 방식 업종 크롤링 테스트 (GET)"""
    try:
        from .crawler import NaverFinanceCrawler

        crawler = NaverFinanceCrawler()

        # 1개 업종만 테스트
        sectors = crawler.crawl_top_sectors(limit=1)

        return jsonify({
            'success': True,
            'message': f'업종 크롤링 테스트 완료: {len(sectors)}개 업종',
            'sectors': [
                {
                    'name': sector.sector_name,
                    'change_rate': sector.change_rate,
                    'stocks_count': len(sector.top_stocks) if sector.top_stocks else 0,
                    'stocks': [
                        {
                            'name': stock.stock_name,
                            'code': stock.stock_code,
                            'change_rate': stock.change_rate
                        }
                        for stock in (sector.top_stocks[:2] if sector.top_stocks else [])
                    ]
                }
                for sector in sectors
            ]
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@top_rate_bp.route('/debug-imports')
def debug_imports():
    """import 문제 확인"""
    try:
        results = {}

        # 기본 라이브러리들
        try:
            import requests
            results['requests'] = '✓ 정상'
        except Exception as e:
            results['requests'] = f'✗ 오류: {str(e)}'

        try:
            from bs4 import BeautifulSoup
            results['beautifulsoup4'] = '✓ 정상'
        except Exception as e:
            results['beautifulsoup4'] = f'✗ 오류: {str(e)}'

        try:
            import openai
            results['openai'] = '✓ 정상'
        except Exception as e:
            results['openai'] = f'✗ 오류: {str(e)}'

        # 내부 모듈들
        try:
            from .models import SectorData, StockData
            results['models'] = '✓ 정상'
        except Exception as e:
            results['models'] = f'✗ 오류: {str(e)}'

        try:
            from .crawler import NaverFinanceCrawler
            results['crawler'] = '✓ 정상'
        except Exception as e:
            results['crawler'] = f'✗ 오류: {str(e)}'

        try:
            from common.utils import safe_request
            results['common_utils'] = '✓ 정상'
        except Exception as e:
            results['common_utils'] = f'✗ 오류: {str(e)}'

        return jsonify({
            'success': True,
            'imports': results
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# routes.py에 추가할 페이지 구조 확인 함수

@top_rate_bp.route('/debug-page-structure')
def debug_page_structure():
    """네이버 금융 페이지 구조 확인"""
    try:
        import requests
        from bs4 import BeautifulSoup

        results = {}

        # 1. 업종 페이지 구조 확인
        url = "https://finance.naver.com/sise/sise_group.naver?type=upjong"

        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }, timeout=10)

        results['status_code'] = response.status_code
        results['content_length'] = len(response.content)

        soup = BeautifulSoup(response.content, 'html.parser')
        results['page_title'] = soup.title.text if soup.title else 'No title'

        # 테이블 찾기
        tables = soup.find_all('table')
        results['total_tables'] = len(tables)

        table_info = []
        for i, table in enumerate(tables):
            info = {
                'index': i,
                'class': table.get('class', []),
                'id': table.get('id', ''),
                'rows_count': len(table.find_all('tr')) if table.find_all('tr') else 0,
                'has_tbody': table.find('tbody') is not None
            }

            # 첫 번째 행의 내용 확인
            first_row = table.find('tr')
            if first_row:
                cells = first_row.find_all(['td', 'th'])
                info['first_row_cells'] = len(cells)
                info['first_row_sample'] = [cell.get_text().strip()[:20] for cell in cells[:3]]

            table_info.append(info)

        results['tables'] = table_info

        # type_1 클래스 테이블 특별 확인
        type1_table = soup.find('table', {'class': 'type_1'})
        if type1_table:
            results['type1_table'] = {
                'found': True,
                'has_tbody': type1_table.find('tbody') is not None,
                'rows_direct': len(type1_table.find_all('tr', recursive=False)),
                'rows_all': len(type1_table.find_all('tr')),
                'sample_rows': []
            }

            # 처음 3개 행 샘플
            rows = type1_table.find_all('tr')[:3]
            for row in rows:
                cells = row.find_all(['td', 'th'])
                sample_row = [cell.get_text().strip()[:15] for cell in cells[:5]]
                results['type1_table']['sample_rows'].append(sample_row)
        else:
            results['type1_table'] = {'found': False}

        return jsonify({
            'success': True,
            'url': url,
            'results': results
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@top_rate_bp.route('/debug-alternative-urls')
def debug_alternative_urls():
    """다른 네이버 금융 URL들 테스트"""
    try:
        import requests
        from bs4 import BeautifulSoup

        urls_to_test = [
            "https://finance.naver.com/sise/sise_group.naver?type=upjong",
            "https://finance.naver.com/sise/sise_rise.naver",
            "https://finance.naver.com/sise/sise_fall.naver",
            "https://finance.naver.com/sise/",
            "https://finance.naver.com/"
        ]

        results = {}

        for url in urls_to_test:
            try:
                response = requests.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }, timeout=10)

                soup = BeautifulSoup(response.content, 'html.parser')

                results[url] = {
                    'status': response.status_code,
                    'title': soup.title.text if soup.title else 'No title',
                    'tables_count': len(soup.find_all('table')),
                    'type1_tables': len(soup.find_all('table', {'class': 'type_1'})),
                    'type2_tables': len(soup.find_all('table', {'class': 'type_2'})),
                    'content_length': len(response.content)
                }

            except Exception as e:
                results[url] = {
                    'status': 'error',
                    'error': str(e)
                }

        return jsonify({
            'success': True,
            'results': results
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500