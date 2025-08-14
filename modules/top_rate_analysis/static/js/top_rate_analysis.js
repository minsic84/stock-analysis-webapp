/**
 * 등락율상위분석 JavaScript 모듈 (완전 수정판)
 * - 누락된 함수들 추가 구현
 * - 분석 실행 기능 완성
 * - API 통신 안정화
 */

class TopRateAnalysis {
    constructor() {
        this.apiPrefix = window.APP_CONFIG?.apiPrefix || '/top-rate/api';
        this.currentDate = window.APP_CONFIG?.currentDate || new Date().toISOString().split('T')[0];
        this.isCollecting = false;
        this.progressInterval = null;
        this.lastProgressMessage = '';

        // 요소 참조
        this.elements = {};

        // 이벤트 리스너 바인딩
        this.bindEvents();

        console.log('✅ TopRateAnalysis 초기화 완료');
    }

    /**
     * 초기화
     */
    static init() {
        if (!window.topRateAnalysis) {
            window.topRateAnalysis = new TopRateAnalysis();
        }
        return window.topRateAnalysis;
    }

    /**
     * DOM 요소 참조 설정
     */
    initElements() {
        this.elements = {
            // 버튼들
            collectDataBtn: document.getElementById('collectDataBtn'),
            analyzeBtn: document.getElementById('analyzeBtn'),

            // 진행상황
            progressSection: document.getElementById('progressSection'),
            progressFill: document.getElementById('progressFill'),
            progressText: document.getElementById('progressText'),
            progressPercent: document.getElementById('progressPercent'),
            logContainer: document.getElementById('logContainer'),

            // 날짜 선택
            analysisDate: document.getElementById('analysisDate'),

            // 결과 표시
            themeGrid: document.getElementById('themeGrid'),

            // 모달
            themeModal: document.getElementById('themeModal'),
            modalTitle: document.getElementById('modalTitle'),
            modalIcon: document.getElementById('modalIcon'),
            modalStockList: document.getElementById('modalStockList'),
            modalNewsList: document.getElementById('modalNewsList'),

            // 스케줄 토글
            scheduleToggles: document.querySelectorAll('.schedule-toggle')
        };
    }

    /**
     * 이벤트 리스너 바인딩
     */
    bindEvents() {
        document.addEventListener('DOMContentLoaded', () => {
            this.initElements();
            this.loadInitialData();
            this.setupEventListeners();
        });
    }

