from common.database import db
from datetime import datetime


class StockInterest(db.Model):
    """관심 종목 모델"""
    __tablename__ = 'stock_interest'

    stock_code = db.Column(db.String(10), primary_key=True)
    stock_name = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Integer, default=1)  # 1: 활성, 0: 비활성
    setting_price = db.Column(db.Integer, default=0)
    first_buy_price = db.Column(db.Integer, default=0)
    second_buy_price = db.Column(db.Integer, default=0)
    third_buy_price = db.Column(db.Integer, default=0)
    buy_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'is_active': self.is_active,
            'setting_price': self.setting_price,
            'first_buy_price': self.first_buy_price,
            'second_buy_price': self.second_buy_price,
            'third_buy_price': self.third_buy_price,
            'buy_count': self.buy_count,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class ThemeStock(db.Model):
    """테마 종목 모델"""
    __tablename__ = 'theme_stocks'

    stock_code = db.Column(db.String(10), primary_key=True)
    stock_name = db.Column(db.String(50), nullable=False)

    def to_dict(self):
        return {
            'stock_code': self.stock_code,
            'stock_name': self.stock_name
        }