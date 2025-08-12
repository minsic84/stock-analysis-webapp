#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, request, jsonify
import logging
import threading
import time
from datetime import datetime
from typing import Dict, List

from .database import TopRateDatabase
from .crawler import ThemeCrawler
from .ai_analyzer import AIAnalyzer
from .utils import group_themes_by_name, calculate_theme_stats

# 블루프린트 생성
top_rate_bp = Blueprint(
    'top_rate_analysis',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/top_rate_analysis/static'
)

# 전역 변수로 진행 상태 관리
crawling_progress = {}
ai_analysis_progress = {}


@top_rate_bp.route('/')
def index():
    """등락율상위분석 메인 페이지"""
    return render_template('top_rate_analysis.html')


@top_rate_bp.route('/crawl-themes', methods=['POST'])
def crawl_themes():
    """당일 테마 데이터 크롤링 시작"""
    try:
        data = request.get_json()
        analysis_date = data.get('date', datetime.now().strftime('%Y-%m-%d'))
        mode = data.get('mode', 'manual')

        # 오늘 날짜가 아니면 크롤링 불가
        today = datetime.now().strftime('%Y-%m-%d')
        if analysis_date != today:
            return jsonify({
                'success': False,
                'message': f'과거 날짜({analysis_date})는 크롤링할 수 없습니다. DB에서 기존 데이터를 조회하세요.'
            }), 400

        # 진행 상태 초기화
        crawling_progress[analysis_date] = {
            'status': 'started',
            'current_theme': '',
            'completed_themes': 0,
            'total_themes': 0,
            'message': '크롤링을 시작합니다...'
        }

        # 백그라운드에서 크롤링 실행
        thread = threading.Thread(
            target=background_crawling,
            args=(analysis_date, mode)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'message': f'{analysis_date} 테마 데이터 크롤링을 시작했습니다.',
            'mode': mode
        })

    except Exception as e:
        logging.error(f"크롤링 시작 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'크롤링 시작 실패: {str(e)}'
        }), 500


@top_rate_bp.route('/crawling-progress/<date>')
def get_crawling_progress(date):
    """크롤링 진행률 조회"""
    try:
        progress = crawling_progress.get(date, {
            'status': 'not_started',
            'current_theme': '',
            'completed_themes': 0,
            'total_themes': 0,
            'message': '크롤링이 시작되지 않았습니다.'
        })

        return jsonify({
            'success': True,
            'progress': progress
        })

    except Exception as e:
        logging.error(f"진행률 조회 실패: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@top_rate_bp.route('/load-themes/<date>')
def load_themes(date):
    """특정 날짜의 테마 데이터 조회"""
    try:
        db = TopRateDatabase()

        # 테마 데이터 조회
        theme_data = db.get_theme_data(date)

        if not theme_data:
            return jsonify({
                'success': False,
                'message': f'{date} 날짜의 테마 데이터가 없습니다. 먼저 데이터 수집을 진행해주세요.'
            })

        # 테마별로 그룹화
        themes_grouped = group_themes_by_name(theme_data)

        # 통계 계산
        stats = calculate_theme_stats(theme_data)

        return jsonify({
            'success': True,
            'themes': themes_grouped,
            'stats': stats,
            'date': date
        })

    except Exception as e:
        logging.error(f"테마 데이터 조회 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'테마 데이터 조회 실패: {str(e)}'
        }), 500


