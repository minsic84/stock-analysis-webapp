#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, send_from_directory
from config import get_config
import os
import logging
import traceback  # 디버깅용 추가



def create_app():
    """Flask 애플리케이션 팩토리"""
    app = Flask(__name__)

    # 환경별 설정 로드
    config_class = get_config()
    app.config.from_object(config_class)

    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 블루프린트 등록
    register_blueprints(app)

    # 기본 라우트
    @app.route('/')
    def index():
        """메인 페이지"""
        return render_template('index.html')

    # favicon 처리 (404 방지)
    @app.route('/favicon.ico')
    def favicon():
        """favicon 요청 처리"""
        return send_from_directory(
            os.path.join(app.root_path, 'static'),
            'favicon.ico',
            mimetype='image/vnd.microsoft.icon'
        )

    # 에러 핸들러들
    @app.errorhandler(404)
    def not_found(error):
        """404 에러 핸들러"""
        try:
            return render_template('404.html'), 404
        except Exception:
            return '''
            <h1>404 - 페이지를 찾을 수 없습니다</h1>
            <p><a href="/">홈으로 돌아가기</a></p>
            ''', 404

    @app.errorhandler(500)
    def internal_error(error):
        """500 에러 핸들러"""
        try:
            return render_template('500.html'), 500
        except Exception:
            return '''
            <h1>500 - 서버 오류</h1>
            <p>서버에서 오류가 발생했습니다.</p>
            <p><a href="/">홈으로 돌아가기</a></p>
            ''', 500

    return app


def register_blueprints(app):
    """블루프린트 등록"""

    # 등락율상위분석 모듈 (개별 등록)
    try:
        from modules.top_rate_analysis import register_module
        success = register_module(app)
        if success:
            app.logger.info("✅ 등락율상위분석 모듈 등록 완료")
        else:
            app.logger.warning("⚠️ 등락율상위분석 모듈 등록 실패")
    except ImportError as e:
        app.logger.error(f"❌ 등락율상위분석 모듈 import 실패: {e}")
        app.logger.info("🔍 다음 사항을 확인해주세요:")
        app.logger.info("   1. modules/top_rate_analysis/ 폴더가 존재하는가?")
        app.logger.info("   2. modules/top_rate_analysis/__init__.py 파일이 있는가?")
        app.logger.info("   3. 모든 필수 파일들이 생성되었는가?")
    except Exception as e:
        app.logger.error(f"❌ 등락율상위분석 모듈 등록 중 오류: {e}")
        app.logger.error(f"   스택 트레이스: {traceback.format_exc()}")  # 상세 오류 정보


if __name__ == '__main__':
    app = create_app()

    # 정적 파일 디렉토리 확인
    static_dir = os.path.join(app.root_path, 'static')
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
        app.logger.info(f"static 디렉토리 생성: {static_dir}")

    print("🚀 Flask 주식분석 웹앱 시작!")
    print("📊 등락율상위분석 모듈: /top-rate")
    print("🌐 메인 페이지: http://localhost:5000")

    app.run(
        debug=app.config['DEBUG'],
        host='0.0.0.0',
        port=5000
    )