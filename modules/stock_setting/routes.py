from flask import Blueprint, render_template, request, jsonify

# Blueprint 생성 (맨 위에 배치)
stock_setting_bp = Blueprint('stock_setting', __name__,
                             template_folder='templates',
                             static_folder='static',
                             static_url_path='/stock_setting_static')

# database import는 Blueprint 생성 후에
from .database import StockSettingDB


# ============= 페이지 라우트 =============
@stock_setting_bp.route('/stock-setting')
def index():
    """종목설정 메인 페이지"""
    return render_template('stock_setting.html')


# ============= API 라우트 =============

@stock_setting_bp.route('/api/stock-setting/stocks')
def api_stocks():
    """종목 목록 조회"""
    stocks = StockSettingDB.get_all_stocks()
    return jsonify(stocks)


@stock_setting_bp.route('/api/stock-setting/stock-name/<stock_code>')
def api_stock_name(stock_code):
    """종목명 자동완성"""
    stock_name = StockSettingDB.get_stock_name_from_theme(stock_code)
    if stock_name:
        return jsonify({'success': True, 'stock_name': stock_name})
    else:
        return jsonify({'success': False, 'message': '해당 종목코드를 찾을 수 없습니다.'})


@stock_setting_bp.route('/api/stock-setting/search-stocks')
def api_search_stocks():
    """종목 검색"""
    search_term = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'code')

    if not search_term:
        return jsonify([])

    if search_type == 'name':
        results = StockSettingDB.search_stocks_by_name(search_term)
    else:
        results = StockSettingDB.search_stocks_by_code(search_term)

    return jsonify(results)


@stock_setting_bp.route('/api/stock-setting/add-stock', methods=['POST'])
def api_add_stock():
    """종목 추가"""
    try:
        data = request.json
        result = StockSettingDB.add_stock(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': f'요청 처리 오류: {str(e)}'})


@stock_setting_bp.route('/api/stock-setting/update-stock', methods=['POST'])
def api_update_stock():
    """종목 수정"""
    try:
        data = request.json
        stock_code = data.pop('stock_code', None)

        if not stock_code:
            return jsonify({'success': False, 'message': '종목코드가 필요합니다.'})

        result = StockSettingDB.update_stock(stock_code, data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': f'요청 처리 오류: {str(e)}'})


@stock_setting_bp.route('/api/stock-setting/delete-stock', methods=['POST'])
def api_delete_stock():
    """종목 삭제"""
    try:
        data = request.json
        stock_codes = data.get('stock_codes', [])

        if not stock_codes:
            return jsonify({'success': False, 'message': '삭제할 종목을 선택해주세요.'})

        result = StockSettingDB.delete_stocks(stock_codes)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': f'요청 처리 오류: {str(e)}'})


@stock_setting_bp.route('/api/stock-setting/statistics')
def api_statistics():
    """통계 정보"""
    stats = StockSettingDB.get_statistics()
    return jsonify(stats)