@top_rate_bp.route('/ai-analysis', methods=['POST'])
def start_ai_analysis():
    """AI 분석 시작 (사용자가 버튼 클릭시에만 실행)"""
    try:
        data = request.get_json()
        analysis_date = data.get('date', datetime.now().strftime('%Y-%m-%d'))

        db = TopRateDatabase()

        # 해당 날짜의 테마 데이터 존재 여부 확인
        theme_data = db.get_theme_data(analysis_date)
        if not theme_data:
            return jsonify({
                'success': False,
                'message': f'{analysis_date} 날짜의 테마 데이터가 없습니다. 먼저 데이터 수집을 진행해주세요.'
            })

        # AI 분석 진행 상태 초기화
        ai_analysis_progress[analysis_date] = {
            'status': 'started',
            'current_stock': '',
            'completed_stocks': 0,
            'total_stocks': len(theme_data),
            'message': 'AI 분석을 시작합니다...'
        }

        # 백그라운드에서 AI 분석 실행
        thread = threading.Thread(
            target=background_ai_analysis,
            args=(analysis_date, theme_data)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'message': f'{analysis_date} AI 분석을 시작했습니다.',
            'estimated_time': f'{len(theme_data)}개 종목 약 {len(theme_data) * 3}초 소요 예상'
        })

    except Exception as e:
        logging.error(f"AI 분석 시작 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'AI 분석 시작 실패: {str(e)}'
        }), 500


@top_rate_bp.route('/ai-progress/<date>')
def get_ai_progress(date):
    """AI 분석 진행률 조회"""
    try:
        progress = ai_analysis_progress.get(date, {
            'status': 'not_started',
            'current_stock': '',
            'completed_stocks': 0,
            'total_stocks': 0,
            'message': 'AI 분석이 시작되지 않았습니다.'
        })

        return jsonify({
            'success': True,
            'progress': progress
        })

    except Exception as e:
        logging.error(f"AI 진행률 조회 실패: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@top_rate_bp.route('/ai-results/<date>')
def get_ai_results(date):
    """AI 분석 결과 조회"""
    try:
        analyzer = AIAnalyzer()
        results = analyzer.get_analysis_results(date)

        return jsonify(results)

    except Exception as e:
        logging.error(f"AI 분석 결과 조회 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'AI 분석 결과 조회 실패: {str(e)}'
        }), 500


@top_rate_bp.route('/comprehensive-analysis', methods=['POST'])
def start_comprehensive_analysis():
    """종합분석 시작 (일봉+수급 데이터 결합)"""
    try:
        data = request.get_json()
        analysis_date = data.get('date', datetime.now().strftime('%Y-%m-%d'))

        # AI 분석 결과 존재 여부 확인
        analyzer = AIAnalyzer()
        ai_results = analyzer.get_analysis_results(analysis_date)

        if not ai_results['success']:
            return jsonify({
                'success': False,
                'message': f'{analysis_date} 날짜의 AI 분석 결과가 없습니다. 먼저 AI 분석을 진행해주세요.'
            })

        # TODO: 종합분석 로직 구현
        # 1. AI 분석 결과 + 일봉 데이터 + 수급 데이터 결합
        # 2. 신고가 여부 판단
        # 3. 수급 패턴 분석
        # 4. 종합 점수 산출

        return jsonify({
            'success': True,
            'message': f'{analysis_date} 종합분석이 완료되었습니다.',
            'results': {
                'analyzed_stocks': len(ai_results.get('high_score_stocks', [])),
                'new_high_stocks': 0,  # TODO: 실제 계산
                'top_recommendations': ai_results.get('buy_recommendations', [])[:5]
            }
        })

    except Exception as e:
        logging.error(f"종합분석 시작 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'종합분석 시작 실패: {str(e)}'
        }), 500


