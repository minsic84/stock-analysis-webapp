// 종목설정 전용 JavaScript

let stockData = [];

// 페이지 로드시 초기화
document.addEventListener('DOMContentLoaded', function() {
    loadStockData();
    setupAutoComplete();
    setupFormSubmit();
});

// 자동완성 설정
function setupAutoComplete() {
    const stockCodeInput = document.getElementById('add_stock_code');
    const stockNameInput = document.getElementById('add_stock_name');
    const suggestionsDiv = document.getElementById('code-suggestions');

    let debounceTimer;

    stockCodeInput.addEventListener('input', function() {
        const value = this.value.trim();

        clearTimeout(debounceTimer);

        if (value.length === 0) {
            hideSuggestions();
            stockNameInput.value = '';
            return;
        }

        // 6자리 입력시 종목명 자동 조회
        if (value.length === 6) {
            fetchStockName(value);
        }

        // 자동완성 표시 (2자리 이상 입력시)
        if (value.length >= 2) {
            debounceTimer = setTimeout(function() {
                searchStocks(value, 'code');
            }, 300);
        } else {
            hideSuggestions();
        }
    });

    // 클릭시 자동완성 숨기기
    document.addEventListener('click', function(e) {
        if (!e.target.closest('#add_stock_code') && !e.target.closest('#code-suggestions')) {
            hideSuggestions();
        }
    });
}

// 폼 제출 설정
function setupFormSubmit() {
    document.getElementById('addStockForm').addEventListener('submit', function(e) {
        e.preventDefault();
        addNewStock();
    });
}

// 종목명 자동 조회
async function fetchStockName(stockCode) {
    try {
        const response = await fetch('/api/stock-setting/stock-name/' + stockCode);
        const result = await response.json();

        if (result.success) {
            document.getElementById('add_stock_name').value = result.stock_name;
        } else {
            document.getElementById('add_stock_name').value = '';
        }
    } catch (error) {
        console.error('종목명 조회 오류:', error);
        document.getElementById('add_stock_name').value = '';
    }
}

// 종목 검색
async function searchStocks(searchTerm, searchType) {
    try {
        const response = await fetch('/api/stock-setting/search-stocks?q=' + searchTerm + '&type=' + searchType);
        const results = await response.json();
        showSuggestions(results);
    } catch (error) {
        console.error('검색 오류:', error);
        hideSuggestions();
    }
}

// 자동완성 표시
function showSuggestions(suggestions) {
    const suggestionsDiv = document.getElementById('code-suggestions');

    if (suggestions.length === 0) {
        hideSuggestions();
        return;
    }

    suggestionsDiv.innerHTML = '';

    suggestions.forEach(function(stock) {
        const item = document.createElement('div');
        item.className = 'suggestion-item';
        item.innerHTML = '<strong>' + stock.stock_code + '</strong> - ' + stock.stock_name;

        item.addEventListener('click', function() {
            document.getElementById('add_stock_code').value = stock.stock_code;
            document.getElementById('add_stock_name').value = stock.stock_name;
            hideSuggestions();
        });

        suggestionsDiv.appendChild(item);
    });

    suggestionsDiv.style.display = 'block';
}

// 자동완성 숨기기
function hideSuggestions() {
    document.getElementById('code-suggestions').style.display = 'none';
}

// 서버에서 종목 데이터 불러오기
async function loadStockData() {
    try {
        const response = await fetch('/api/stock-setting/stocks');
        stockData = await response.json();
        renderStockTable();
        updateStatistics();
    } catch (error) {
        console.error('데이터 로드 오류:', error);
        alert('데이터를 불러오는 중 오류가 발생했습니다.');
    }
}

// 테이블 렌더링
function renderStockTable() {
    const tbody = document.getElementById('stockTableBody');
    tbody.innerHTML = '';

    stockData.forEach(function(stock) {
        const row = document.createElement('tr');
        row.innerHTML =
            '<td><input type="checkbox" class="row-checkbox" value="' + stock.stock_code + '"></td>' +
            '<td><strong>' + stock.stock_code + '</strong></td>' +
            '<td><input type="text" value="' + stock.stock_name + '" onchange="updateField(\'' + stock.stock_code + '\', \'stock_name\', this.value)"></td>' +
            '<td><select onchange="updateField(\'' + stock.stock_code + '\', \'is_active\', this.value)">' +
                '<option value="1"' + (stock.is_active == 1 ? ' selected' : '') + '>활성</option>' +
                '<option value="0"' + (stock.is_active == 0 ? ' selected' : '') + '>비활성</option>' +
            '</select></td>' +
            '<td><input type="number" value="' + stock.setting_price + '" onchange="updateField(\'' + stock.stock_code + '\', \'setting_price\', this.value)"></td>' +
            '<td><input type="number" value="' + stock.first_buy_price + '" onchange="updateField(\'' + stock.stock_code + '\', \'first_buy_price\', this.value)"></td>' +
            '<td><input type="number" value="' + stock.second_buy_price + '" onchange="updateField(\'' + stock.stock_code + '\', \'second_buy_price\', this.value)"></td>' +
            '<td><input type="number" value="' + stock.third_buy_price + '" onchange="updateField(\'' + stock.stock_code + '\', \'third_buy_price\', this.value)"></td>' +
            '<td><input type="number" value="' + stock.buy_count + '" onchange="updateField(\'' + stock.stock_code + '\', \'buy_count\', this.value)"></td>' +
            '<td style="font-size: 12px; color: #666;">' + stock.created_at + '</td>' +
            '<td style="font-size: 12px; color: #666;">' + stock.updated_at + '</td>' +
            '<td class="manage-buttons">' +
                '<button class="manage-btn btn-save" onclick="saveStock(\'' + stock.stock_code + '\')">저장</button>' +
                '<button class="manage-btn btn-delete" onclick="deleteStock(\'' + stock.stock_code + '\')">삭제</button>' +
            '</td>';
        tbody.appendChild(row);
    });

    document.getElementById('totalCount').textContent = stockData.length;
}

