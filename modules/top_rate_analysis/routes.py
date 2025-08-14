#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
등락율상위분석 실제 API 라우트 (paste.txt 기반 완전 구현)
- 실제 크롤링 실행
- 실제 데이터 분석 및 조회
- 실시간 진행상황 추적
- 테마 카드 및 상세 모달
"""

import json
import logging
import threading
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, current_app

from .database import TopRateDatabase
from .crawler import TopRateCrawler
from .utils import get_trading_date, get_table_name, format_date_for_display

# Blueprint 생성
top_rate_bp = Blueprint(
    'top_rate',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/top_rate_static'
)

# 전역 변수
db = TopRateDatabase()
crawler = None

# 실제 진행상황 추적
crawling_progress = {
    'is_running': False,
    'percent': 0,
    'message': '대기 중',
    'start_time': None,
    'end_time': None,
    'success': None,
    'error_message': '',
    'current_theme': '',
    'total_themes': 0,
    'processed_themes': 0
}


# ============= 페이지 라우트 =============

@top_rate_bp.route('/')
def index():
    """등락율상위분석 메인 페이지 (실제 데이터 기반)"""
    try:
        # 현재 거래일 계산
        trading_date = get_trading_date()

        # 실제 사용 가능한 날짜 목록
        available_dates = db.get_available_dates()

        # 시스템 상태 정보
        system_status = db.get_system_status()

        context = {
            'current_date': trading_date,
            'available_dates': available_dates,
            'page_title': '등락율상위분석 (실제 데이터)',
            'api_prefix': '/top-rate/api',
            'module_name': '등락율상위분석',
            'module_version': '4.0.0',
            'system_status': system_status
        }

        return render_template('top_rate_analysis.html', **context)

    except Exception as e:
        current_app.logger.error(f"메인 페이지 로드 실패: {e}")
        return f"페이지 로드 오류: {e}", 500


# ============= 🚀 실제 크롤링 API =============

@top_rate_bp.route('/api/collect-data', methods=['POST'])
def collect_data():
    """실제 데이터 수집 (paste.txt 크롤링 실행)"""
    global crawling_progress, crawler

    try:
        data = request.get_json() or {}
        target_date = data.get('date', get_trading_date())

        # 이미 실행 중인지 확인
        if crawling_progress['is_running']:
            return jsonify({
                'success': False,
                'message': '이미 크롤링이 실행 중입니다.'
            }), 400

        # 크롤링 진행상황 초기화
        crawling_progress.update({
            'is_running': True,
            'percent': 0,
            'message': '크롤링 준비 중...',
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': None,
            'success': None,
            'error_message': '',
            'current_theme': '',
            'total_themes': 0,
            'processed_themes': 0
        })

        # 진행상황 콜백 함수
        def progress_callback(percent, message):
            crawling_progress['percent'] = percent
            crawling_progress['message'] = message
            current_app.logger.info(f"크롤링 진행: {percent}% - {message}")

        # 백그라운드에서 실제 크롤링 실행
        def run_crawling():
            global crawler
            try:
                crawler = TopRateCrawler(progress_callback=progress_callback)
                success = crawler.crawl_and_save(target_date)

                crawling_progress.update({
                    'is_running': False,
                    'success': success,
                    'end_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'percent': 100 if success else 0,
                    'message': '크롤링 완료' if success else '크롤링 실패'
                })

                if success:
                    current_app.logger.info(f"✅ 실제 크롤링 완료: {target_date}")
                else:
                    current_app.logger.error(f"❌ 실제 크롤링 실패: {target_date}")

            except Exception as e:
                crawling_progress.update({
                    'is_running': False,
                    'success': False,
                    'error_message': str(e),
                    'end_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'message': f'크롤링 오류: {str(e)}'
                })
                current_app.logger.error(f"❌ 크롤링 예외 발생: {e}")

        # 별도 쓰레드에서 크롤링 실행
        thread = threading.Thread(target=run_crawling)
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'message': f'{target_date} 실제 데이터 수집을 시작했습니다.',
            'target_date': target_date
        })

    except Exception as e:
        current_app.logger.error(f"데이터 수집 시작 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'데이터 수집 시작 실패: {str(e)}'
        }), 500


@top_rate_bp.route('/api/crawling-progress')
def get_crawling_progress():
    """실제 크롤링 진행상황 조회"""
    return jsonify({
        'success': True,
        'progress': crawling_progress
    })


# ============= 📊 실제 분석 API =============

@top_rate_bp.route('/api/analyze', methods=['POST'])
def analyze_data():
    """실제 데이터 분석 (DB에서 실제 조회)"""
    try:
        data = request.get_json() or {}
        date_str = data.get('date', get_trading_date())

        # 데이터 존재 확인
        if not db.has_data_for_date(date_str):
            return jsonify({
                'success': False,
                'message': f'{date_str} 데이터가 없습니다. 먼저 데이터를 수집하세요.'
            }), 400

        # 실제 테마별 분석 결과 조회
        theme_results = db.get_theme_analysis_results(date_str)

        if not theme_results:
            return jsonify({
                'success': False,
                'message': f'{date_str} 분석할 데이터가 없습니다.'
            }), 400

        # 분석 요약 통계
        total_themes = len(theme_results)
        avg_change_rate = sum(theme['avg_change_rate'] for theme in theme_results) / total_themes
        total_stocks = sum(theme['stock_count'] for theme in theme_results)
        hot_themes = len([theme for theme in theme_results if theme['strength'] == 'HOT'])

        analysis_summary = {
            'date': date_str,
            'total_themes': total_themes,
            'total_stocks': total_stocks,
            'avg_change_rate': round(avg_change_rate, 2),
            'hot_themes': hot_themes,
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        current_app.logger.info(f"📊 {date_str} 실제 분석 완료: {total_themes}개 테마, {total_stocks}개 종목")

        return jsonify({
            'success': True,
            'date': date_str,
            'summary': analysis_summary,
            'themes': theme_results,
            'message': f'{date_str} 분석이 완료되었습니다.'
        })

    except Exception as e:
        current_app.logger.error(f"데이터 분석 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'데이터 분석 실패: {str(e)}'
        }), 500


@top_rate_bp.route('/api/theme-detail')
def get_theme_detail():
    """테마 상세 정보 조회 (모달용)"""
    try:
        theme_name = request.args.get('theme')
        date_str = request.args.get('date', get_trading_date())

        if not theme_name:
            return jsonify({
                'success': False,
                'message': '테마명이 필요합니다.'
            }), 400

        # 실제 테마 상세 정보 조회
        theme_detail = db.get_theme_detail(theme_name, date_str)

        if not theme_detail:
            return jsonify({
                'success': False,
                'message': f'{theme_name} 테마 정보를 찾을 수 없습니다.'
            }), 404

        current_app.logger.info(f"📋 테마 상세 조회: {theme_name} ({date_str})")

        return jsonify({
            'success': True,
            'theme_detail': theme_detail
        })

    except Exception as e:
        current_app.logger.error(f"테마 상세정보 조회 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'테마 상세정보 조회 실패: {str(e)}'
        }), 500


# ============= 📅 데이터 관리 API =============

@top_rate_bp.route('/api/available-dates')
def get_available_dates():
    """사용 가능한 날짜 목록 조회 (실제 테이블 기반)"""
    try:
        dates = db.get_available_dates()

        return jsonify({
            'success': True,
            'dates': dates,
            'total_count': len(dates),
            'latest_date': dates[0] if dates else None
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'날짜 목록 조회 실패: {str(e)}',
            'dates': []
        }), 500


@top_rate_bp.route('/api/check-date-data')
def check_date_data():
    """특정 날짜 데이터 존재 여부 확인 (실제 테이블 확인)"""
    try:
        date_str = request.args.get('date', get_trading_date())

        if not date_str:
            return jsonify({
                'success': False,
                'message': '날짜가 필요합니다.',
                'has_data': False
            }), 400

        # 실제 데이터 존재 확인
        has_data = db.has_data_for_date(date_str)

        return jsonify({
            'success': True,
            'date': date_str,
            'has_data': has_data,
            'message': f'{date_str} 데이터 {"있음" if has_data else "없음"}'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'데이터 확인 실패: {str(e)}',
            'has_data': False
        }), 500


# ============= 🖥️ 시스템 모니터링 API =============

@top_rate_bp.route('/api/system-status')
def get_system_status():
    """실시간 시스템 상태 조회"""
    try:
        status = db.get_system_status()

        # 크롤링 상태 추가
        status['crawling'] = {
            'is_running': crawling_progress['is_running'],
            'last_run': crawling_progress.get('end_time'),
            'success': crawling_progress.get('success'),
            'current_progress': crawling_progress['percent']
        }

        return jsonify({
            'success': True,
            'system_status': status
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'시스템 상태 조회 실패: {str(e)}'
        }), 500


@top_rate_bp.route('/api/health-check')
def health_check():
    """헬스 체크 (DB 연결 확인)"""
    try:
        is_healthy = db.test_connection()

        return jsonify({
            'success': True,
            'healthy': is_healthy,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'database': 'connected' if is_healthy else 'disconnected'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'healthy': False,
            'error': str(e),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }), 500


# ============= 🗑️ 데이터 관리 API =============

@top_rate_bp.route('/api/cleanup-old-data', methods=['POST'])
def cleanup_old_data():
    """오래된 데이터 정리"""
    try:
        data = request.get_json() or {}
        keep_days = data.get('keep_days', 30)

        if keep_days < 7:
            return jsonify({
                'success': False,
                'message': '최소 7일은 보관해야 합니다.'
            }), 400

        success = db.delete_old_data(keep_days)

        return jsonify({
            'success': success,
            'message': f'{keep_days}일 이전 데이터 정리 {"완료" if success else "실패"}'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'데이터 정리 실패: {str(e)}'
        }), 500


# ============= 📊 통계 API =============

@top_rate_bp.route('/api/daily-summary')
def get_daily_summary():
    """일별 요약 통계"""
    try:
        date_str = request.args.get('date', get_trading_date())

        if not db.has_data_for_date(date_str):
            return jsonify({
                'success': False,
                'message': f'{date_str} 데이터가 없습니다.'
            }), 404

        # 테마 분석 결과 조회
        themes = db.get_theme_analysis_results(date_str)

        if not themes:
            return jsonify({
                'success': False,
                'message': f'{date_str} 분석 결과가 없습니다.'
            }), 404

        # 요약 통계 계산
        total_themes = len(themes)
        total_stocks = sum(theme['stock_count'] for theme in themes)
        avg_change_rate = sum(theme['avg_change_rate'] for theme in themes) / total_themes

        # 강도별 분류
        strength_counts = {}
        for theme in themes:
            strength = theme['strength']
            strength_counts[strength] = strength_counts.get(strength, 0) + 1

        # 상위 5개 테마
        top_themes = themes[:5]

        summary = {
            'date': date_str,
            'total_themes': total_themes,
            'total_stocks': total_stocks,
            'avg_change_rate': round(avg_change_rate, 2),
            'strength_distribution': strength_counts,
            'top_themes': top_themes,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        return jsonify({
            'success': True,
            'daily_summary': summary
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'일별 요약 조회 실패: {str(e)}'
        }), 500


# ============= 🔧 유틸리티 API =============

@top_rate_bp.route('/api/test-connection')
def test_db_connection():
    """DB 연결 테스트"""
    try:
        success = db.test_connection()

        return jsonify({
            'success': success,
            'message': 'DB 연결 성공' if success else 'DB 연결 실패',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'DB 연결 테스트 실패: {str(e)}'
        }), 500


@top_rate_bp.route('/api/module-info')
def get_module_info():
    """모듈 정보 조회"""
    return jsonify({
        'success': True,
        'module_info': {
            'name': '등락율상위분석',
            'version': '4.0.0',
            'description': '실제 네이버 금융 크롤링 기반 테마 분석',
            'features': [
                '실시간 테마별 상위 종목 크롤링',
                '종목별 뉴스 5개씩 수집',
                'MySQL 데이터베이스 저장',
                '테마별 분석 결과 제공',
                '실시간 진행상황 모니터링'
            ],
            'data_source': 'Naver Finance',
            'update_frequency': '사용자 요청시',
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    })


# ============= 🚨 에러 핸들러 =============

@top_rate_bp.errorhandler(404)
def not_found_error(error):
    """404 에러 처리"""
    return jsonify({
        'success': False,
        'error': 'Not Found',
        'message': '요청한 리소스를 찾을 수 없습니다.'
    }), 404


@top_rate_bp.errorhandler(500)
def internal_error(error):
    """500 에러 처리"""
    return jsonify({
        'success': False,
        'error': 'Internal Server Error',
        'message': '서버 내부 오류가 발생했습니다.'
    }), 500


# ============= 개발자 도구 (개발 모드 전용) =============

@top_rate_bp.route('/api/dev/force-crawl/<date>')
def dev_force_crawl(date):
    """개발용: 강제 크롤링 (특정 날짜)"""
    if not current_app.config.get('DEBUG', False):
        return jsonify({'error': 'Development mode only'}), 403

    try:
        crawler_instance = TopRateCrawler()
        success = crawler_instance.crawl_and_save(date)

        return jsonify({
            'success': success,
            'message': f'{date} 강제 크롤링 {"성공" if success else "실패"}'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@top_rate_bp.route('/api/dev/reset-progress')
def dev_reset_progress():
    """개발용: 진행상황 리셋"""
    if not current_app.config.get('DEBUG', False):
        return jsonify({'error': 'Development mode only'}), 403

    global crawling_progress
    crawling_progress.update({
        'is_running': False,
        'percent': 0,
        'message': '대기 중',
        'success': None,
        'error_message': ''
    })

    return jsonify({'success': True, 'message': '진행상황 리셋 완료'})