@top_rate_bp.route('/check-analysis/<date>')
def check_analysis_exists(date):
    """특정 날짜의 분석 결과 존재 여부 확인"""
    try:
        db = TopRateDatabase()

        # 테이블 존재 여부 확인
        date_suffix = date.replace('-', '')
        theme_table = f"theme_{date_suffix}"
        ai_table = f"ai_analysis_{date_suffix}"

        theme_exists = db.check_table_exists(theme_table)
        ai_exists = db.check_table_exists(ai_table)

        return jsonify({
            'success': True,
            'theme_data_exists': theme_exists,
            'ai_analysis_exists': ai_exists,
            'comprehensive_exists': False,  # TODO: 구현
            'date': date
        })

    except Exception as e:
        logging.error(f"분석 존재 여부 확인 실패: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


def background_crawling(analysis_date: str, mode: str):
    """백그라운드 크롤링 작업"""
    try:
        # 진행 상태 업데이트
        def update_progress(current_theme: str, completed: int, total: int, message: str):
            crawling_progress[analysis_date] = {
                'status': 'running',
                'current_theme': current_theme,
                'completed_themes': completed,
                'total_themes': total,
                'message': message
            }

        update_progress('', 0, 0, '크롤링을 준비하고 있습니다...')

        # 크롤러 실행
        crawler = ThemeCrawler()

        # 진행률 업데이트를 위한 크롤러 수정 (추후 개선)
        success = crawler.crawl_and_save_themes(analysis_date)

        if success:
            crawling_progress[analysis_date] = {
                'status': 'completed',
                'current_theme': '',
                'completed_themes': 100,
                'total_themes': 100,
                'message': '크롤링이 완료되었습니다!'
            }
            logging.info(f"✅ {analysis_date} 크롤링 완료")
        else:
            crawling_progress[analysis_date] = {
                'status': 'failed',
                'current_theme': '',
                'completed_themes': 0,
                'total_themes': 0,
                'message': '크롤링 중 오류가 발생했습니다.'
            }
            logging.error(f"❌ {analysis_date} 크롤링 실패")

    except Exception as e:
        crawling_progress[analysis_date] = {
            'status': 'failed',
            'current_theme': '',
            'completed_themes': 0,
            'total_themes': 0,
            'message': f'크롤링 오류: {str(e)}'
        }
        logging.error(f"백그라운드 크롤링 실패: {e}")


def background_ai_analysis(analysis_date: str, theme_data: List[Dict]):
    """백그라운드 AI 분석 작업"""
    try:
        # 진행 상태 업데이트 함수
        def update_ai_progress(current_stock: str, completed: int, total: int, message: str):
            ai_analysis_progress[analysis_date] = {
                'status': 'running',
                'current_stock': current_stock,
                'completed_stocks': completed,
                'total_stocks': total,
                'message': message
            }

        update_ai_progress('', 0, len(theme_data), 'AI 분석을 준비하고 있습니다...')

        # AI 분석기 실행
        analyzer = AIAnalyzer()

        # 진행률 업데이트를 위한 개선된 분석 (추후 analyzer 수정)
        success = analyzer.analyze_and_save(analysis_date, theme_data)

        if success:
            ai_analysis_progress[analysis_date] = {
                'status': 'completed',
                'current_stock': '',
                'completed_stocks': len(theme_data),
                'total_stocks': len(theme_data),
                'message': 'AI 분석이 완료되었습니다!'
            }
            logging.info(f"✅ {analysis_date} AI 분석 완료")
        else:
            ai_analysis_progress[analysis_date] = {
                'status': 'failed',
                'current_stock': '',
                'completed_stocks': 0,
                'total_stocks': len(theme_data),
                'message': 'AI 분석 중 오류가 발생했습니다.'
            }
            logging.error(f"❌ {analysis_date} AI 분석 실패")

    except Exception as e:
        ai_analysis_progress[analysis_date] = {
            'status': 'failed',
            'current_stock': '',
            'completed_stocks': 0,
            'total_stocks': len(theme_data),
            'message': f'AI 분석 오류: {str(e)}'
        }
        logging.error(f"백그라운드 AI 분석 실패: {e}")


# 디버깅용 엔드포인트들
@top_rate_bp.route('/test-db')
def test_database():
    """데이터베이스 연결 테스트"""
    try:
        db = TopRateDatabase()
        success = db.setup_crawling_database()

        return jsonify({
            'success': success,
            'message': '데이터베이스 연결 테스트 완료' if success else '데이터베이스 연결 실패'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@top_rate_bp.route('/test-crawler')
def test_crawler():
    """크롤러 간단 테스트"""
    try:
        crawler = ThemeCrawler()
        themes = crawler.get_theme_list()

        return jsonify({
            'success': True,
            'message': f'테마 {len(themes)}개 크롤링 테스트 완료',
            'themes': themes[:3]  # 상위 3개만 표시
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500