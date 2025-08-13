/**
 * 등락율상위분석 JavaScript 모듈
 * - 실시간 데이터 수집 진행상황 추적
 * - 테마별 분석 결과 표시
 * - 스케줄 관리
 * - API 통신
 */

class TopRateAnalysis {
    constructor() {
        this.apiPrefix = window.APP_CONFIG?.apiPrefix || '/top-rate/api';
        this.currentDate = window.APP_CONFIG?.currentDate || new Date().toISOString().split('T')[0];
        this.isCollecting = false;
        this.progressInterval = null;

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

        // 분석 실행 버튼
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

        // 페이지 언로드시 정리
        window.addEventListener('beforeunload', () => {
            this.cleanup();
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
            }

            // 스케줄 상태 로드
            await this.loadScheduleStatus();

            this.addLog('💡 시스템 준비 완료. 원하는 작업을 선택하세요.', 'info');

        } catch (error) {
            console.error('초기 데이터 로드 실패:', error);
            this.addLog('❌ 초기 데이터 로드 중 오류가 발생했습니다.', 'error');
        }
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
                // 에러가 발생해도 계속 모니터링
            }
        }, 1000); // 1초마다 체크
    }

    /**
     * 진행상황 업데이트
     */
    updateProgress(progress) {
        const { percent, message, is_running } = progress;

        // 프로그레스바 업데이트
        if (this.elements.progressFill) {
            this.elements.progressFill.style.width = `${percent}%`;
        }

        if (this.elements.progressPercent) {
            this.elements.progressPercent.textContent = `${Math.round(percent)}%`;
        }

        if (this.elements.progressText) {
            this.elements.progressText.textContent = message;
        }

        // 진행상황이 변경되면 로그 추가
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
     * 분석 실행
     */
    async startAnalysis() {
        try {
            this.addLog('🔍 분석을 시작합니다...', 'info');

            // 분석 버튼 비활성화
            this.elements.analyzeBtn.disabled = true;

            // 테마 결과 로드
            await this.loadThemeResults();

            this.addLog('📊 테마별 분석 결과가 표시되었습니다.', 'success');
            this.showToast('분석 완료', 'success');

        } catch (error) {
            console.error('분석 실행 실패:', error);
            this.addLog(`❌ 분석 실행 실패: ${error.message}`, 'error');
            this.showToast('분석 실패', 'error');
        } finally {
            this.elements.analyzeBtn.disabled = false;
        }
    }

    /**
     * 테마 분석 결과 로드
     */
    async loadThemeResults() {
        try {
            const response = await this.apiCall('/theme-summary', 'GET', null, {
                date: this.currentDate
            });

            if (response.success) {
                this.displayThemeResults(response.themes);
            } else {
                throw new Error(response.message || '테마 데이터 로드 실패');
            }

        } catch (error) {
            console.error('테마 결과 로드 실패:', error);
            this.showEmptyState('테마 데이터를 불러올 수 없습니다.');
        }
    }

    /**
     * 테마 결과 표시
     */
    displayThemeResults(themes) {
        if (!this.elements.themeGrid) return;

        this.elements.themeGrid.innerHTML = '';

        if (!themes || themes.length === 0) {
            this.showEmptyState('분석할 테마 데이터가 없습니다.');
            return;
        }

        themes.forEach(theme => {
            const themeCard = this.createThemeCard(theme);
            this.elements.themeGrid.appendChild(themeCard);
        });

        // 애니메이션 효과
        this.elements.themeGrid.classList.add('fade-in');
    }

    /**
     * 테마 카드 생성
     */
    createThemeCard(theme) {
        const card = document.createElement('div');
        card.className = 'theme-card';
        card.onclick = () => this.openThemeModal(theme);

        const changeClass = theme.avg_change_rate > 0 ? 'positive' : 'negative';
        const changeSign = theme.avg_change_rate > 0 ? '+' : '';
        const risingRatio = theme.stock_count > 0 ? (theme.rising_stocks / theme.stock_count * 100) : 0;

        card.innerHTML = `
            <div class="theme-header">
                <div class="theme-name">
                    <span class="theme-icon">${theme.icon || '📊'}</span>
                    ${theme.theme_name}
                </div>
                <div class="theme-change ${changeClass}">
                    ${changeSign}${theme.avg_change_rate.toFixed(1)}%
                </div>
            </div>

            <div class="theme-stats">
                <div class="stat-item">
                    <span class="stat-value">${theme.stock_count}</span>
                    <span class="stat-label">종목수</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">${theme.total_news || 0}</span>
                    <span class="stat-label">뉴스</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">${changeSign}${theme.max_change_rate.toFixed(1)}%</span>
                    <span class="stat-label">최고상승</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">${theme.rising_stocks}/${theme.stock_count}</span>
                    <span class="stat-label">상승종목</span>
                </div>
            </div>

            <div class="theme-top-stock">
                <div class="top-stock-title">🏆 대표종목</div>
                <div class="top-stock-name">${theme.top_stock || '정보 없음'}</div>
            </div>
        `;

        return card;
    }

    /**
     * 테마 상세 모달 열기
     */
    async openThemeModal(theme) {
        try {
            // 상세 정보 로드
            const response = await this.apiCall('/theme-detail', 'GET', null, {
                date: this.currentDate,
                theme_name: theme.theme_name
            });

            if (!response.success) {
                throw new Error(response.message || '상세 정보 로드 실패');
            }

            const themeDetail = response.theme_detail;

            // 모달 제목 설정
            if (this.elements.modalTitle) {
                this.elements.modalIcon.textContent = theme.icon || '📊';
                this.elements.modalTitle.innerHTML = `${theme.icon || '📊'} ${theme.theme_name} 테마 상세분석`;
            }

            // 종목 리스트 생성
            this.displayStockList(themeDetail.stocks || []);

            // 뉴스 리스트 생성
            this.displayNewsList(themeDetail.news || []);

            // 모달 표시
            if (this.elements.themeModal) {
                this.elements.themeModal.style.display = 'block';
                document.body.style.overflow = 'hidden'; // 스크롤 방지
            }

        } catch (error) {
            console.error('테마 상세정보 로드 실패:', error);
            this.showToast('상세 정보를 불러올 수 없습니다.', 'error');
        }
    }

    /**
     * 종목 리스트 표시
     */
    displayStockList(stocks) {
        if (!this.elements.modalStockList) return;

        this.elements.modalStockList.innerHTML = '';

        stocks.forEach(stock => {
            const stockItem = document.createElement('div');
            stockItem.className = 'stock-item';

            const changeClass = stock.change_rate > 0 ? 'positive' : 'negative';
            const changeSign = stock.change_rate > 0 ? '+' : '';

            stockItem.innerHTML = `
                <div class="stock-info">
                    <div class="stock-name">${stock.stock_name}</div>
                    <div class="stock-price">${this.formatNumber(stock.price)}원</div>
                </div>
                <div class="stock-change ${changeClass}">
                    ${changeSign}${stock.change_rate.toFixed(1)}%
                </div>
            `;

            this.elements.modalStockList.appendChild(stockItem);
        });
    }

    /**
     * 뉴스 리스트 표시
     */
    displayNewsList(news) {
        if (!this.elements.modalNewsList) return;

        this.elements.modalNewsList.innerHTML = '';

        if (!news || news.length === 0) {
            this.elements.modalNewsList.innerHTML = '<div class="empty-state">관련 뉴스가 없습니다.</div>';
            return;
        }

        news.slice(0, 10).forEach(newsItem => { // 최대 10개만 표시
            const newsElement = document.createElement('div');
            newsElement.className = 'news-item';

            const title = newsItem.title || newsItem;
            newsElement.innerHTML = `<div class="news-title">${title}</div>`;

            this.elements.modalNewsList.appendChild(newsElement);
        });
    }

    /**
     * 모달 닫기
     */
    closeModal() {
        if (this.elements.themeModal) {
            this.elements.themeModal.style.display = 'none';
            document.body.style.overflow = ''; // 스크롤 복원
        }
    }

    /**
     * 스케줄 토글
     */
    async toggleSchedule(toggleElement) {
        const time = toggleElement.getAttribute('data-time');

        try {
            const response = await this.apiCall('/toggle-schedule', 'POST', {
                time: time
            });

            if (response.success) {
                const isActive = response.enabled;
                toggleElement.classList.toggle('active', isActive);

                const action = isActive ? '활성화' : '비활성화';
                this.addLog(`⏰ ${time} 자동 스케줄이 ${action}되었습니다.`, 'info');
                this.showToast(`스케줄 ${action}`, isActive ? 'success' : 'info');
            } else {
                throw new Error(response.message || '스케줄 토글 실패');
            }

        } catch (error) {
            console.error('스케줄 토글 실패:', error);
            this.showToast('스케줄 변경에 실패했습니다.', 'error');
        }
    }

    /**
     * 스케줄 상태 로드
     */
    async loadScheduleStatus() {
        try {
            const response = await this.apiCall('/schedules');

            if (response.success) {
                response.schedules.forEach(schedule => {
                    const toggleElement = document.querySelector(`[data-time="${schedule.time}"]`);
                    if (toggleElement) {
                        toggleElement.classList.toggle('active', schedule.enabled);
                    }
                });
            }

        } catch (error) {
            console.error('스케줄 상태 로드 실패:', error);
        }
    }

    /**
     * 날짜 변경 처리
     */
    async onDateChange() {
        this.addLog(`📅 분석 날짜가 ${this.currentDate}로 변경되었습니다.`, 'info');

        // 분석 결과 초기화
        this.clearAnalysisResults();
        this.hideAnalyzeButton();

        // 해당 날짜의 데이터 존재 여부 확인
        const hasData = await this.checkDataExists(this.currentDate);

        if (hasData) {
            this.showAnalyzeButton();
            this.addLog('💡 해당 날짜의 데이터가 있습니다. 분석 버튼을 클릭하세요.', 'info');
        } else {
            this.addLog('ℹ️ 해당 날짜의 데이터가 없습니다. 먼저 데이터를 수집하세요.', 'info');
        }
    }

    /**
     * 데이터 존재 여부 확인
     */
    async checkDataExists(date) {
        try {
            const response = await this.apiCall('/crawling-status', 'GET', null, { date });
            return response.success && response.status.exists && response.status.total_stocks > 0;
        } catch (error) {
            console.error('데이터 존재 확인 실패:', error);
            return false;
        }
    }

    /**
     * API 호출
     */
    async apiCall(endpoint, method = 'GET', body = null, params = null) {
        try {
            let url = this.apiPrefix + endpoint;

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
        if (!this.elements.themeGrid) return;

        this.elements.themeGrid.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-chart-line"></i>
                <h3>분석 결과 없음</h3>
                <p>${message}</p>
            </div>
        `;
    }

    /**
     * 에러 상태 표시
     */
    showErrorState(message = '오류가 발생했습니다.') {
        if (!this.elements.themeGrid) return;

        this.elements.themeGrid.innerHTML = `
            <div class="error-state">
                <i class="fas fa-exclamation-triangle"></i>
                <h3>오류 발생</h3>
                <p>${message}</p>
                <button class="btn btn-primary" onclick="window.topRateAnalysis.loadThemeResults()">
                    <i class="fas fa-refresh"></i>
                    다시 시도
                </button>
            </div>
        `;
    }

    /**
     * 숫자 포맷팅
     */
    formatNumber(num) {
        if (typeof num !== 'number') return num;
        return num.toLocaleString('ko-KR');
    }

    /**
     * 날짜 포맷팅
     */
    formatDate(dateStr) {
        const date = new Date(dateStr);
        return date.toLocaleDateString('ko-KR', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }

    /**
     * 퍼센트 포맷팅
     */
    formatPercent(value, decimals = 1) {
        if (typeof value !== 'number') return value;
        const sign = value > 0 ? '+' : '';
        return `${sign}${value.toFixed(decimals)}%`;
    }

    /**
     * 디바운스 함수
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * 스로틀 함수
     */
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    /**
     * 로컬 스토리지 유틸리티
     */
    saveToStorage(key, value) {
        try {
            localStorage.setItem(`top_rate_${key}`, JSON.stringify(value));
        } catch (error) {
            console.warn('로컬 스토리지 저장 실패:', error);
        }
    }

    loadFromStorage(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(`top_rate_${key}`);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.warn('로컬 스토리지 로드 실패:', error);
            return defaultValue;
        }
    }

    /**
     * 설정 저장/로드
     */
    saveSettings() {
        const settings = {
            currentDate: this.currentDate,
            lastUpdate: new Date().toISOString()
        };
        this.saveToStorage('settings', settings);
    }

    loadSettings() {
        const settings = this.loadFromStorage('settings', {});
        if (settings.currentDate) {
            this.currentDate = settings.currentDate;
            if (this.elements.analysisDate) {
                this.elements.analysisDate.value = this.currentDate;
            }
        }
    }

    /**
     * 에러 처리
     */
    handleError(error, context = '') {
        console.error(`${context} 오류:`, error);

        const errorMessage = error.message || '알 수 없는 오류가 발생했습니다.';
        this.addLog(`❌ ${context} ${errorMessage}`, 'error');

        // 사용자에게 친화적인 메시지 표시
        let userMessage = errorMessage;

        if (error.message?.includes('network') || error.message?.includes('fetch')) {
            userMessage = '네트워크 연결을 확인해주세요.';
        } else if (error.message?.includes('timeout')) {
            userMessage = '요청 시간이 초과되었습니다. 다시 시도해주세요.';
        } else if (error.message?.includes('404')) {
            userMessage = '요청한 리소스를 찾을 수 없습니다.';
        } else if (error.message?.includes('500')) {
            userMessage = '서버 오류가 발생했습니다.';
        }

        this.showToast(userMessage, 'error');
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

        // 설정 저장
        this.saveSettings();

        // 모달 닫기
        this.closeModal();

        console.log('🧹 TopRateAnalysis 정리 완료');
    }

    /**
     * 개발자 도구용 디버그 함수들
     */
    debug() {
        return {
            version: '3.0.0',
            currentDate: this.currentDate,
            isCollecting: this.isCollecting,
            apiPrefix: this.apiPrefix,
            elements: Object.keys(this.elements),
            progressInterval: !!this.progressInterval
        };
    }

    // 개발자 도구에서 사용할 수 있도록 전역 함수 등록
    registerGlobalMethods() {
        if (window.console && typeof window.console.log === 'function') {
            window.topRateDebug = () => this.debug();
            window.topRateTest = {
                showToast: (msg, type) => this.showToast(msg, type),
                addLog: (msg, type) => this.addLog(msg, type),
                loadThemes: () => this.loadThemeResults(),
                checkData: (date) => this.checkDataExists(date)
            };
        }
    }
}

// 전역 함수들 (HTML에서 직접 호출용)
window.closeModal = function() {
    if (window.topRateAnalysis) {
        window.topRateAnalysis.closeModal();
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
            moduleVersion: '3.0.0'
        };
    }

    // TopRateAnalysis 초기화
    window.topRateAnalysis = TopRateAnalysis.init();

    // 개발자 도구 등록 (개발 환경에서만)
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        window.topRateAnalysis.registerGlobalMethods();
        console.log('🛠️ 개발자 도구 활성화: window.topRateDebug(), window.topRateTest');
    }

    console.log('🎉 등락율상위분석 모듈 로드 완료');
});

// 모듈 익스포트 (ES6 환경에서 사용 가능)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TopRateAnalysis;
}