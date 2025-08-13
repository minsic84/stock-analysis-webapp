#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
개선된 AI 분석 데이터베이스 스키마
상세 분석 정보를 위한 컬럼 추가
"""

import pymysql
import logging
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
import os
from dotenv import load_dotenv

load_dotenv()


class EnhancedTopRateDatabase:
    """개선된 등락율상위분석 전용 데이터베이스 클래스"""

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

    def setup_enhanced_ai_analysis_table(self, date: str) -> str:
        """개선된 AI 분석 테이블 설정 (상세 컬럼 추가)"""
        try:
            table_name = f"ai_analysis_{date.replace('-', '')}"

            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor()

            # 기존 테이블 삭제
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            logging.info(f"🗑️ 기존 {table_name} 테이블 삭제")

            # 개선된 테이블 생성
            create_table_sql = f"""
            CREATE TABLE {table_name} (
                id INT AUTO_INCREMENT PRIMARY KEY,

                -- 기본 정보
                stock_code VARCHAR(10) NOT NULL,
                stock_name VARCHAR(100) NOT NULL,
                primary_theme VARCHAR(100) NOT NULL,

                -- 분석 결과
                issue_type ENUM('THEME', 'INDIVIDUAL') NOT NULL,
                issue_category VARCHAR(50),
                ai_score INT DEFAULT 0,
                confidence_level DECIMAL(3,2) DEFAULT 0.50,
                investment_opinion ENUM('강력매수', '매수', '보유', '관심', '관망', '매도') DEFAULT '관망',

                -- 상세 점수 분해 (신규 추가)
                keyword_score INT DEFAULT 0,
                combo_bonus INT DEFAULT 0,
                market_score INT DEFAULT 0,
                sustainability_score INT DEFAULT 0,
                total_calculated_score INT DEFAULT 0,

                -- 상세 분석 정보 (신규 추가)
                found_keywords JSON,
                found_categories JSON,
                analysis_summary TEXT,

                -- 기존 필드
                key_factors JSON NOT NULL,
                news_summary TEXT,
                ai_reasoning TEXT,

                -- 메타 정보
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

                -- 인덱스
                INDEX idx_stock_code (stock_code),
                INDEX idx_issue_type (issue_type),
                INDEX idx_ai_score (ai_score DESC),
                INDEX idx_investment_opinion (investment_opinion),
                INDEX idx_total_score (total_calculated_score DESC),
                INDEX idx_keyword_score (keyword_score DESC)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """

            cursor.execute(create_table_sql)
            logging.info(f"✅ 개선된 {table_name} 테이블 생성 완료")

            # 테이블 구조 확인 및 출력
            cursor.execute(f"DESCRIBE {table_name}")
            columns = cursor.fetchall()

            logging.info(f"\n📋 {table_name} 테이블 구조:")
            for col in columns:
                col_name, col_type, null, key, default, extra = col
                logging.info(f"   {col_name}: {col_type} {extra if extra else ''}")

            cursor.close()
            connection.close()
            return table_name

        except Exception as e:
            logging.error(f"AI 분석 테이블 설정 실패: {e}")
            raise

    def save_enhanced_ai_analysis(self, table_name: str, analysis_data: List[Dict]) -> bool:
        """개선된 AI 분석 결과 저장 (상세 정보 포함)"""
        try:
            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor()

            insert_sql = f"""
            INSERT INTO {table_name} 
            (stock_code, stock_name, primary_theme, issue_type, issue_category, 
             ai_score, confidence_level, investment_opinion,
             keyword_score, combo_bonus, market_score, sustainability_score, total_calculated_score,
             found_keywords, found_categories, analysis_summary,
             key_factors, news_summary, ai_reasoning)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                        analysis.get('confidence_level', 0.5),
                        analysis['investment_opinion'],

                        # 상세 점수 정보
                        analysis.get('keyword_score', 0),
                        analysis.get('combo_bonus', 0),
                        analysis.get('market_score', 0),
                        analysis.get('sustainability_score', 0),
                        analysis.get('total_calculated_score', 0),

                        # 상세 분석 정보
                        json.dumps(analysis.get('found_keywords', []), ensure_ascii=False),
                        json.dumps(analysis.get('found_categories', []), ensure_ascii=False),
                        analysis.get('analysis_summary', ''),

                        # 기존 필드
                        json.dumps(analysis.get('key_factors', []), ensure_ascii=False),
                        analysis.get('news_summary', ''),
                        analysis.get('ai_reasoning', '')
                    ))
                    success_count += 1

                except Exception as e:
                    logging.error(f"AI 분석 저장 실패 ({analysis.get('stock_name', 'Unknown')}): {e}")

            cursor.close()
            connection.close()

            logging.info(f"✅ 개선된 AI 분석 저장 완료: {success_count}/{len(analysis_data)}개 종목")
            return True

        except Exception as e:
            logging.error(f"AI 분석 저장 실패: {e}")
            return False

    def get_enhanced_ai_analysis(self, date: str) -> List[Dict]:
        """개선된 AI 분석 결과 조회 (상세 정보 포함)"""
        try:
            table_name = f"ai_analysis_{date.replace('-', '')}"

            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor(pymysql.cursors.DictCursor)

            query = f"""
            SELECT 
                stock_code, stock_name, primary_theme, issue_type, issue_category,
                ai_score, confidence_level, investment_opinion,
                keyword_score, combo_bonus, market_score, sustainability_score, total_calculated_score,
                found_keywords, found_categories, analysis_summary,
                key_factors, news_summary, ai_reasoning,
                created_at
            FROM {table_name}
            ORDER BY ai_score DESC, total_calculated_score DESC
            """

            cursor.execute(query)
            result = cursor.fetchall()

            cursor.close()
            connection.close()

            return result if result else []

        except Exception as e:
            logging.error(f"AI 분석 조회 실패: {e}")
            return []

    def get_analysis_statistics(self, date: str) -> Dict:
        """분석 통계 조회"""
        try:
            table_name = f"ai_analysis_{date.replace('-', '')}"

            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor(pymysql.cursors.DictCursor)

            # 기본 통계
            cursor.execute(f"""
            SELECT 
                COUNT(*) as total_count,
                AVG(ai_score) as avg_score,
                AVG(keyword_score) as avg_keyword_score,
                AVG(combo_bonus) as avg_combo_bonus,
                AVG(market_score) as avg_market_score,
                AVG(sustainability_score) as avg_sustainability_score
            FROM {table_name}
            """)

            basic_stats = cursor.fetchone()

            # 투자 의견별 통계
            cursor.execute(f"""
            SELECT investment_opinion, COUNT(*) as count
            FROM {table_name}
            GROUP BY investment_opinion
            ORDER BY count DESC
            """)

            opinion_stats = cursor.fetchall()

            # 이슈 타입별 통계
            cursor.execute(f"""
            SELECT issue_type, COUNT(*) as count, AVG(ai_score) as avg_score
            FROM {table_name}
            GROUP BY issue_type
            """)

            issue_type_stats = cursor.fetchall()

            # 고득점 종목 (80점 이상)
            cursor.execute(f"""
            SELECT stock_name, ai_score, investment_opinion, total_calculated_score
            FROM {table_name}
            WHERE ai_score >= 80
            ORDER BY ai_score DESC
            LIMIT 10
            """)

            high_score_stocks = cursor.fetchall()

            cursor.close()
            connection.close()

            return {
                'basic_stats': basic_stats,
                'opinion_stats': opinion_stats,
                'issue_type_stats': issue_type_stats,
                'high_score_stocks': high_score_stocks
            }

        except Exception as e:
            logging.error(f"분석 통계 조회 실패: {e}")
            return {}

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

    def migrate_existing_table(self, date: str) -> bool:
        """기존 테이블을 개선된 스키마로 마이그레이션"""
        try:
            table_name = f"ai_analysis_{date.replace('-', '')}"

            if not self.check_table_exists(table_name):
                logging.info(f"테이블 {table_name}이 존재하지 않습니다")
                return False

            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor()

            # 새 컬럼들 추가
            new_columns = [
                "ADD COLUMN keyword_score INT DEFAULT 0",
                "ADD COLUMN combo_bonus INT DEFAULT 0",
                "ADD COLUMN market_score INT DEFAULT 0",
                "ADD COLUMN sustainability_score INT DEFAULT 0",
                "ADD COLUMN total_calculated_score INT DEFAULT 0",
                "ADD COLUMN found_keywords JSON",
                "ADD COLUMN found_categories JSON",
                "ADD COLUMN analysis_summary TEXT",
                "ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
            ]

            for column_sql in new_columns:
                try:
                    cursor.execute(f"ALTER TABLE {table_name} {column_sql}")
                    logging.info(f"컬럼 추가: {column_sql}")
                except Exception as e:
                    logging.warning(f"컬럼 추가 실패 (이미 존재할 수 있음): {e}")

            # 새 인덱스 추가
            new_indexes = [
                f"CREATE INDEX idx_total_score ON {table_name} (total_calculated_score DESC)",
                f"CREATE INDEX idx_keyword_score ON {table_name} (keyword_score DESC)"
            ]

            for index_sql in new_indexes:
                try:
                    cursor.execute(index_sql)
                    logging.info(f"인덱스 추가: {index_sql}")
                except Exception as e:
                    logging.warning(f"인덱스 추가 실패 (이미 존재할 수 있음): {e}")

            cursor.close()
            connection.close()

            logging.info(f"✅ {table_name} 테이블 마이그레이션 완료")
            return True

        except Exception as e:
            logging.error(f"테이블 마이그레이션 실패: {e}")
            return False


