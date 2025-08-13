#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
등락율상위분석 전용 데이터베이스 클래스
- 완전 독립적인 DB 연결 및 관리
- 날짜별 테이블 자동 생성/관리
- 크롤링 데이터 저장 및 조회
"""

import pymysql
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import os
from .utils import get_trading_date, get_table_name


class TopRateDatabase:
    """등락율상위분석 전용 데이터베이스 클래스"""

    def __init__(self):
        """데이터베이스 연결 설정 초기화"""
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'stock_user'),
            'password': os.getenv('DB_PASSWORD', 'StockPass2025!'),
            'charset': 'utf8mb4',
            'autocommit': True
        }

        # 전용 크롤링 데이터베이스
        self.crawling_db = 'crawling_db'

        # 연결 테스트
        self._test_connection()

    def _test_connection(self) -> bool:
        """데이터베이스 연결 테스트"""
        try:
            connection = self.get_connection()
            connection.close()
            logging.info("✅ TopRateDatabase 연결 성공")
            return True
        except Exception as e:
            logging.error(f"❌ TopRateDatabase 연결 실패: {e}")
            return False

    def get_connection(self, database: str = None) -> pymysql.Connection:
        """
        데이터베이스 연결 반환

        Args:
            database: 연결할 데이터베이스명 (None이면 기본 연결)

        Returns:
            pymysql.Connection 객체
        """
        config = self.db_config.copy()
        if database:
            config['database'] = database
        return pymysql.connect(**config)

    def setup_crawling_database(self) -> bool:
        """
        크롤링 전용 데이터베이스 생성

        Returns:
            성공 여부
        """
        try:
            connection = self.get_connection()
            cursor = connection.cursor()

            # 데이터베이스 생성 (존재하지 않으면)
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS {self.crawling_db} "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )

            cursor.close()
            connection.close()

            logging.info(f"✅ 크롤링 데이터베이스 ({self.crawling_db}) 설정 완료")
            return True

        except Exception as e:
            logging.error(f"❌ 크롤링 데이터베이스 설정 실패: {e}")
            return False

    def setup_theme_table(self, date_str: str) -> str:
        """
        날짜별 테마 테이블 생성 (기존 테이블 덮어쓰기)

        Args:
            date_str: YYYY-MM-DD 형식의 날짜

        Returns:
            생성된 테이블명
        """
        table_name = get_table_name(date_str)

        try:
            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor()

            # 기존 테이블 삭제 (덮어쓰기)
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

            # 새 테이블 생성
            create_sql = f"""
            CREATE TABLE {table_name} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                stock_code VARCHAR(10) NOT NULL,
                stock_name VARCHAR(100) NOT NULL,
                price INT DEFAULT 0,
                change_rate DECIMAL(5,2) DEFAULT 0.00,
                volume BIGINT DEFAULT 0,
                themes JSON,
                news JSON,
                theme_stocks JSON,
                crawled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_stock_code (stock_code),
                INDEX idx_change_rate (change_rate),
                INDEX idx_crawled_at (crawled_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """

            cursor.execute(create_sql)
            cursor.close()
            connection.close()

            logging.info(f"✅ 테마 테이블 생성 완료: {table_name}")
            return table_name

        except Exception as e:
            logging.error(f"❌ 테마 테이블 생성 실패: {e}")
            raise

    def save_theme_data(self, table_name: str, theme_data: List[Dict]) -> bool:
        """
        테마 크롤링 데이터 저장

        Args:
            table_name: 저장할 테이블명
            theme_data: 저장할 테마 데이터 리스트

        Returns:
            저장 성공 여부
        """
        if not theme_data:
            logging.warning("저장할 테마 데이터가 없습니다")
            return False

        try:
            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor()

            insert_sql = f"""
            INSERT INTO {table_name} 
            (stock_code, stock_name, price, change_rate, volume, themes, news, theme_stocks)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            success_count = 0

            for data in theme_data:
                try:
                    cursor.execute(insert_sql, (
                        data.get('stock_code', ''),
                        data.get('stock_name', ''),
                        data.get('price', 0),
                        data.get('change_rate', 0.0),
                        data.get('volume', 0),
                        json.dumps(data.get('themes', []), ensure_ascii=False),
                        json.dumps(data.get('news', []), ensure_ascii=False),
                        json.dumps(data.get('theme_stocks', {}), ensure_ascii=False)
                    ))
                    success_count += 1

                except Exception as e:
                    logging.error(f"개별 데이터 저장 실패 ({data.get('stock_name', 'Unknown')}): {e}")
                    continue

            cursor.close()
            connection.close()

            logging.info(f"✅ 테마 데이터 저장 완료: {success_count}/{len(theme_data)}개")
            return success_count > 0

        except Exception as e:
            logging.error(f"❌ 테마 데이터 저장 실패: {e}")
            return False

    def get_theme_data(self, date_str: str) -> List[Dict]:
        """
        날짜별 테마 데이터 조회

        Args:
            date_str: YYYY-MM-DD 형식의 날짜

        Returns:
            테마 데이터 리스트
        """
        table_name = get_table_name(date_str)

        try:
            if not self.check_table_exists(table_name):
                logging.warning(f"테이블이 존재하지 않습니다: {table_name}")
                return []

            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor(pymysql.cursors.DictCursor)

            query = f"""
            SELECT stock_code, stock_name, price, change_rate, volume, 
                   themes, news, theme_stocks, crawled_at
            FROM {table_name} 
            ORDER BY change_rate DESC
            """

            cursor.execute(query)
            results = cursor.fetchall()

            # JSON 필드 파싱
            for result in results:
                for json_field in ['themes', 'news', 'theme_stocks']:
                    if result[json_field]:
                        try:
                            result[json_field] = json.loads(result[json_field])
                        except json.JSONDecodeError:
                            result[json_field] = []

            cursor.close()
            connection.close()

            logging.info(f"✅ 테마 데이터 조회 완료: {len(results)}개 ({table_name})")
            return results

        except Exception as e:
            logging.error(f"❌ 테마 데이터 조회 실패: {e}")
            return []

    def get_theme_summary(self, date_str: str) -> List[Dict]:
        """
        테마별 요약 통계 조회

        Args:
            date_str: YYYY-MM-DD 형식의 날짜

        Returns:
            테마별 요약 데이터
        """
        table_name = get_table_name(date_str)

        try:
            if not self.check_table_exists(table_name):
                return []

            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor(pymysql.cursors.DictCursor)

            # 테마별 집계 쿼리
            query = f"""
            SELECT 
                JSON_UNQUOTE(JSON_EXTRACT(themes, '$[0]')) as theme_name,
                COUNT(*) as stock_count,
                AVG(change_rate) as avg_change_rate,
                MAX(change_rate) as max_change_rate,
                SUM(CASE WHEN change_rate > 0 THEN 1 ELSE 0 END) as rising_stocks,
                (
                    SELECT COUNT(*)
                    FROM {table_name} t2 
                    WHERE JSON_EXTRACT(t2.news, '$') != 'null' 
                    AND JSON_LENGTH(t2.news) > 0
                    AND JSON_EXTRACT(t2.themes, '$[0]') = JSON_EXTRACT(themes, '$[0]')
                ) as total_news,
                (
                    SELECT CONCAT(stock_name, ' (+', ROUND(change_rate, 1), '%)')
                    FROM {table_name} t3
                    WHERE JSON_EXTRACT(t3.themes, '$[0]') = JSON_EXTRACT(themes, '$[0]')
                    ORDER BY change_rate DESC 
                    LIMIT 1
                ) as top_stock
            FROM {table_name}
            WHERE JSON_LENGTH(themes) > 0
            GROUP BY JSON_UNQUOTE(JSON_EXTRACT(themes, '$[0]'))
            HAVING theme_name IS NOT NULL AND theme_name != ''
            ORDER BY avg_change_rate DESC
            """

            cursor.execute(query)
            results = cursor.fetchall()

            cursor.close()
            connection.close()

            logging.info(f"✅ 테마 요약 조회 완료: {len(results)}개 테마")
            return results

        except Exception as e:
            logging.error(f"❌ 테마 요약 조회 실패: {e}")
            return []

    def get_theme_detail(self, date_str: str, theme_name: str) -> Dict:
        """
        특정 테마의 상세 정보 조회

        Args:
            date_str: YYYY-MM-DD 형식의 날짜
            theme_name: 테마명

        Returns:
            테마 상세 정보
        """
        table_name = get_table_name(date_str)

        try:
            if not self.check_table_exists(table_name):
                return {}

            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor(pymysql.cursors.DictCursor)

            # 해당 테마 종목들 조회
            query = f"""
            SELECT stock_code, stock_name, price, change_rate, volume, news
            FROM {table_name}
            WHERE JSON_CONTAINS(themes, JSON_QUOTE(%s))
            ORDER BY change_rate DESC
            """

            cursor.execute(query, (theme_name,))
            stocks = cursor.fetchall()

            # JSON 필드 파싱
            all_news = []
            for stock in stocks:
                if stock['news']:
                    try:
                        stock_news = json.loads(stock['news'])
                        all_news.extend(stock_news)
                        stock['news'] = stock_news
                    except json.JSONDecodeError:
                        stock['news'] = []

            cursor.close()
            connection.close()

            if not stocks:
                return {}

            # 테마 통계 계산
            change_rates = [stock['change_rate'] for stock in stocks]
            rising_count = len([rate for rate in change_rates if rate > 0])

            result = {
                'theme_name': theme_name,
                'stock_count': len(stocks),
                'avg_change_rate': sum(change_rates) / len(change_rates),
                'max_change_rate': max(change_rates),
                'rising_stocks': rising_count,
                'total_news': len(all_news),
                'stocks': stocks,
                'news': all_news[:10]  # 상위 10개 뉴스만
            }

            logging.info(f"✅ 테마 상세정보 조회 완료: {theme_name} ({len(stocks)}개 종목)")
            return result

        except Exception as e:
            logging.error(f"❌ 테마 상세정보 조회 실패: {e}")
            return {}

    def check_table_exists(self, table_name: str) -> bool:
        """
        테이블 존재 여부 확인

        Args:
            table_name: 확인할 테이블명

        Returns:
            존재 여부
        """
        try:
            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor()

            cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
            exists = cursor.fetchone() is not None

            cursor.close()
            connection.close()

            return exists

        except Exception as e:
            logging.error(f"테이블 존재 확인 실패: {e}")
            return False

    def get_available_dates(self) -> List[str]:
        """
        수집된 데이터가 있는 날짜 목록 조회

        Returns:
            날짜 리스트 (YYYY-MM-DD 형식)
        """
        try:
            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor()

            cursor.execute("SHOW TABLES LIKE 'theme_%'")
            tables = cursor.fetchall()

            cursor.close()
            connection.close()

            # 테이블명에서 날짜 추출
            dates = []
            for (table_name,) in tables:
                if table_name.startswith('theme_') and len(table_name) == 14:  # theme_YYYYMMDD
                    date_part = table_name[6:]  # YYYYMMDD
                    try:
                        # YYYY-MM-DD 형식으로 변환
                        formatted_date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
                        dates.append(formatted_date)
                    except:
                        continue

            dates.sort(reverse=True)  # 최신 순으로 정렬
            return dates

        except Exception as e:
            logging.error(f"날짜 목록 조회 실패: {e}")
            return []

    def delete_old_data(self, keep_days: int = 30) -> bool:
        """
        오래된 데이터 삭제 (보관 기간 초과)

        Args:
            keep_days: 보관할 일수

        Returns:
            삭제 성공 여부
        """
        try:
            from datetime import timedelta

            cutoff_date = datetime.now() - timedelta(days=keep_days)
            cutoff_str = cutoff_date.strftime('%Y%m%d')

            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor()

            # 삭제 대상 테이블 조회
            cursor.execute("SHOW TABLES LIKE 'theme_%'")
            tables = cursor.fetchall()

            deleted_count = 0
            for (table_name,) in tables:
                if table_name.startswith('theme_') and len(table_name) == 14:
                    date_part = table_name[6:]  # YYYYMMDD
                    if date_part < cutoff_str:
                        cursor.execute(f"DROP TABLE {table_name}")
                        deleted_count += 1
                        logging.info(f"🗑️ 오래된 테이블 삭제: {table_name}")

            cursor.close()
            connection.close()

            if deleted_count > 0:
                logging.info(f"✅ 오래된 데이터 정리 완료: {deleted_count}개 테이블 삭제")
            else:
                logging.info("ℹ️ 삭제할 오래된 데이터가 없습니다")

            return True

        except Exception as e:
            logging.error(f"❌ 오래된 데이터 삭제 실패: {e}")
            return False

    def get_crawling_status(self, date_str: str) -> Dict:
        """
        크롤링 상태 정보 조회

        Args:
            date_str: YYYY-MM-DD 형식의 날짜

        Returns:
            크롤링 상태 정보
        """
        table_name = get_table_name(date_str)

        try:
            if not self.check_table_exists(table_name):
                return {
                    'exists': False,
                    'total_stocks': 0,
                    'last_updated': None,
                    'theme_count': 0
                }

            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor(pymysql.cursors.DictCursor)

            # 기본 통계
            cursor.execute(f"SELECT COUNT(*) as total FROM {table_name}")
            total_result = cursor.fetchone()

            # 최근 업데이트 시간
            cursor.execute(f"SELECT MAX(crawled_at) as last_updated FROM {table_name}")
            time_result = cursor.fetchone()

            # 테마 수
            cursor.execute(f"""
                SELECT COUNT(DISTINCT JSON_UNQUOTE(JSON_EXTRACT(themes, '$[0]'))) as theme_count
                FROM {table_name}
                WHERE JSON_LENGTH(themes) > 0
            """)
            theme_result = cursor.fetchone()

            cursor.close()
            connection.close()

            return {
                'exists': True,
                'total_stocks': total_result['total'] if total_result else 0,
                'last_updated': time_result['last_updated'] if time_result else None,
                'theme_count': theme_result['theme_count'] if theme_result else 0
            }

        except Exception as e:
            logging.error(f"❌ 크롤링 상태 조회 실패: {e}")
            return {
                'exists': False,
                'total_stocks': 0,
                'last_updated': None,
                'theme_count': 0
            }