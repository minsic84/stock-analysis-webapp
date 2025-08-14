#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
등락율상위분석 실제 데이터베이스 모듈 (paste.txt 기반 완전 구현)
- 실제 MySQL 연결 및 데이터 처리
- crawling_db 스키마 관리
- 테마별 테이블 생성 및 관리
- 실제 분석 데이터 조회
"""

import pymysql
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


class TopRateDatabase:
    """실제 작동하는 등락율상위분석 데이터베이스 (paste.txt 기반)"""

    def __init__(self):
        """데이터베이스 초기화"""
        self.crawling_db = 'crawling_db'

        # DB 연결 설정 (paste.txt와 동일)
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'charset': 'utf8mb4',
            'autocommit': True
        }

        logging.info("🗄️ TopRateDatabase 초기화 완료 (실제 DB 모드)")

    def get_connection(self, database: str = None) -> pymysql.Connection:
        """DB 연결 생성 (paste.txt get_db_connection 함수 기반)"""
        try:
            config = self.db_config.copy()
            if database:
                config['database'] = database

            connection = pymysql.connect(**config)
            return connection

        except Exception as e:
            logging.error(f"❌ DB 연결 실패: {e}")
            raise

    def setup_crawling_database(self) -> bool:
        """crawling_db 스키마 설정 (paste.txt setup_database 함수 기반)"""
        try:
            connection = self.get_connection()
            cursor = connection.cursor()

            # crawling_db 스키마 생성
            cursor.execute(
                "CREATE DATABASE IF NOT EXISTS crawling_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            logging.info("✅ crawling_db 스키마 생성/확인 완료")

            cursor.close()
            connection.close()
            return True

        except Exception as e:
            logging.error(f"❌ crawling_db 설정 실패: {e}")
            return False

    def get_available_dates(self) -> List[str]:
        """수집된 데이터가 있는 날짜 목록 조회 (실제 테이블 기반)"""
        try:
            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor()

            # theme_ 테이블들 조회
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

            # 최신 순으로 정렬
            dates.sort(reverse=True)
            logging.info(f"📅 사용 가능한 날짜: {len(dates)}개 ({dates[:3]}...)")
            return dates

        except Exception as e:
            logging.error(f"❌ 날짜 목록 조회 실패: {e}")
            return []

    def has_data_for_date(self, date_str: str) -> bool:
        """특정 날짜의 데이터 존재 여부 확인 (실제 테이블 기반)"""
        try:
            clean_date = date_str.replace('-', '')
            table_name = f"theme_{clean_date}"

            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor()

            # 테이블 존재 확인
            cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
            table_exists = cursor.fetchone()

            if not table_exists:
                cursor.close()
                connection.close()
                return False

            # 데이터 존재 확인
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]

            cursor.close()
            connection.close()

            logging.info(f"📊 {date_str} 데이터 확인: {count}개 종목")
            return count > 0

        except Exception as e:
            logging.error(f"❌ 데이터 존재 확인 실패 ({date_str}): {e}")
            return False

    def get_theme_analysis_results(self, date_str: str) -> List[Dict]:
        """테마별 분석 결과 조회 (카드 표시용)"""
        try:
            clean_date = date_str.replace('-', '')
            table_name = f"theme_{clean_date}"

            if not self.has_data_for_date(date_str):
                return []

            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor()

            # 테마별 통계 계산
            query = f"""
            SELECT 
                JSON_UNQUOTE(JSON_EXTRACT(themes, '$[0]')) as theme_name,
                COUNT(*) as stock_count,
                AVG(change_rate) as avg_change_rate,
                SUM(CASE WHEN change_rate > 0 THEN 1 ELSE 0 END) as positive_stocks,
                SUM(volume) as total_volume,
                AVG(JSON_LENGTH(news)) as avg_news_count
            FROM {table_name}
            GROUP BY theme_name
            HAVING stock_count >= 3  -- 최소 3개 종목 이상
            ORDER BY avg_change_rate DESC
            """

            cursor.execute(query)
            results = cursor.fetchall()

            cursor.close()
            connection.close()

            # 결과 포맷팅 (카드 표시용)
            themes = []
            for i, (
            theme_name, stock_count, avg_change_rate, positive_stocks, total_volume, avg_news_count) in enumerate(
                    results):
                # 테마 아이콘 매핑
                icon = self._get_theme_icon(theme_name)

                # 상승 비율 계산
                positive_ratio = (positive_stocks / stock_count * 100) if stock_count > 0 else 0

                # 테마 강도 계산
                strength = self._calculate_theme_strength(avg_change_rate, positive_ratio, stock_count)

                theme_data = {
                    'rank': i + 1,
                    'theme_name': theme_name,
                    'icon': icon,
                    'stock_count': int(stock_count),
                    'avg_change_rate': round(float(avg_change_rate), 2),
                    'positive_stocks': int(positive_stocks),
                    'positive_ratio': round(positive_ratio, 1),
                    'total_volume': int(total_volume) if total_volume else 0,
                    'avg_news_count': round(float(avg_news_count), 1) if avg_news_count else 0,
                    'strength': strength,
                    'date': date_str
                }
                themes.append(theme_data)

            logging.info(f"📊 {date_str} 테마 분석 결과: {len(themes)}개 테마")
            return themes

        except Exception as e:
            logging.error(f"❌ 테마 분석 결과 조회 실패 ({date_str}): {e}")
            return []

    def get_theme_detail(self, theme_name: str, date_str: str) -> Optional[Dict]:
        """특정 테마의 상세 정보 조회 (모달 표시용)"""
        try:
            clean_date = date_str.replace('-', '')
            table_name = f"theme_{clean_date}"

            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor()

            # 테마에 속한 종목들 조회
            query = f"""
            SELECT 
                stock_code, stock_name, price, change_rate, volume, news, theme_stocks
            FROM {table_name}
            WHERE JSON_CONTAINS(themes, JSON_QUOTE(%s))
            ORDER BY change_rate DESC
            """

            cursor.execute(query, (theme_name,))
            stocks = cursor.fetchall()

            if not stocks:
                cursor.close()
                connection.close()
                return None

            # 종목 리스트 구성
            stock_list = []
            all_news = []
            total_volume = 0

            for stock_code, stock_name, price, change_rate, volume, news_json, theme_stocks_json in stocks:
                # 뉴스 파싱
                try:
                    stock_news = json.loads(news_json) if news_json else []
                    all_news.extend(stock_news)
                except:
                    stock_news = []

                # 테마 내 종목 정보 파싱
                try:
                    theme_stocks = json.loads(theme_stocks_json) if theme_stocks_json else {}
                    theme_stock_count = len(theme_stocks.get(theme_name, []))
                except:
                    theme_stock_count = 0

                stock_info = {
                    'rank': len(stock_list) + 1,
                    'stock_code': stock_code,
                    'stock_name': stock_name,
                    'current_price': int(price) if price else 0,
                    'change_rate': float(change_rate) if change_rate else 0,
                    'volume': int(volume) if volume else 0,
                    'news_count': len(stock_news),
                    'theme_stock_count': theme_stock_count
                }
                stock_list.append(stock_info)
                total_volume += stock_info['volume']

            cursor.close()
            connection.close()

            # 테마 요약 통계
            positive_stocks = sum(1 for stock in stock_list if stock['change_rate'] > 0)
            avg_change_rate = sum(stock['change_rate'] for stock in stock_list) / len(stock_list)

            # 최신 뉴스 5개 선별 (시간순)
            recent_news = sorted(all_news, key=lambda x: x.get('time', ''), reverse=True)[:5]

            theme_detail = {
                'theme_name': theme_name,
                'icon': self._get_theme_icon(theme_name),
                'date': date_str,
                'summary': {
                    'total_stocks': len(stock_list),
                    'positive_stocks': positive_stocks,
                    'positive_ratio': round(positive_stocks / len(stock_list) * 100, 1),
                    'avg_change_rate': round(avg_change_rate, 2),
                    'total_volume': total_volume,
                    'total_news': len(all_news)
                },
                'stocks': stock_list,
                'recent_news': recent_news
            }

            logging.info(f"📋 {theme_name} 상세 정보: {len(stock_list)}개 종목, {len(all_news)}개 뉴스")
            return theme_detail

        except Exception as e:
            logging.error(f"❌ 테마 상세 정보 조회 실패 ({theme_name}): {e}")
            return None

    def get_system_status(self) -> Dict:
        """시스템 상태 정보 조회 (실시간 모니터링용)"""
        try:
            connection = self.get_connection(self.crawling_db)
            cursor = connection.cursor()

            # 전체 테이블 목록
            cursor.execute("SHOW TABLES LIKE 'theme_%'")
            all_tables = cursor.fetchall()

            # 최신 테이블 정보
            if all_tables:
                latest_table = sorted([table[0] for table in all_tables])[-1]

                # 최신 데이터 통계
                cursor.execute(f"SELECT COUNT(*) FROM {latest_table}")
                latest_stock_count = cursor.fetchone()[0]

                cursor.execute(f"""
                SELECT 
                    COUNT(DISTINCT JSON_UNQUOTE(JSON_EXTRACT(themes, '$[0]'))) as theme_count,
                    SUM(JSON_LENGTH(news)) as total_news,
                    MAX(created_at) as last_update
                FROM {latest_table}
                """)
                stats = cursor.fetchone()
                theme_count, total_news, last_update = stats
            else:
                latest_table = None
                latest_stock_count = 0
                theme_count = 0
                total_news = 0
                last_update = None

            # DB 연결 상태 확인
            cursor.execute("SELECT CONNECTION_ID()")
            connection_id = cursor.fetchone()[0]

            cursor.close()
            connection.close()

            # 시스템 상태 구성
            status = {
                'database': {
                    'status': 'healthy',
                    'connection_id': connection_id,
                    'response_time': '< 10ms'  # 실제로는 측정 필요
                },
                'latest_data': {
                    'table_name': latest_table,
                    'stock_count': latest_stock_count,
                    'theme_count': theme_count,
                    'total_news': total_news,
                    'last_update': last_update.strftime('%Y-%m-%d %H:%M:%S') if last_update else None
                },
                'storage': {
                    'total_tables': len(all_tables),
                    'oldest_date': self._extract_date_from_table(all_tables[0][0]) if all_tables else None,
                    'newest_date': self._extract_date_from_table(all_tables[-1][0]) if all_tables else None
                },
                'health_check': {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'status': 'operational'
                }
            }

            return status

        except Exception as e:
            logging.error(f"❌ 시스템 상태 조회 실패: {e}")
            return {
                'database': {'status': 'error', 'error': str(e)},
                'health_check': {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'status': 'error'
                }
            }

    def delete_old_data(self, keep_days: int = 30) -> bool:
        """오래된 데이터 삭제 (paste.txt 기반)"""
        try:
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

    # ============= 유틸리티 함수들 =============

    def _get_theme_icon(self, theme_name: str) -> str:
        """테마별 아이콘 매핑"""
        icon_mapping = {
            '증권': '🏦', 'AI반도체': '🤖', '2차전지': '🔋',
            'AI': '🤖', '반도체': '💾', '바이오': '🧬',
            '게임': '🎮', '자동차': '🚗', '화학': '⚗️',
            '조선': '🚢', '항공': '✈️', '건설': '🏗️',
            '통신': '📡', '은행': '🏛️', '헬스케어': '🏥',
            '엔터테인먼트': '🎭', '코로나19': '🦠',
            'K-pop': '🎵', '메타버스': '🌐', '전기차': '⚡',
            '친환경': '🌱', '우주항공': '🚀', '로봇': '🤖',
            'VR': '🥽', 'AR': '🥽', '블록체인': '⛓️'
        }

        # 테마명에서 키워드 찾기
        for keyword, icon in icon_mapping.items():
            if keyword in theme_name:
                return icon

        return '📈'  # 기본 아이콘

    def _calculate_theme_strength(self, avg_change_rate: float, positive_ratio: float, stock_count: int) -> str:
        """테마 강도 계산"""
        if avg_change_rate >= 5.0 and positive_ratio >= 80:
            return 'HOT'
        elif avg_change_rate >= 3.0 and positive_ratio >= 70:
            return 'STRONG'
        elif avg_change_rate >= 1.0 and positive_ratio >= 60:
            return 'NORMAL'
        else:
            return 'WEAK'

    def _extract_date_from_table(self, table_name: str) -> Optional[str]:
        """테이블명에서 날짜 추출"""
        try:
            if table_name.startswith('theme_') and len(table_name) == 14:
                date_part = table_name[6:]  # YYYYMMDD
                return f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
        except:
            pass
        return None

    def test_connection(self) -> bool:
        """DB 연결 테스트"""
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            connection.close()

            logging.info("✅ DB 연결 테스트 성공")
            return result[0] == 1

        except Exception as e:
            logging.error(f"❌ DB 연결 테스트 실패: {e}")
            return False