# 기존 database.py의 TopRateDatabase 클래스 확장
class TopRateDatabase:
    """기존 TopRateDatabase 클래스에 개선된 메서드 추가"""

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
        """크롤링 데이터베이스 설정"""
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS {self.crawling_db} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.close()
            connection.close()
            return True
        except Exception as e:
            logging.error(f"데이터베이스 설정 실패: {e}")
            return False

    def setup_ai_analysis_table(self, date: str) -> str:
        """개선된 AI 분석 테이블 설정 (기존 메서드를 개선된 버전으로 대체)"""
        enhanced_db = EnhancedTopRateDatabase()
        return enhanced_db.setup_enhanced_ai_analysis_table(date)

    def save_ai_analysis(self, table_name: str, analysis_data: List[Dict]) -> bool:
        """개선된 AI 분석 결과 저장 (기존 메서드를 개선된 버전으로 대체)"""
        enhanced_db = EnhancedTopRateDatabase()
        return enhanced_db.save_enhanced_ai_analysis(table_name, analysis_data)

    def get_ai_analysis(self, date: str) -> List[Dict]:
        """개선된 AI 분석 결과 조회 (기존 메서드를 개선된 버전으로 대체)"""
        enhanced_db = EnhancedTopRateDatabase()
        return enhanced_db.get_enhanced_ai_analysis(date)

    def get_theme_data(self, date: str) -> List[Dict]:
        """테마 데이터 조회 (기존 메서드 유지)"""
        try:
            table_name = f"theme_{date.replace('-', '')}"
            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor(pymysql.cursors.DictCursor)

            query = f"SELECT * FROM {table_name} ORDER BY change_rate DESC"
            cursor.execute(query)
            result = cursor.fetchall()

            cursor.close()
            connection.close()
            return result if result else []

        except Exception as e:
            logging.error(f"테마 데이터 조회 실패: {e}")
            return []

    def check_table_exists(self, table_name: str) -> bool:
        """테이블 존재 여부 확인 (기존 메서드 유지)"""
        enhanced_db = EnhancedTopRateDatabase()
        return enhanced_db.check_table_exists(table_name)