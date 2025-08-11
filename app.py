#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, jsonify
from config import Config, get_config
from common.database import init_db
import os


def create_app():
    """Flask 애플리케이션 팩토리"""
    app = Flask(__name__)

    # 환경별 설정 로드
    config_class = get_config()
    app.config.from_object(config_class)

    # 데이터베이스 초기화
    init_db(app)

    # 블루프린트 등록
    register_blueprints(app)

    # 기본 라우트
    @app.route('/')
    def index():
        """메인 페이지"""
        return render_template('index.html')

    # 에러 핸들러
    @app.errorhandler(404)
    def not_found(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('500.html'), 500

    return app


def register_blueprints(app):
    """블루프린트 등록"""
    # 등락율상위분석 모듈
    from modules.top_rate_analysis.routes import top_rate_bp
    app.register_blueprint(top_rate_bp, url_prefix='/top-rate')

    # 추후 다른 모듈들 추가 가능
    # from modules.stock_setting.routes import stock_setting_bp
    # app.register_blueprint(stock_setting_bp, url_prefix='/stock-setting')


if __name__ == '__main__':
    app = create_app()
    app.run(
        debug=app.config['DEBUG'],
        host='0.0.0.0',
        port=5000
    )