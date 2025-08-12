#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pymysql
import logging
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


class TopRateDatabase:
    """등락율상위분석 전용 데이터베이스 클래스"""

    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'charset': 'utf8mb4',
            'autocommit': True
        }
        self.crawling_db = 'crawling_db'

    def get_connection(self, database: str = None) -> pymysql.Connection:
        """데이터베이스 연결 반환"""
        config = self.db_config.copy()
        if database:
            config['database'] = database
        return pymysql.connect(**config)

    def setup_crawling_database(self):
        """크롤링 데이터베이스 및 스키마 설정"""
        try:
            connection = self.get_connection()
            cursor = connection.cursor()

            # crawling_db 생성
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS {self.crawling_db} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            logging.info(f"✅ {self.crawling_db} 데이터베이스 생성/확인 완료")

            cursor.close()
            connection.close()
            return True

        except Exception as e:
            logging.error(f"데이터베이스 설정 실패: {e}")
            return False

    def setup_theme_table(self, date: str) -> str:
        """테마 크롤링 테이블 설정 (덮어쓰기)"""
        try:
            table_name = f"theme_{date.replace('-', '')}"

            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor()

            # 기존 테이블 삭제
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            logging.info(f"🗑️ 기존 {table_name} 테이블 삭제")

            # 새 테이블 생성
            create_table_sql = f"""
            CREATE TABLE {table_name} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                stock_code VARCHAR(10) NOT NULL,
                stock_name VARCHAR(100) NOT NULL,
                themes JSON NOT NULL,
                price INT DEFAULT 0,
                change_rate DECIMAL(5,2) DEFAULT 0,
                volume BIGINT DEFAULT 0,
                news JSON NOT NULL,
                theme_stocks JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_stock_code (stock_code),
                INDEX idx_stock_name (stock_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """

            cursor.execute(create_table_sql)
            logging.info(f"✅ {table_name} 테이블 생성 완료")

            cursor.close()
            connection.close()
            return table_name

        except Exception as e:
            logging.error(f"테마 테이블 설정 실패: {e}")
            raise

    def save_theme_data(self, table_name: str, theme_data: Dict) -> bool:
        """테마 크롤링 데이터 저장"""
        try:
            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor()

            # 종목별로 데이터 정리 (중복 제거)
            stock_data = {}

            for theme_name, theme_info in theme_data.items():
                theme_stocks = theme_info['theme_stocks']

                for stock in theme_info['stocks']:
                    stock_code = stock['code']

                    if stock_code not in stock_data:
                        stock_data[stock_code] = {
                            'stock_code': stock_code,
                            'stock_name': stock['name'],
                            'themes': [],
                            'price': stock['price'],
                            'change_rate': stock['change_rate'],
                            'volume': stock['volume'],
                            'news': stock['news'],
                            'theme_stocks': {}
                        }

                    # 테마 추가 (중복 방지)
                    if theme_name not in stock_data[stock_code]['themes']:
                        stock_data[stock_code]['themes'].append(theme_name)

                    # 해당 테마의 모든 종목 정보 추가
                    stock_data[stock_code]['theme_stocks'][theme_name] = theme_stocks

            # DB에 삽입
            insert_sql = f"""
            INSERT INTO {table_name} (stock_code, stock_name, themes, price, change_rate, volume, news, theme_stocks)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            success_count = 0
            for stock_code, stock_info in stock_data.items():
                try:
                    cursor.execute(insert_sql, (
                        stock_info['stock_code'],
                        stock_info['stock_name'],
                        json.dumps(stock_info['themes'], ensure_ascii=False),
                        stock_info['price'],
                        stock_info['change_rate'],
                        stock_info['volume'],
                        json.dumps(stock_info['news'], ensure_ascii=False),
                        json.dumps(stock_info['theme_stocks'], ensure_ascii=False)
                    ))
                    success_count += 1

                except Exception as e:
                    logging.error(f"{stock_info['stock_name']} 저장 실패: {e}")

            cursor.close()
            connection.close()

            logging.info(f"✅ 테마 데이터 저장 완료: {success_count}/{len(stock_data)}개 종목")
            return True

        except Exception as e:
            logging.error(f"테마 데이터 저장 실패: {e}")
            return False

    def get_theme_data(self, date: str) -> List[Dict]:
        """특정 날짜의 테마 데이터 조회"""
        try:
            table_name = f"theme_{date.replace('-', '')}"

            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor(pymysql.cursors.DictCursor)

            query = f"""
            SELECT * FROM {table_name}
            ORDER BY change_rate DESC
            """

            cursor.execute(query)
            result = cursor.fetchall()

            cursor.close()
            connection.close()

            return result if result else []

        except Exception as e:
            logging.error(f"테마 데이터 조회 실패: {e}")
            return []

    def check_table_exists(self, table_name: str) -> bool:
        """테이블 존재 여부 확인"""
        try:
            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor()

            query = """
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_schema = %s AND table_name = %s
            """

            cursor.execute(query, (self.crawling_db, table_name))
            result = cursor.fetchone()

            cursor.close()
            connection.close()

            return result[0] > 0 if result else False

        except Exception as e:
            logging.error(f"테이블 존재 확인 실패: {e}")
            return False

    def setup_ai_analysis_table(self, date: str) -> str:
        """AI 분석 테이블 설정 (덮어쓰기)"""
        try:
            table_name = f"ai_analysis_{date.replace('-', '')}"

            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor()

            # 기존 테이블 삭제
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            logging.info(f"🗑️ 기존 {table_name} 테이블 삭제")

            # 새 테이블 생성
            create_table_sql = f"""
            CREATE TABLE {table_name} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                stock_code VARCHAR(10) NOT NULL,
                stock_name VARCHAR(100) NOT NULL,
                primary_theme VARCHAR(100) NOT NULL,
                issue_type ENUM('THEME', 'INDIVIDUAL') NOT NULL,
                issue_category VARCHAR(50),
                ai_score INT DEFAULT 0,
                confidence_level DECIMAL(3,2) DEFAULT 0.50,
                key_factors JSON NOT NULL,
                news_summary TEXT,
                ai_reasoning TEXT,
                investment_opinion ENUM('강력매수', '매수', '보유', '관망', '매도') DEFAULT '관망',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_stock_code (stock_code),
                INDEX idx_issue_type (issue_type),
                INDEX idx_ai_score (ai_score DESC)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """

            cursor.execute(create_table_sql)
            logging.info(f"✅ {table_name} 테이블 생성 완료")

            cursor.close()
            connection.close()
            return table_name

        except Exception as e:
            logging.error(f"AI 분석 테이블 설정 실패: {e}")
            raise

    def save_ai_analysis(self, table_name: str, analysis_data: List[Dict]) -> bool:
        """AI 분석 결과 저장"""
        try:
            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor()

            insert_sql = f"""
            INSERT INTO {table_name} 
            (stock_code, stock_name, primary_theme, issue_type, issue_category, ai_score, 
             confidence_level, key_factors, news_summary, ai_reasoning, investment_opinion)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            success_count = 0
            for analysis in analysis_data:
                try:
                    cursor.execute(insert_sql, (
                        analysis['stock_code'],
                        analysis['stock_name'],
                        analysis['primary_theme'],
                        analysis['issue_type'],
                        analysis.get('issue_category', ''),
                        analysis['ai_score'],
                        analysis['confidence_level'],
                        json.dumps(analysis['key_factors'], ensure_ascii=False),
                        analysis.get('news_summary', ''),
                        analysis.get('ai_reasoning', ''),
                        analysis['investment_opinion']
                    ))
                    success_count += 1

                except Exception as e:
                    logging.error(f"AI 분석 저장 실패 ({analysis.get('stock_name', 'Unknown')}): {e}")

            cursor.close()
            connection.close()

            logging.info(f"✅ AI 분석 저장 완료: {success_count}/{len(analysis_data)}개 종목")
            return True

        except Exception as e:
            logging.error(f"AI 분석 저장 실패: {e}")
            return False

    def get_ai_analysis(self, date: str) -> List[Dict]:
        """AI 분석 결과 조회"""
        try:
            table_name = f"ai_analysis_{date.replace('-', '')}"

            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor(pymysql.cursors.DictCursor)

            query = f"""
            SELECT * FROM {table_name}
            ORDER BY ai_score DESC
            """

            cursor.execute(query)
            result = cursor.fetchall()

            cursor.close()
            connection.close()

            return result if result else []

        except Exception as e:
            logging.error(f"AI 분석 조회 실패: {e}")
            return []

    def get_theme_analysis_progress(self, theme_date: str, ai_date: str) -> Dict:
        """테마별 AI 분석 진행률 조회"""
        try:
            theme_table = f"theme_{theme_date.replace('-', '')}"
            ai_table = f"ai_analysis_{ai_date.replace('-', '')}"

            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor(pymysql.cursors.DictCursor)

            # 테마별 통계 조회
            query = f"""
            SELECT 
                JSON_UNQUOTE(JSON_EXTRACT(themes, '$[0]')) as theme_name,
                COUNT(DISTINCT t.stock_code) as total_stocks,
                COUNT(DISTINCT ai.stock_code) as analyzed_stocks
            FROM {theme_table} t
            LEFT JOIN {ai_table} ai ON t.stock_code = ai.stock_code
            GROUP BY JSON_UNQUOTE(JSON_EXTRACT(themes, '$[0]'))
            ORDER BY total_stocks DESC
            """

            cursor.execute(query)
            result = cursor.fetchall()

            cursor.close()
            connection.close()

            return result if result else []

        except Exception as e:
            logging.error(f"분석 진행률 조회 실패: {e}")
            return []