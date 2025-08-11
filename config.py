import os
from datetime import timedelta
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


class Config:
    """기본 설정 클래스"""
    # Flask 기본 설정
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')

    # 데이터베이스 설정 (기존 방식과 동일)
    DB_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 3306)),
        'user': os.getenv('DB_USER', 'stock_user'),
        'password': os.getenv('DB_PASSWORD', 'StockPass2025!'),
        'charset': 'utf8mb4',
        'autocommit': True
    }

    # 스키마 설정 (기존 방식과 동일)
    SCHEMAS = {
        'daily': 'realtime_daily_db',
        'program': 'realtime_program_db',
        'index': 'realtime_index_db',
        'main': 'stock_trading_db',
        'real_program': 'realtime_program_db',
        'real_index': 'realtime_index_db'
    }

    # OpenAI API 설정
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

    # 세션 설정
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

    # 업로드 설정
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

    # 개발/운영 환경 구분
    ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = ENV == 'development'


class DevelopmentConfig(Config):
    """개발환경 설정"""
    DEBUG = True


class ProductionConfig(Config):
    """운영환경 설정"""
    DEBUG = False

    # 보안 설정 강화
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


# 기본 설정 (개발환경)
def get_config():
    """환경에 따른 설정 반환"""
    env = os.getenv('FLASK_ENV', 'development')
    if env == 'production':
        return ProductionConfig
    else:
        return DevelopmentConfig