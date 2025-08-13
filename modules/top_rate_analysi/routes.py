#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
등락율상위분석 Flask Blueprint Routes
- 완전 독립적인 API 엔드포인트
- 실시간 진행상황 추적
- 자동 스케줄 관리
"""

import json
import logging
import threading
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, current_app

from .database import TopRateDatabase
from .crawler import TopRateCrawler, crawling_progress
from .scheduler import TopRateScheduler, get_scheduler
from .utils import get_trading_date, get_table_name, calculate_theme_stats

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
scheduler = None


@top_rate_bp.before_app_first_request
def init_scheduler():
    """앱 첫 요청 전 스케줄러 초기화"""
    global scheduler
    try:
        scheduler = get_scheduler()
        scheduler.init_app(current_app)
    except Exception as e:
        current_app.logger.error(f"스케줄러 초기화 실패: {e}")


# ============= 페이지 라우트 =============

@top_rate_bp.route('/')
def index():
    """등락율상위분석 메인 페이지"""
    try:
        # 현재 거래일 계산
        trading_date = get_trading_date()

        # 사용 가능한 날짜 목록
        available_dates = db.get_available_dates()

        context = {
            'current_date': trading_date,
            'available_dates': available_dates,
            'page_title': '등락율상위분석'
        }

        return render_template('top_rate_analysis.html', **context)

    except Exception as e:
        current_app.logger.error(f"메인 페이지 로드 실패: {e}")
        return f"페이지 로드 오류: {e}", 500


# ============= 데이터 수집 API =============

@top_rate_bp.route('/api/collect-data', methods=['POST'])
def collect_data():
    """당일 데이터 수집 시작"""
    try:
        data = request.get_json()
        target_date = data.get('date') if data else None

        # 날짜 검증
        if target_date is None:
            target_date = get_trading_date()

        # 이미 크롤링 중인지 확인
        if crawling_progress['is_running']:
            return jsonify({
                'success': False,
                'message': '이미 데이터 수집이 진행 중입니다.'
            }), 400

        # 백그라운드에서 크롤링 실행
        def run_crawling():
            def progress_callback(percent, message):
                crawling_progress.update({
                    'percent': percent,
                    'message': message
                })

            try:
                crawling_progress.update({
                    'is_running': True,
                    'percent': 0,
                    'message': '크롤링 준비 중...',
                    'start_time': datetime.now(),
                    'success': None,
                    'error_message': ''
                })

                crawler = TopRateCrawler(progress_callback=progress_callback)
                success = crawler.crawl_and_save(target_date)

                crawling_progress.update({
                    'is_running': False,
                    'end_time': datetime.now(),
                    'success': success,
                    'percent': 100 if success else crawling_progress['percent']
                })

                if success:
                    crawling_progress['message'] = '데이터 수집 완료!'
                else:
                    crawling_progress['message'] = '데이터 수집 실패'
                    crawling_progress['error_message'] = '크롤링 프로세스 실패'

            except Exception as e:
                crawling_progress.update({
                    'is_running': False,
                    'success': False,
                    'end_time': datetime.now(),
                    'message': '데이터 수집 오류 발생',
                    'error_message': str(e)
                })
                current_app.logger.error(f"크롤링 오류: {e}")

        # 백그라운드 스레드 시작
        thread = threading.Thread(target=run_crawling)
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'message': '데이터 수집을 시작했습니다.',
            'target_date': target_date
        })

    except Exception as e:
        current_app.logger.error(f"데이터 수집 시작 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'데이터 수집 시작 실패: {e}'
        }), 500


@top_rate_bp.route('/api/delete-old-data', methods=['POST'])
def delete_old_data():
    """오래된 데이터 삭제"""
    try:
        data = request.get_json()
        keep_days = data.get('keep_days', 30) if data else 30

        success = db.delete_old_data(keep_days)

        return jsonify({
            'success': success,
            'message': f'{keep_days}일 이전 데이터 삭제 완료' if success else '데이터 삭제 실패'
        })

    except Exception as e:
        current_app.logger.error(f"데이터 삭제 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'데이터 삭제 실패: {e}'
        }), 500


# ============= 디버깅/테스트 API =============

@top_rate_bp.route('/api/test-db')
def test_database():
    """데이터베이스 연결 테스트"""
    try:
        success = db.setup_crawling_database()

        return jsonify({
            'success': success,
            'message': '데이터베이스 연결 테스트 완료' if success else '데이터베이스 연결 실패',
            'trading_date': get_trading_date()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'데이터베이스 테스트 실패: {e}'
        }), 500


@top_rate_bp.route('/api/test-crawler')
def test_crawler():
    """크롤러 간단 테스트"""
    try:
        crawler = TopRateCrawler()

        # 테마 리스트만 간단히 테스트
        themes = crawler._get_theme_list()

        return jsonify({
            'success': True,
            'message': f'크롤러 테스트 완료',
            'theme_count': len(themes),
            'sample_themes': themes[:3] if themes else []
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'크롤러 테스트 실패: {e}'
        }), 500


@top_rate_bp.route('/api/system-info')
def get_system_info():
    """시스템 정보 조회"""
    try:
        global scheduler

        # 크롤링 진행상황
        progress_info = crawling_progress.copy()
        if progress_info.get('start_time'):
            progress_info['start_time'] = progress_info['start_time'].isoformat()
        if progress_info.get('end_time'):
            progress_info['end_time'] = progress_info['end_time'].isoformat()

        # 스케줄러 상태
        scheduler_info = {
            'initialized': scheduler is not None,
            'running': scheduler.is_running if scheduler else False,
            'next_runs': scheduler.get_next_run_times() if scheduler else {}
        }

        # 데이터베이스 정보
        available_dates = db.get_available_dates()
        current_date_status = db.get_crawling_status(get_trading_date())

        return jsonify({
            'success': True,
            'system_info': {
                'current_time': datetime.now().isoformat(),
                'trading_date': get_trading_date(),
                'crawling_progress': progress_info,
                'scheduler': scheduler_info,
                'database': {
                    'available_dates': available_dates,
                    'total_dates': len(available_dates),
                    'current_date_status': current_date_status
                }
            }
        })

    except Exception as e:
        current_app.logger.error(f"시스템 정보 조회 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'시스템 정보 조회 실패: {e}'
        }), 500


# ============= 에러 핸들러 =============

@top_rate_bp.errorhandler(404)
def not_found(error):
    """404 에러 핸들러"""
    return jsonify({
        'success': False,
        'message': '요청한 리소스를 찾을 수 없습니다.',
        'error_code': 404
    }), 404


@top_rate_bp.errorhandler(500)
def internal_error(error):
    """500 에러 핸들러"""
    current_app.logger.error(f"내부 서버 오류: {error}")
    return jsonify({
        'success': False,
        'message': '내부 서버 오류가 발생했습니다.',
        'error_code': 500
    }), 500


# ============= 컨텍스트 프로세서 =============

@top_rate_bp.context_processor
def inject_common_vars():
    """템플릿에 공통 변수 주입"""
    return {
        'module_name': '등락율상위분석',
        'module_version': '3.0.0',
        'current_trading_date': get_trading_date(),
        'api_prefix': '/top-rate/api'
    }


@top_rate_bp.route('/api/progress')
def get_progress():
    """크롤링 진행상황 조회"""
    try:
        progress_data = crawling_progress.copy()

        # datetime 객체를 문자열로 변환
        if progress_data.get('start_time'):
            progress_data['start_time'] = progress_data['start_time'].isoformat()
        if progress_data.get('end_time'):
            progress_data['end_time'] = progress_data['end_time'].isoformat()

        return jsonify(progress_data)

    except Exception as e:
        current_app.logger.error(f"진행상황 조회 실패: {e}")
        return jsonify({
            'is_running': False,
            'percent': 0,
            'message': '진행상황 조회 오류',
            'success': False,
            'error_message': str(e)
        })


@top_rate_bp.route('/api/stop-crawling', methods=['POST'])
def stop_crawling():
    """크롤링 중지 (구현 예정)"""
    try:
        # 실제로는 크롤링 프로세스를 안전하게 중지하는 로직 필요
        crawling_progress.update({
            'is_running': False,
            'message': '사용자에 의해 중지됨',
            'success': False
        })

        return jsonify({
            'success': True,
            'message': '크롤링이 중지되었습니다.'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'중지 실패: {e}'
        }), 500


# ============= 분석 결과 API =============

@top_rate_bp.route('/api/theme-summary')
def get_theme_summary():
    """테마별 요약 데이터 조회"""
    try:
        date_str = request.args.get('date', get_trading_date())

        # 데이터 존재 확인
        table_name = get_table_name(date_str)
        if not db.check_table_exists(table_name):
            return jsonify({
                'success': False,
                'message': f'{date_str} 데이터가 없습니다. 먼저 데이터를 수집해주세요.',
                'themes': []
            })

        # 테마 요약 조회
        themes = db.get_theme_summary(date_str)

        # 아이콘 매핑 (확장 가능)
        icon_mapping = {
            '증권': '🏦', 'AI반도체': '🤖', '2차전지': '🔋',
            '바이오': '🧬', '게임': '🎮', '자동차': '🚗',
            '화학': '⚗️', '조선': '🚢', '항공': '✈️',
            '건설': '🏗️', '통신': '📡', '은행': '🏛️'
        }

        # 아이콘 추가 및 데이터 정리
        for theme in themes:
            theme['icon'] = icon_mapping.get(theme['theme_name'], '📊')
            theme['rising_ratio'] = (theme['rising_stocks'] / theme['stock_count'] * 100) if theme[
                                                                                                 'stock_count'] > 0 else 0

        return jsonify({
            'success': True,
            'date': date_str,
            'themes': themes,
            'total_themes': len(themes)
        })

    except Exception as e:
        current_app.logger.error(f"테마 요약 조회 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'테마 요약 조회 실패: {e}',
            'themes': []
        }), 500


@top_rate_bp.route('/api/theme-detail')
def get_theme_detail():
    """특정 테마 상세정보 조회"""
    try:
        date_str = request.args.get('date', get_trading_date())
        theme_name = request.args.get('theme_name')

        if not theme_name:
            return jsonify({
                'success': False,
                'message': '테마명이 필요합니다.'
            }), 400

        # 테마 상세정보 조회
        theme_detail = db.get_theme_detail(date_str, theme_name)

        if not theme_detail:
            return jsonify({
                'success': False,
                'message': f'{theme_name} 테마 정보를 찾을 수 없습니다.'
            })

        return jsonify({
            'success': True,
            'theme_detail': theme_detail
        })

    except Exception as e:
        current_app.logger.error(f"테마 상세정보 조회 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'테마 상세정보 조회 실패: {e}'
        }), 500


@top_rate_bp.route('/api/crawling-status')
def get_crawling_status():
    """크롤링 상태 정보 조회"""
    try:
        date_str = request.args.get('date', get_trading_date())
        status = db.get_crawling_status(date_str)

        return jsonify({
            'success': True,
            'date': date_str,
            'status': status
        })

    except Exception as e:
        current_app.logger.error(f"크롤링 상태 조회 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'상태 조회 실패: {e}'
        }), 500


# ============= 스케줄 관리 API =============

@top_rate_bp.route('/api/schedules')
def get_schedules():
    """스케줄 목록 조회"""
    try:
        global scheduler
        if not scheduler:
            return jsonify({
                'success': False,
                'message': '스케줄러가 초기화되지 않았습니다.',
                'schedules': []
            })

        schedules = scheduler.get_schedules()

        return jsonify({
            'success': True,
            'schedules': schedules
        })

    except Exception as e:
        current_app.logger.error(f"스케줄 목록 조회 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'스케줄 조회 실패: {e}',
            'schedules': []
        }), 500


@top_rate_bp.route('/api/toggle-schedule', methods=['POST'])
def toggle_schedule():
    """스케줄 활성화/비활성화"""
    try:
        data = request.get_json()
        schedule_time = data.get('time')  # "09:15" 형식

        if not schedule_time:
            return jsonify({
                'success': False,
                'message': '스케줄 시간이 필요합니다.'
            }), 400

        global scheduler
        if not scheduler:
            return jsonify({
                'success': False,
                'message': '스케줄러가 초기화되지 않았습니다.'
            }), 500

        # 시간 파싱
        try:
            hour, minute = map(int, schedule_time.split(':'))
            job_id = f"auto_crawling_{hour:02d}_{minute:02d}"
        except ValueError:
            return jsonify({
                'success': False,
                'message': '잘못된 시간 형식입니다.'
            }), 400

        # 스케줄이 존재하는지 확인
        schedules = scheduler.get_schedules()
        existing_schedule = next((s for s in schedules if s['id'] == job_id), None)

        if existing_schedule:
            # 기존 스케줄 토글
            enabled = scheduler.toggle_schedule(job_id)
            action = "활성화" if enabled else "비활성화"
        else:
            # 새 스케줄 추가
            new_job_id = scheduler.add_schedule(hour, minute, f"{hour:02d}:{minute:02d}")
            enabled = bool(new_job_id)
            action = "추가" if enabled else "추가 실패"

        return jsonify({
            'success': enabled is not False,
            'message': f'스케줄이 {action}되었습니다.',
            'enabled': enabled
        })

    except Exception as e:
        current_app.logger.error(f"스케줄 토글 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'스케줄 토글 실패: {e}'
        }), 500


@top_rate_bp.route('/api/manual-crawling', methods=['POST'])
def manual_crawling():
    """수동 크롤링 실행"""
    try:
        data = request.get_json()
        target_date = data.get('date') if data else None

        global scheduler
        if not scheduler:
            return jsonify({
                'success': False,
                'message': '스케줄러가 초기화되지 않았습니다.'
            }), 500

        # 수동 크롤링 실행
        success = scheduler.run_manual_crawling(target_date)

        return jsonify({
            'success': success,
            'message': '수동 크롤링이 완료되었습니다.' if success else '수동 크롤링이 실패했습니다.'
        })

    except Exception as e:
        current_app.logger.error(f"수동 크롤링 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'수동 크롤링 실패: {e}'
        }), 500


# ============= 유틸리티 API =============

@top_rate_bp.route('/api/available-dates')
def get_available_dates():
    """수집된 데이터가 있는 날짜 목록"""
    try:
        dates = db.get_available_dates()

        return jsonify({
            'success': True,
            'dates': dates,
            'current_trading_date': get_trading_date()
        })

    except Exception as e:
        current_app.logger.error(f"날짜 목록 조회 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'날짜 조회 실패: {e}',
            'dates': []})