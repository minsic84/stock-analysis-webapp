def register_module(app):
    """종목설정 모듈을 앱에 등록"""
    from .routes import stock_setting_bp
    app.register_blueprint(stock_setting_bp)