    /**
     * 이벤트 리스너 설정
     */
    setupEventListeners() {
        // 데이터 수집 버튼
        if (this.elements.collectDataBtn) {
            this.elements.collectDataBtn.addEventListener('click', () => {
                this.startDataCollection();
            });
        }

        // 🔥 분석 실행 버튼 (핵심 수정)
        if (this.elements.analyzeBtn) {
            this.elements.analyzeBtn.addEventListener('click', () => {
                this.startAnalysis();
            });
        }

        // 날짜 변경
        if (this.elements.analysisDate) {
            this.elements.analysisDate.addEventListener('change', (e) => {
                this.currentDate = e.target.value;
                this.onDateChange();
            });
        }

        // 스케줄 토글
        this.elements.scheduleToggles?.forEach(toggle => {
            toggle.addEventListener('click', () => {
                this.toggleSchedule(toggle);
            });
        });

        // 모달 닫기 (외부 클릭)
        if (this.elements.themeModal) {
            this.elements.themeModal.addEventListener('click', (e) => {
                if (e.target === this.elements.themeModal) {
                    this.closeModal();
                }
            });
        }

        // 키보드 이벤트
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeModal();
            }
        });
    }

    /**
     * 초기 데이터 로드
     */
    async loadInitialData() {
        try {
            // 현재 날짜의 분석 결과가 있는지 확인
            const hasData = await this.checkDataExists(this.currentDate);

            if (hasData) {
                this.showAnalyzeButton();
                await this.loadThemeResults();
                this.addLog(`💡 ${this.currentDate} 데이터가 있습니다. 분석 버튼을 클릭하세요.`, 'success');
            } else {
                this.hideAnalyzeButton();
                this.addLog(`ℹ️ ${this.currentDate} 데이터가 없습니다. 먼저 데이터를 수집하세요.`, 'info');
            }

            this.addLog('💡 시스템 준비 완료. 원하는 작업을 선택하세요.', 'info');

        } catch (error) {
            console.error('초기 데이터 로드 실패:', error);
            this.addLog('❌ 초기 데이터 로드 중 오류가 발생했습니다.', 'error');
        }
    }

    /**
     * 🔥 분석 실행 (핵심 수정)
     */
    async startAnalysis() {
        try {
            this.addLog('🔍 분석을 시작합니다...', 'info');

            // 분석 버튼 비활성화
            if (this.elements.analyzeBtn) {
                this.elements.analyzeBtn.disabled = true;
                this.elements.analyzeBtn.textContent = '🔄 분석 중...';
            }

            // 기존 결과 초기화
            this.clearAnalysisResults();

            // API 호출로 분석 실행
            const response = await this.apiCall('/analyze', 'POST', {
                date: this.currentDate
            });

            if (response.success) {
                this.addLog(`📊 ${response.data.themes.length}개 테마 분석 완료`, 'success');

                // 테마 카드 표시
                this.displayThemeCards(response.data.themes);

                // 요약 정보 표시
                const summary = response.data.summary;
                this.addLog(`✅ 총 ${summary.total_themes}개 테마 중 ${summary.positive_themes}개 상승`, 'info');

                this.showToast('분석 완료!', 'success');
            } else {
                throw new Error(response.message || '분석 실패');
            }

        } catch (error) {
            console.error('분석 실행 실패:', error);
            this.addLog(`❌ 분석 실행 실패: ${error.message}`, 'error');
            this.showToast('분석 실행 중 오류가 발생했습니다.', 'error');
        } finally {
            // 분석 버튼 복원
            if (this.elements.analyzeBtn) {
                this.elements.analyzeBtn.disabled = false;
                this.elements.analyzeBtn.textContent = '📊 분석 실행';
            }
        }
    }

    /**
     * 🔥 테마 결과 로드 (신규 구현)
     */
    async loadThemeResults() {
        try {
            const response = await this.apiCall('/themes', 'GET', null, {
                date: this.currentDate
            });

            if (response.success && response.themes.length > 0) {
                this.displayThemeCards(response.themes);
                return true;
            } else {
                this.showEmptyState('분석 결과가 없습니다.');
                return false;
            }

        } catch (error) {
            console.error('테마 결과 로드 실패:', error);
            this.showEmptyState('테마 결과 로드 중 오류가 발생했습니다.');
            return false;
        }
    }

    /**
     * 🔥 테마 카드 표시 (신규 구현)
     */
    displayThemeCards(themes) {
        if (!this.elements.themeGrid) {
            console.error('themeGrid 요소를 찾을 수 없습니다');
            return;
        }

        this.elements.themeGrid.innerHTML = '';

        themes.forEach((theme, index) => {
            const card = this.createThemeCard(theme, index);
            this.elements.themeGrid.appendChild(card);
        });

        // 애니메이션 효과
        this.elements.themeGrid.classList.add('fade-in');
        setTimeout(() => {
            this.elements.themeGrid.classList.remove('fade-in');
        }, 500);
    }

    /**
     * 🔥 테마 카드 생성 (신규 구현)
     */
    createThemeCard(theme, index) {
        const card = document.createElement('div');
        card.className = 'theme-card';
        card.setAttribute('data-theme', theme.name);

        // 등락률에 따른 색상 클래스
        const changeClass = theme.change_rate > 0 ? 'positive' :
                           theme.change_rate < 0 ? 'negative' : 'neutral';

        card.innerHTML = `
            <div class="theme-header">
                <span class="theme-icon">${theme.icon || '📈'}</span>
                <h3 class="theme-name">${theme.name}</h3>
            </div>
            <div class="theme-stats">
                <div class="stat-item primary">
                    <span class="stat-label">등락률</span>
                    <span class="stat-value ${changeClass}">
                        ${theme.change_rate > 0 ? '+' : ''}${theme.change_rate.toFixed(2)}%
                    </span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">종목 수</span>
                    <span class="stat-value">${theme.stock_count}개</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">거래량 비율</span>
                    <span class="stat-value">${theme.volume_ratio.toFixed(1)}%</span>
                </div>
            </div>
            <div class="theme-footer">
                <small class="theme-index">#${index + 1}</small>
                <span class="click-hint">클릭하여 상세보기</span>
            </div>
        `;

        // 클릭 이벤트
        card.addEventListener('click', () => {
            this.openThemeModal(theme);
        });

        // 호버 효과
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-2px)';
        });

        card.addEventListener('mouseleave', () => {
            card.style.transform = 'translateY(0)';
        });

        return card;
    }

    /**
     * 데이터 수집 시작
     */
    async startDataCollection() {
        if (this.isCollecting) {
            this.showToast('이미 데이터 수집이 진행 중입니다.', 'warning');
            return;
        }

        try {
            this.isCollecting = true;
            this.elements.collectDataBtn.disabled = true;
            this.elements.progressSection.classList.remove('hidden');
            this.hideAnalyzeButton();

            // API 호출
            const response = await this.apiCall('/collect-data', 'POST', {
                date: this.currentDate
            });

            if (response.success) {
                this.addLog(`🚀 ${this.currentDate} 데이터 수집을 시작했습니다.`, 'info');
                this.startProgressMonitoring();
            } else {
                throw new Error(response.message || '데이터 수집 시작 실패');
            }

        } catch (error) {
            console.error('데이터 수집 시작 실패:', error);
            this.addLog(`❌ 데이터 수집 시작 실패: ${error.message}`, 'error');
            this.showToast('데이터 수집을 시작할 수 없습니다.', 'error');

            this.isCollecting = false;
            this.elements.collectDataBtn.disabled = false;
        }
    }

    /**
     * 진행상황 모니터링 시작
     */
    startProgressMonitoring() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
        }

        this.progressInterval = setInterval(async () => {
            try {
                const progress = await this.apiCall('/progress');

                if (progress) {
                    this.updateProgress(progress);

                    // 완료되면 모니터링 중지
                    if (!progress.is_running) {
                        clearInterval(this.progressInterval);
                        this.progressInterval = null;
                        this.onCollectionComplete(progress);
                    }
                }

            } catch (error) {
                console.error('진행상황 조회 실패:', error);
            }
        }, 1000);
    }

    /**
     * 진행상황 업데이트
     */
    updateProgress(progress) {
        const { percent, message, is_running } = progress;

        if (this.elements.progressFill) {
            this.elements.progressFill.style.width = `${percent}%`;
        }

        if (this.elements.progressPercent) {
            this.elements.progressPercent.textContent = `${Math.round(percent)}%`;
        }

        if (this.elements.progressText) {
            this.elements.progressText.textContent = message;
        }

        if (message && message !== this.lastProgressMessage) {
            const logType = percent === 100 ? 'success' : 'info';
            this.addLog(message, logType);
            this.lastProgressMessage = message;
        }
    }

    /**
     * 수집 완료 처리
     */
    async onCollectionComplete(progress) {
        this.isCollecting = false;
        this.elements.collectDataBtn.disabled = false;

        if (progress.success) {
            this.addLog('✅ 데이터 수집이 완료되었습니다!', 'success');
            this.showToast('데이터 수집 완료', 'success');
            this.showAnalyzeButton();
        } else {
            const errorMsg = progress.error_message || '알 수 없는 오류';
            this.addLog(`❌ 데이터 수집 실패: ${errorMsg}`, 'error');
            this.showToast('데이터 수집 실패', 'error');
        }
    }

    /**
     * 🔥 데이터 존재 여부 확인 (신규 구현)
     */
    async checkDataExists(date) {
        try {
            const response = await this.apiCall('/check-date-data', 'GET', null, { date });
            return response.success && response.has_data;
        } catch (error) {
            console.error('데이터 존재 확인 실패:', error);
            return false;
        }
    }

    /**
     * 날짜 변경 처리
     */
    async onDateChange() {
        try {
            this.addLog(`📅 분석 날짜를 ${this.currentDate}로 변경했습니다.`, 'info');

            // 기존 결과 초기화
            this.clearAnalysisResults();

            // 새 날짜 데이터 확인
            const hasData = await this.checkDataExists(this.currentDate);

            if (hasData) {
                this.showAnalyzeButton();
                await this.loadThemeResults();
                this.addLog(`💡 ${this.currentDate} 데이터가 있습니다. 분석 버튼을 클릭하세요.`, 'success');
            } else {
                this.hideAnalyzeButton();
                this.addLog(`ℹ️ ${this.currentDate} 데이터가 없습니다.`, 'info');
            }

        } catch (error) {
            console.error('날짜 변경 처리 실패:', error);
            this.addLog('❌ 날짜 변경 처리 중 오류가 발생했습니다.', 'error');
        }
    }

    /**
     * 🔥 테마 모달 열기 (신규 구현)
     */
    async openThemeModal(theme) {
        try {
            if (!this.elements.themeModal) {
                console.error('테마 모달 요소를 찾을 수 없습니다');
                return;
            }

            // 모달 제목 설정
            if (this.elements.modalTitle) {
                this.elements.modalTitle.textContent = theme.name;
            }

            if (this.elements.modalIcon) {
                this.elements.modalIcon.textContent = theme.icon || '📈';
            }

            // 테마 상세정보 로드
            const response = await this.apiCall('/theme-detail', 'GET', null, {
                date: this.currentDate,
                theme_name: theme.name
            });

            if (response.success && response.theme_detail) {
                this.displayThemeDetail(response.theme_detail);
            } else {
                // 기본 정보만 표시
                this.displayBasicThemeInfo(theme);
            }

            // 모달 표시
            this.elements.themeModal.style.display = 'flex';

            // 애니메이션
            setTimeout(() => {
                this.elements.themeModal.classList.add('show');
            }, 10);

        } catch (error) {
            console.error('테마 모달 열기 실패:', error);
            this.showToast('테마 상세정보를 불러올 수 없습니다.', 'error');
        }
    }

    /**
     * 🔥 테마 상세정보 표시 (신규 구현)
     */
    displayThemeDetail(themeDetail) {
        // 종목 리스트 표시
        if (this.elements.modalStockList && themeDetail.stocks) {
            this.elements.modalStockList.innerHTML = '';

            themeDetail.stocks.forEach((stock, index) => {
                const stockItem = document.createElement('div');
                stockItem.className = 'stock-item';

                const changeClass = stock.change_rate > 0 ? 'positive' :
                                   stock.change_rate < 0 ? 'negative' : 'neutral';

                stockItem.innerHTML = `
                    <div class="stock-info">
                        <span class="stock-rank">${index + 1}</span>
                        <span class="stock-name">${stock.stock_name}</span>
                        <span class="stock-code">(${stock.stock_code})</span>
                    </div>
                    <div class="stock-stats">
                        <span class="stock-price">${stock.current_price.toLocaleString()}원</span>
                        <span class="stock-change ${changeClass}">
                            ${stock.change_rate > 0 ? '+' : ''}${stock.change_rate.toFixed(2)}%
                        </span>
                    </div>
                `;

                this.elements.modalStockList.appendChild(stockItem);
            });
        }

        // 뉴스 리스트 표시 (있다면)
        if (this.elements.modalNewsList && themeDetail.news) {
            this.elements.modalNewsList.innerHTML = '';

            themeDetail.news.forEach(newsItem => {
                const newsElement = document.createElement('div');
                newsElement.className = 'news-item';
                newsElement.innerHTML = `
                    <h4 class="news-title">${newsItem.title}</h4>
                    <p class="news-summary">${newsItem.summary}</p>
                    <small class="news-date">${newsItem.date}</small>
                `;
                this.elements.modalNewsList.appendChild(newsElement);
            });
        }
    }

    /**
     * 🔥 기본 테마 정보 표시 (신규 구현)
     */
    displayBasicThemeInfo(theme) {
        if (this.elements.modalStockList) {
            this.elements.modalStockList.innerHTML = `
                <div class="info-message">
                    <h3>${theme.name} 테마 정보</h3>
                    <p>📊 등락률: ${theme.change_rate > 0 ? '+' : ''}${theme.change_rate.toFixed(2)}%</p>
                    <p>📈 종목 수: ${theme.stock_count}개</p>
                    <p>📦 거래량 비율: ${theme.volume_ratio.toFixed(1)}%</p>
                    <p class="note">상세 종목 정보는 준비 중입니다.</p>
                </div>
            `;
        }

        if (this.elements.modalNewsList) {
            this.elements.modalNewsList.innerHTML = `
                <div class="info-message">
                    <p>📰 관련 뉴스 정보는 준비 중입니다.</p>
                </div>
            `;
        }
    }

    /**
     * 모달 닫기
     */
    closeModal() {
        if (this.elements.themeModal) {
            this.elements.themeModal.classList.remove('show');
            setTimeout(() => {
                this.elements.themeModal.style.display = 'none';
            }, 300);
        }
    }

    /**
     * 스케줄 토글
     */
    toggleSchedule(toggleElement) {
        toggleElement.classList.toggle('active');
        const time = toggleElement.getAttribute('data-time');
        const isActive = toggleElement.classList.contains('active');
        const action = isActive ? '활성화' : '비활성화';

        this.addLog(`⏰ ${time} 자동 스케줄이 ${action}되었습니다.`, 'info');
    }

    /**
     * API 호출
     */
    async apiCall(endpoint, method = 'GET', body = null, params = null) {
        try {
            let url = `${this.apiPrefix}${endpoint}`;

            // GET 요청의 경우 쿼리 파라미터 추가
            if (params && method === 'GET') {
                const queryString = new URLSearchParams(params).toString();
                url += '?' + queryString;
            }

            const options = {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                },
            };

            // POST 요청의 경우 body 추가
            if (body && method !== 'GET') {
                options.body = JSON.stringify(body);
            }

            const response = await fetch(url, options);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();

        } catch (error) {
            console.error(`API 호출 실패 (${endpoint}):`, error);
            throw error;
        }
    }

    /**
     * 로그 추가
     */
    addLog(message, type = 'info') {
        if (!this.elements.logContainer) return;

        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${type}`;

        const timestamp = new Date().toLocaleTimeString();
        logEntry.textContent = `[${timestamp}] ${message}`;

        this.elements.logContainer.appendChild(logEntry);
        this.elements.logContainer.scrollTop = this.elements.logContainer.scrollHeight;

        // 로그가 너무 많아지면 오래된 것 제거
        const logs = this.elements.logContainer.children;
        if (logs.length > 100) {
            logs[0].remove();
        }
    }

    /**
     * 토스트 알림 표시
     */
    showToast(message, type = 'info', duration = 3000) {
        // 기존 토스트 제거
        const existingToast = document.querySelector('.toast');
        if (existingToast) {
            existingToast.remove();
        }

        // 새 토스트 생성
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;

        document.body.appendChild(toast);

        // 애니메이션 표시
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);

        // 자동 제거
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.remove();
                }
            }, 300);
        }, duration);
    }

    /**
     * 분석 버튼 표시
     */
    showAnalyzeButton() {
        if (this.elements.analyzeBtn) {
            this.elements.analyzeBtn.classList.remove('hidden');
        }
    }

    /**
     * 분석 버튼 숨기기
     */
    hideAnalyzeButton() {
        if (this.elements.analyzeBtn) {
            this.elements.analyzeBtn.classList.add('hidden');
        }
    }

    /**
     * 분석 결과 초기화
     */
    clearAnalysisResults() {
        if (this.elements.themeGrid) {
            this.elements.themeGrid.innerHTML = '';
        }
    }

    /**
     * 빈 상태 표시
     */
    showEmptyState(message = '데이터가 없습니다.') {
        if (this.elements.themeGrid) {
            this.elements.themeGrid.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📭</div>
                    <h3 class="empty-title">분석 결과 없음</h3>
                    <p class="empty-message">${message}</p>
                </div>
            `;
        }
    }

    /**
     * 정리 작업
     */
    cleanup() {
        // 진행상황 모니터링 중지
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }

        // 모달 닫기
        this.closeModal();

        console.log('🧹 TopRateAnalysis 정리 완료');
    }
}

