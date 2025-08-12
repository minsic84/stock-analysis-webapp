#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, jsonify, send_from_directory
from config import Config, get_config
from common.database import init_db
import os
import logging


def create_app():
    """Flask 애플리케이션 팩토리"""
    app = Flask(__name__)

    # 환경별 설정 로드
    config_class = get_config()
    app.config.from_object(config_class)

    # 로깅 설정
    logging.basicConfig(level=logging.INFO)

    # 데이터베이스 초기화 (오류가 있어도 계속 진행)
    try:
        init_db(app)
    except Exception as e:
        app.logger.warning(f"데이터베이스 초기화 실패 (개발 모드에서 계속 진행): {e}")

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
            # 템플릿 로드 실패시 기본 응답
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
            # 템플릿 로드 실패시 기본 응답
            return '''
            <h1>500 - 서버 오류</h1>
            <p>서버에서 오류가 발생했습니다.</p>
            <p><a href="/">홈으로 돌아가기</a></p>
            ''', 500

    return app


def register_blueprints(app):
    """블루프린트 등록"""
    try:
        # 등락율상위분석 모듈
        from modules.top_rate_analysis.routes import top_rate_bp
        app.register_blueprint(top_rate_bp, url_prefix='/top-rate')
        app.logger.info("등락율상위분석 모듈 등록 완료")
    except Exception as e:
        app.logger.error(f"등락율상위분석 모듈 등록 실패: {e}")

    # 추후 다른 모듈들 추가 가능
    # try:
    #     from modules.stock_setting.routes import stock_setting_bp
    #     app.register_blueprint(stock_setting_bp, url_prefix='/stock-setting')
    # except Exception as e:
    #     app.logger.error(f"종목설정 모듈 등록 실패: {e}")


if __name__ == '__main__':
    app = create_app()

    # 정적 파일 디렉토리 확인
    static_dir = os.path.join(app.root_path, 'static')
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
        app.logger.info(f"static 디렉토리 생성: {static_dir}")

    app.run(
        debug=app.config['DEBUG'],
        host='0.0.0.0',
        port=5000
    )