// 필드 업데이트
function updateField(stockCode, field, value) {
    const stock = stockData.find(function(s) {
        return s.stock_code === stockCode;
    });
    if (stock) {
        if (field === 'stock_name') {
            stock[field] = value;
        } else {
            stock[field] = parseInt(value) || 0;
        }
    }
}

// 새 종목 추가
async function addNewStock() {
    const stockCode = document.getElementById('add_stock_code').value.trim();
    const stockName = document.getElementById('add_stock_name').value.trim();

    if (!stockCode) {
        alert('종목코드를 입력해주세요.');
        return;
    }

    const newStock = {
        stock_code: stockCode,
        stock_name: stockName,
        is_active: parseInt(document.getElementById('add_is_active').value),
        setting_price: parseInt(document.getElementById('add_setting_price').value) || 0,
        first_buy_price: parseInt(document.getElementById('add_first_buy_price').value) || 0,
        second_buy_price: 0,
        third_buy_price: 0,
        buy_count: parseInt(document.getElementById('add_buy_count').value) || 0
    };

    try {
        const response = await fetch('/api/stock-setting/add-stock', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(newStock)
        });

        const result = await response.json();
        if (result.success) {
            alert('종목이 추가되었습니다.');
            document.getElementById('addStockForm').reset();
            document.getElementById('add_stock_name').value = '';
            loadStockData();
        } else {
            alert('추가 실패: ' + result.message);
        }
    } catch (error) {
        alert('추가 중 오류가 발생했습니다.');
    }
}

// 개별 종목 저장
async function saveStock(stockCode) {
    const stock = stockData.find(function(s) {
        return s.stock_code === stockCode;
    });
    if (!stock) return;

    try {
        const response = await fetch('/api/stock-setting/update-stock', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(stock)
        });

        const result = await response.json();
        if (result.success) {
            alert('저장되었습니다.');
            loadStockData();
        } else {
            alert('저장 실패: ' + result.message);
        }
    } catch (error) {
        alert('저장 중 오류가 발생했습니다.');
    }
}

// 종목 삭제
async function deleteStock(stockCode) {
    if (confirm(stockCode + ' 종목을 삭제하시겠습니까?')) {
        await deleteStocks([stockCode]);
    }
}

// 선택된 종목들 삭제
async function deleteSelected() {
    const checkboxes = document.querySelectorAll('.row-checkbox:checked');
    const selected = [];
    checkboxes.forEach(function(cb) {
        selected.push(cb.value);
    });

    if (selected.length === 0) {
        alert('삭제할 종목을 선택해주세요.');
        return;
    }

    if (confirm('선택된 ' + selected.length + '개 종목을 삭제하시겠습니까?')) {
        await deleteStocks(selected);
    }
}

// 삭제 실행
async function deleteStocks(stockCodes) {
    try {
        const response = await fetch('/api/stock-setting/delete-stock', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({stock_codes: stockCodes})
        });

        const result = await response.json();
        if (result.success) {
            alert(result.message);
            loadStockData();
        } else {
            alert('삭제 실패: ' + result.message);
        }
    } catch (error) {
        alert('삭제 중 오류가 발생했습니다.');
    }
}

// 전체 선택/해제
function toggleSelectAll() {
    const selectAll = document.getElementById('selectAll');
    const checkboxes = document.querySelectorAll('.row-checkbox');
    checkboxes.forEach(function(checkbox) {
        checkbox.checked = selectAll.checked;
    });
}

// 목록 새로고침
function refreshStockList() {
    loadStockData();
}

// 통계 업데이트
function updateStatistics() {
    let activeCount = 0;
    let inactiveCount = 0;
    let totalBuyCount = 0;
    let totalPrice = 0;

    stockData.forEach(function(stock) {
        if (stock.is_active === 1) {
            activeCount++;
        } else {
            inactiveCount++;
        }
        totalBuyCount += stock.buy_count;
        totalPrice += stock.setting_price;
    });

    const avgPrice = stockData.length > 0 ? Math.round(totalPrice / stockData.length) : 0;

    document.getElementById('activeCount').textContent = activeCount;
    document.getElementById('inactiveCount').textContent = inactiveCount;
    document.getElementById('totalBuyCount').textContent = totalBuyCount;
    document.getElementById('avgPrice').textContent = avgPrice.toLocaleString() + '원';
}

// 전체 저장
async function saveAllChanges() {
    if (confirm('모든 변경사항을 저장하시겠습니까?')) {
        let successCount = 0;

        for (let i = 0; i < stockData.length; i++) {
            const stock = stockData[i];
            try {
                const response = await fetch('/api/stock-setting/update-stock', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(stock)
                });
                const result = await response.json();
                if (result.success) successCount++;
            } catch (error) {
                console.error('저장 오류:', error);
            }
        }

        alert(successCount + '개 종목이 저장되었습니다.');
        loadStockData();
    }
}