// 전역 함수들 (HTML에서 직접 호출용)
window.closeModal = function() {
    if (window.topRateAnalysis) {
        window.topRateAnalysis.closeModal();
    }
};

window.openThemeModal = function(theme) {
    if (window.topRateAnalysis) {
        window.topRateAnalysis.openThemeModal(theme);
    }
};

// 페이지 로드 완료시 자동 초기화
document.addEventListener('DOMContentLoaded', function() {
    // 설정 확인
    if (!window.APP_CONFIG) {
        console.warn('⚠️ APP_CONFIG가 설정되지 않았습니다. 기본값을 사용합니다.');
        window.APP_CONFIG = {
            apiPrefix: '/top-rate/api',
            currentDate: new Date().toISOString().split('T')[0],
            availableDates: [],
            moduleName: '등락율상위분석',
            moduleVersion: '3.1.0'
        };
    }

    // TopRateAnalysis 초기화
    window.topRateAnalysis = TopRateAnalysis.init();

    // 개발자 도구 등록 (개발 환경에서만)
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        console.log('🛠️ 개발자 도구 활성화');
        window.topRateDebug = () => window.topRateAnalysis.debug();
        window.topRateTest = {
            showToast: (msg, type) => window.topRateAnalysis.showToast(msg, type),
            addLog: (msg, type) => window.topRateAnalysis.addLog(msg, type),
            loadThemes: () => window.topRateAnalysis.loadThemeResults(),
            checkData: (date) => window.topRateAnalysis.checkDataExists(date),
            analyze: () => window.topRateAnalysis.startAnalysis()
        };
    }

    console.log('🎉 등락율상위분석 모듈 로드 완료');
});

// 모듈 익스포트 (ES6 환경에서 사용 가능)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TopRateAnalysis;
}