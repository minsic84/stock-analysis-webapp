from common.database import db
from .models import StockInterest, ThemeStock
from sqlalchemy.exc import SQLAlchemyError


class StockSettingDB:
    """종목설정 데이터베이스 관리 클래스"""

    @staticmethod
    def get_all_stocks():
        """모든 관심 종목 조회"""
        try:
            stocks = StockInterest.query.all()
            return [stock.to_dict() for stock in stocks]
        except SQLAlchemyError as e:
            print(f"종목 조회 오류: {e}")
            return []

    @staticmethod
    def get_stock_by_code(stock_code):
        """종목코드로 관심 종목 조회"""
        try:
            return StockInterest.query.filter_by(stock_code=stock_code).first()
        except SQLAlchemyError as e:
            print(f"종목 조회 오류: {e}")
            return None

    @staticmethod
    def get_stock_name_from_theme(stock_code):
        """theme_stock에서 종목명 조회"""
        try:
            theme_stock = ThemeStock.query.filter_by(stock_code=stock_code).first()
            return theme_stock.stock_name if theme_stock else None
        except SQLAlchemyError as e:
            print(f"종목명 조회 오류: {e}")
            return None

    @staticmethod
    def search_stocks_by_name(search_term):
        """종목명으로 검색"""
        try:
            stocks = ThemeStock.query.filter(
                ThemeStock.stock_name.like(f'%{search_term}%')
            ).limit(10).all()
            return [stock.to_dict() for stock in stocks]
        except SQLAlchemyError as e:
            print(f"종목 검색 오류: {e}")
            return []

    @staticmethod
    def search_stocks_by_code(search_term):
        """종목코드로 검색"""
        try:
            stocks = ThemeStock.query.filter(
                ThemeStock.stock_code.like(f'{search_term}%')
            ).limit(10).all()
            return [stock.to_dict() for stock in stocks]
        except SQLAlchemyError as e:
            print(f"종목 검색 오류: {e}")
            return []

    @staticmethod
    def add_stock(stock_data):
        """새 종목 추가"""
        try:
            # 이미 존재하는지 확인
            existing = StockInterest.query.filter_by(stock_code=stock_data['stock_code']).first()
            if existing:
                return {'success': False, 'message': '이미 등록된 종목입니다.'}

            # theme_stock에서 종목명 가져오기
            if not stock_data.get('stock_name'):
                theme_stock_name = StockSettingDB.get_stock_name_from_theme(stock_data['stock_code'])
                if not theme_stock_name:
                    return {'success': False, 'message': '해당 종목코드를 찾을 수 없습니다.'}
                stock_data['stock_name'] = theme_stock_name

            # 새 종목 생성
            new_stock = StockInterest(
                stock_code=stock_data['stock_code'],
                stock_name=stock_data['stock_name'],
                is_active=stock_data.get('is_active', 1),
                setting_price=stock_data.get('setting_price', 0),
                first_buy_price=stock_data.get('first_buy_price', 0),
                second_buy_price=stock_data.get('second_buy_price', 0),
                third_buy_price=stock_data.get('third_buy_price', 0),
                buy_count=stock_data.get('buy_count', 0)
            )

            db.session.add(new_stock)
            db.session.commit()

            return {'success': True, 'message': '종목이 추가되었습니다.'}

        except SQLAlchemyError as e:
            db.session.rollback()
            return {'success': False, 'message': f'DB 오류: {str(e)}'}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'오류 발생: {str(e)}'}

    @staticmethod
    def update_stock(stock_code, update_data):
        """종목 정보 수정"""
        try:
            stock = StockInterest.query.filter_by(stock_code=stock_code).first()
            if not stock:
                return {'success': False, 'message': '종목을 찾을 수 없습니다.'}

            # 데이터 업데이트
            for field, value in update_data.items():
                if field != 'stock_code' and hasattr(stock, field):
                    setattr(stock, field, value)

            db.session.commit()
            return {'success': True, 'message': '종목이 수정되었습니다.'}

        except SQLAlchemyError as e:
            db.session.rollback()
            return {'success': False, 'message': f'DB 오류: {str(e)}'}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'오류 발생: {str(e)}'}

    @staticmethod
    def delete_stocks(stock_codes):
        """종목 삭제"""
        try:
            deleted_count = 0
            for stock_code in stock_codes:
                stock = StockInterest.query.filter_by(stock_code=stock_code).first()
                if stock:
                    db.session.delete(stock)
                    deleted_count += 1

            db.session.commit()
            return {'success': True, 'message': f'{deleted_count}개 종목이 삭제되었습니다.'}

        except SQLAlchemyError as e:
            db.session.rollback()
            return {'success': False, 'message': f'DB 오류: {str(e)}'}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'오류 발생: {str(e)}'}

    @staticmethod
    def get_statistics():
        """통계 정보 계산"""
        try:
            stocks = StockSettingDB.get_all_stocks()

            active_count = len([s for s in stocks if s['is_active'] == 1])
            inactive_count = len([s for s in stocks if s['is_active'] == 0])
            total_buy_count = sum(s['buy_count'] for s in stocks)
            avg_price = round(sum(s['setting_price'] for s in stocks) / len(stocks)) if stocks else 0

            return {
                'total_count': len(stocks),
                'active_count': active_count,
                'inactive_count': inactive_count,
                'total_buy_count': total_buy_count,
                'avg_price': avg_price
            }
        except Exception as e:
            print(f"통계 계산 오류: {e}")
            return {
                'total_count': 0,
                'active_count': 0,
                'inactive_count': 0,
                'total_buy_count': 0,
                'avg_price': 0
            }