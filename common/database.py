#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pymysql
import logging
from flask import current_app
from typing import List, Dict, Optional


class DatabaseManager:
    """데이터베이스 관리 클래스 (기존 방식과 동일)"""

    def __init__(self):
        self.config = None
        self.schemas = None

    def init_app(self, app):
        """Flask 앱 초기화"""
        self.config = app.config['DB_CONFIG']
        self.schemas = app.config['SCHEMAS']

        # 연결 테스트
        try:
            self.test_connection()
            app.logger.info("데이터베이스 연결 성공")
        except Exception as e:
            app.logger.error(f"데이터베이스 연결 실패: {e}")
            # 일단 경고만 하고 계속 진행 (개발 단계)
            app.logger.warning("DB 연결 없이 계속 진행합니다")

    def test_connection(self):
        """연결 테스트"""
        conn = pymysql.connect(**self.config)
        try:
            with conn.cursor() as cursor:
                cursor.execute('SELECT 1')
        finally:
            conn.close()

    def get_connection(self, schema_name='main'):
        """데이터베이스 연결 반환"""
        config = self.config.copy()
        config['database'] = self.schemas.get(schema_name, self.schemas['main'])
        return pymysql.connect(**config)

    def execute_query(self, query: str, params: tuple = None, schema_name: str = 'main') -> List[Dict]:
        """쿼리 실행"""
        try:
            conn = self.get_connection(schema_name)
            try:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(query, params)

                    if query.strip().upper().startswith('SELECT'):
                        return cursor.fetchall()
                    else:
                        conn.commit()
                        return []
            finally:
                conn.close()

        except Exception as e:
            logging.error(f"쿼리 실행 오류: {e}")
            raise

    def check_table_exists(self, table_name: str, schema_name: str = 'main') -> bool:
        """테이블 존재 여부 확인"""
        try:
            database_name = self.schemas.get(schema_name, self.schemas['main'])
            query = """
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_schema = %s AND table_name = %s
            """

            result = self.execute_query(query, (database_name, table_name))
            return result[0]['count'] > 0 if result else False

        except Exception as e:
            logging.error(f"테이블 존재 확인 실패: {e}")
            return False


# 전역 인스턴스
db_manager = DatabaseManager()


def init_db(app):
    """데이터베이스 초기화 (기존 방식과 동일)"""
    db_manager.init_app(app)


def get_stock_table_name(stock_code: str, table_type: str = 'daily') -> str:
    """종목코드에 따른 테이블명 생성"""
    if table_type == 'daily':
        return f"daily_prices_{stock_code}"
    elif table_type == 'supply':
        return f"supply_demand_{stock_code}"
    else:
        raise ValueError(f"지원하지 않는 테이블 타입: {table_type}")


def execute_query(query: str, schema_name: str = 'main', params: tuple = None) -> List[Dict]:
    """쿼리 실행 헬퍼 함수"""
    return db_manager.execute_query(query, params, schema_name)


def check_table_exists(table_name: str, schema_name: str = 'main') -> bool:
    """테이블 존재 여부 확인 헬퍼 함수"""
    return db_manager.check_table_exists(table_name, schema_name)