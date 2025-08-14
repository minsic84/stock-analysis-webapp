/**
 * 등락율상위분석 실제 프론트엔드 (paste.txt 기반 완전 구현)
 * - 실제 크롤링 실행 및 모니터링
 * - 실제 데이터 기반 테마 카드 표시
 * - 실시간 시스템 상태 모니터링
 * - 테마 상세 모달
 */

class TopRateAnalysis {
    constructor() {
        this.apiPrefix = window.APP_CONFIG?.apiPrefix || '/top-rate/api';
        this.currentDate = window.APP_CONFIG?.currentDate || new Date().toISOString().split('T')[0];
        
        // 상태 관리
        this.isCollecting = false;
        this.isAnalyzing = false;
        this.progressInterval = null;
        this.systemMonitorInterval = null;
        
        // 캐시
        this.themeResults = [];
        this.systemStatus = {};
        
        this.elements = {};
        this.initElements();
        this.setupEventListeners();
        this.loadInitialData();
        this.startSystemMonitoring();

        console.log('🚀 TopRateAnalysis 초기화 완료 (실제 데이터 모드)');
    }

    static init() {
        return new TopRateAnalysis();
    }

    // ============= 초기화 =============

    initElements() {
        this.elements = {
            // 메인 컨트롤
            collectDataBtn: document.getElementById('collectDataBtn'),
            analyzeBtn: document.getElementById('analyzeBtn'),
            analysisDate: document.getElementById('analysisDate'),
            
            // 진행상황
            progressSection: document.getElementById('progressSection'),
            progressFill: document.getElementById('progressFill'),
            progressText: document.getElementById('progressText'),
            progressPercent: document.getElementById('progressPercent'),
            
            // 결과 표시
            themeGrid: document.getElementById('themeGrid'),
            themeModal: document.getElementById('themeModal'),
            modalContent: document.getElementById('modalContent'),
            
            // 로그 및 모니터링
            logContainer: document.getElementById('logContainer'),
            systemStatus: document.getElementById('systemStatus'),
            
            // 상태 표시
            dbStatus: document.getElementById('dbStatus'),
            crawlingStatus: document.getElementById('crawlingStatus'),
            lastUpdate: document.getElementById('lastUpdate')
        };
    }

    setupEventListeners() {
        // 🚀 실제 데이터 수집 버튼
        if (this.elements.collectDataBtn) {
            this.elements.collectDataBtn.addEventListener('click', () => {
                this.startRealDataCollection();
            });
        }

        // 📊 실제 분석 실행 버튼
        if (this.elements.analyzeBtn) {
            this.elements.analyzeBtn.addEventListener('click', () => {
                this.startRealAnalysis();
            });
        }

        // 📅 날짜 변경
        if (this.elements.analysisDate) {
            this.elements.analysisDate.addEventListener('change', (e) => {
                this.currentDate = e.target.value;
                this.onDateChange();
            });
        }

        // 🔄 새로고침 (Ctrl+R)
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'r') {
                e.preventDefault();
                this.refreshData();
            }
            if (e.key === 'Escape') {
                this.closeModal();
            }
        });

        // 📱 윈도우 리사이즈
        window.addEventListener('resize', () => {
            this.adjustLayout();
        });
    }

    // ============= 🚀 실제 데이터 수집 =============

    async startRealDataCollection() {
        if (this.isCollecting) {
            this.showToast('이미 데이터 수집이 진행 중입니다.', 'warning');
            return;
        }

        try {
            this.isCollecting = true;
            this.elements.collectDataBtn.disabled = true;
            this.elements.collectDataBtn.textContent = '수집 중...';

            this.addLog('🚀 실제 데이터 수집을 시작합니다...', 'info');
            this.showProgressSection();

            // 실제 크롤링 시작 요청
            const response = await this.apiCall('/collect-data', 'POST', {
                date: this.currentDate
            });

            if (response.success) {
                this.addLog(`✅ ${response.target_date} 데이터 수집이 시작되었습니다.`, 'success');
                this.startProgressMonitoring();
            } else {
                throw new Error(response.message);
            }

        } catch (error) {
            this.addLog(`❌ 데이터 수집 시작 실패: ${error.message}`, 'error');
            this.showToast('데이터 수집 시작 실패', 'error');
            this.resetCollectionState();
        }
    }

    startProgressMonitoring() {
        this.progressInterval = setInterval(async () => {
            try {
                const response = await this.apiCall('/crawling-progress');
                
                if (response.success) {
                    this.updateProgress(response.progress);
                    
                    // 완료 확인
                    if (!response.progress.is_running) {
                        this.onCollectionComplete(response.progress);
                        clearInterval(this.progressInterval);
                        this.progressInterval = null;
                    }
                }
            } catch (error) {
                console.error('진행상황 모니터링 실패:', error);
                this.addLog('⚠️ 진행상황 모니터링 중 오류 발생', 'warning');
            }
        }, 2000); // 2초마다 확인
    }

    updateProgress(progress) {
        // 진행률 업데이트
        if (this.elements.progressFill) {
            this.elements.progressFill.style.width = `${progress.percent}%`;
        }
        
        if (this.elements.progressPercent) {
            this.elements.progressPercent.textContent = `${progress.percent}%`;
        }
        
        if (this.elements.progressText) {
            this.elements.progressText.textContent = progress.message;
        }

        // 진행상황 로그 (중복 방지)
        if (progress.message !== this.lastProgressMessage) {
            const logType = progress.percent === 100 ? 'success' : 'info';
            this.addLog(`[${progress.percent}%] ${progress.message}`, logType);
            this.lastProgressMessage = progress.message;
        }

        // 테마별 상세 진행상황
        if (progress.current_theme) {
            const detail = `${progress.current_theme} (${progress.processed_themes}/${progress.total_themes})`;
            this.addLog(`    📋 ${detail}`, 'info');
        }
    }

    onCollectionComplete(progress) {
        this.resetCollectionState();

        if (progress.success) {
            this.addLog('🎉 실제 데이터 수집이 완료되었습니다!', 'success');
            this.showToast('데이터 수집 완료', 'success');
            this.showAnalyzeButton();
            
            // 시스템 상태 새로고침
            this.refreshSystemStatus();
        } else {
            const errorMsg = progress.error_message || '알 수 없는 오류';
            this.addLog(`❌ 데이터 수집 실패: ${errorMsg}`, 'error');
            this.showToast('데이터 수집 실패', 'error');
        }
    }

    resetCollectionState() {
        this.isCollecting = false;
        if (this.elements.collectDataBtn) {
            this.elements.collectDataBtn.disabled = false;
            this.elements.collectDataBtn.textContent = '📡 데이터 수집';
        }
    }

    // ============= 📊 실제 데이터 분석 =============

    async startRealAnalysis() {
        if (this.isAnalyzing) {
            this.showToast('이미 분석이 진행 중입니다.', 'warning');
            return;
        }

        try {
            this.isAnalyzing = true;
            this.elements.analyzeBtn.disabled = true;
            this.elements.analyzeBtn.textContent = '분석 중...';

            this.addLog('📊 실제 데이터 분석을 시작합니다...', 'info');

            // 실제 분석 요청
            const response = await this.apiCall('/analyze', 'POST', {
                date: this.currentDate
            });

            if (response.success) {
                this.addLog(`✅ ${response.date} 분석이 완료되었습니다.`, 'success');
                this.displayAnalysisResults(response);
                this.showToast('분석 완료', 'success');
            } else {
                throw new Error(response.message);
            }

        } catch (error) {
            this.addLog(`❌ 데이터 분석 실패: ${error.message}`, 'error');
            this.showToast('데이터 분석 실패', 'error');
        } finally {
            this.isAnalyzing = false;
            if (this.elements.analyzeBtn) {
                this.elements.analyzeBtn.disabled = false;
                this.elements.analyzeBtn.textContent = '📊 분석 실행';
            }
        }
    }

    displayAnalysisResults(data) {
        this.themeResults = data.themes;
        
        // 분석 요약 표시
        this.displayAnalysisSummary(data.summary);
        
        // 테마 카드 렌더링
        this.renderThemeCards(data.themes);
        
        // 분석 완료 로그
        const summary = data.summary;
        this.addLog(`📈 분석 요약: ${summary.total_themes}개 테마, ${summary.total_stocks}개 종목`, 'success');
        this.addLog(`🔥 HOT 테마: ${summary.hot_themes}개, 평균 등락률: ${summary.avg_change_rate}%`, 'success');
    }

    displayAnalysisSummary(summary) {
        // 요약 정보를 상단에 표시
        const summaryHtml = `
            <div class="analysis-summary">
                <div class="summary-item">
                    <span class="label">분석 날짜:</span>
                    <span class="value">${summary.date}</span>
                </div>
                <div class="summary-item">
                    <span class="label">총 테마:</span>
                    <span class="value">${summary.total_themes}개</span>
                </div>
                <div class="summary-item">
                    <span class="label">총 종목:</span>
                    <span class="value">${summary.total_stocks}개</span>
                </div>
                <div class="summary-item">
                    <span class="label">평균 등락률:</span>
                    <span class="value ${summary.avg_change_rate >= 0 ? 'positive' : 'negative'}">
                        ${summary.avg_change_rate >= 0 ? '+' : ''}${summary.avg_change_rate}%
                    </span>
                </div>
                <div class="summary-item">
                    <span class="label">HOT 테마:</span>
                    <span class="value hot">${summary.hot_themes}개</span>
                </div>
            </div>
        `;

        // 결과 영역에 요약 추가
        const resultsSection = document.querySelector('.analysis-results');
        if (resultsSection) {
            resultsSection.insertAdjacentHTML('afterbegin', summaryHtml);
        }
    }

    renderThemeCards(themes) {
        if (!this.elements.themeGrid) return;

        if (themes.length === 0) {
            this.showEmptyState('분석할 테마가 없습니다.');
            return;
        }

        const cardsHtml = themes.map(theme => this.createThemeCard(theme)).join('');
        this.elements.themeGrid.innerHTML = cardsHtml;

        // 카드 클릭 이벤트 추가
        this.elements.themeGrid.querySelectorAll('.theme-card').forEach(card => {
            card.addEventListener('click', () => {
                const themeName = card.dataset.theme;
                this.openThemeModal(themeName);
            });
        });

        this.addLog(`🎴 ${themes.length}개 테마 카드를 표시했습니다.`, 'info');
    }

    createThemeCard(theme) {
        const strengthClass = theme.strength.toLowerCase();
        const changeRateClass = theme.avg_change_rate >= 0 ? 'positive' : 'negative';
        
        return `
            <div class="theme-card ${strengthClass}" data-theme="${theme.theme_name}">
                <div class="card-header">
                    <div class="theme-info">
                        <span class="theme-icon">${theme.icon}</span>
                        <span class="theme-name">${theme.theme_name}</span>
                        <span class="theme-rank">#${theme.rank}</span>
                    </div>
                    <div class="theme-strength ${strengthClass}">${theme.strength}</div>
                </div>
                
                <div class="card-content">
                    <div class="main-stats">
                        <div class="stock-count">
                            <span class="label">📊 종목</span>
                            <span class="value">${theme.stock_count}개</span>
                        </div>
                        <div class="change-rate">
                            <span class="label">📈 등락률</span>
                            <span class="value ${changeRateClass}">
                                ${theme.avg_change_rate >= 0 ? '+' : ''}${theme.avg_change_rate}%
                            </span>
                        </div>
                    </div>
                    
                    <div class="progress-section">
                        <div class="progress-info">
                            <span>🔥 상승 ${theme.positive_stocks}/${theme.stock_count}</span>
                            <span class="percentage">(${theme.positive_ratio}%)</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${theme.positive_ratio}%"></div>
                        </div>
                    </div>
                    
                    <div class="additional-stats">
                        <div class="stat">
                            <span class="label">💰 거래량:</span>
                            <span class="value">${this.formatNumber(theme.total_volume)}</span>
                        </div>
                        <div class="stat">
                            <span class="label">📰 뉴스:</span>
                            <span class="value">${theme.avg_news_count}개/종목</span>
                        </div>
                    </div>
                </div>
                
                <div class="card-actions">
                    <button class="action-btn primary" onclick="event.stopPropagation(); window.topRateAnalysis.openThemeModal('${theme.theme_name}')">
                        👀 상세보기
                    </button>
                    <button class="action-btn secondary" onclick="event.stopPropagation(); window.topRateAnalysis.addToWatchlist('${theme.theme_name}')">
                        ⭐ 관심등록
                    </button>
                </div>
            </div>
        `;
    }

    // ============= 🎪 테마 상세 모달 =============

    async openThemeModal(themeName) {
        try {
            this.addLog(`🔍 ${themeName} 상세 정보를 조회합니다...`, 'info');

            // 실제 테마 상세 정보 요청
            const response = await this.apiCall('/theme-detail', 'GET', null, {
                theme: themeName,
                date: this.currentDate
            });

            if (response.success) {
                this.displayThemeModal(response.theme_detail);
            } else {
                throw new Error(response.message);
            }

        } catch (error) {
            this.addLog(`❌ ${themeName} 상세 정보 조회 실패: ${error.message}`, 'error');
            this.showToast('상세 정보 조회 실패', 'error');
        }
    }

    displayThemeModal(themeDetail) {
        if (!this.elements.themeModal) return;

        const modalHtml = `
            <div class="modal-overlay active" onclick="window.topRateAnalysis.closeModal()">
                <div class="modal-content" onclick="event.stopPropagation()">
                    <div class="modal-header">
                        <div class="modal-title">
                            <span class="theme-icon">${themeDetail.icon}</span>
                            <span class="theme-name">${themeDetail.theme_name}</span>
                            <span class="theme-date">${themeDetail.date}</span>
                        </div>
                        <button class="modal-close" onclick="window.topRateAnalysis.closeModal()">✕</button>
                    </div>
                    
                    <div class="modal-body">
                        <!-- 테마 요약 -->
                        <div class="theme-summary">
                            <div class="summary-stats">
                                <div class="stat-item">
                                    <span class="stat-label">총 종목</span>
                                    <span class="stat-value">${themeDetail.summary.total_stocks}개</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-label">상승 종목</span>
                                    <span class="stat-value positive">${themeDetail.summary.positive_stocks}개 (${themeDetail.summary.positive_ratio}%)</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-label">평균 등락률</span>
                                    <span class="stat-value ${themeDetail.summary.avg_change_rate >= 0 ? 'positive' : 'negative'}">
                                        ${themeDetail.summary.avg_change_rate >= 0 ? '+' : ''}${themeDetail.summary.avg_change_rate}%
                                    </span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-label">총 거래량</span>
                                    <span class="stat-value">${this.formatNumber(themeDetail.summary.total_volume)}</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-label">관련 뉴스</span>
                                    <span class="stat-value">${themeDetail.summary.total_news}개</span>
                                </div>
                            </div>
                        </div>
                        
                        <!-- 종목 리스트 -->
                        <div class="stocks-section">
                            <h3>📈 포함 종목 (${themeDetail.stocks.length}개)</h3>
                            <div class="stocks-table">
                                <div class="table-header">
                                    <span class="col-rank">순위</span>
                                    <span class="col-name">종목명</span>
                                    <span class="col-code">코드</span>
                                    <span class="col-price">현재가</span>
                                    <span class="col-change">등락률</span>
                                    <span class="col-volume">거래량</span>
                                    <span class="col-news">뉴스</span>
                                </div>
                                <div class="table-body">
                                    ${this.renderStockRows(themeDetail.stocks)}
                                </div>
                            </div>
                        </div>
                        
                        <!-- 최신 뉴스 -->
                        <div class="news-section">
                            <h3>📰 최신 뉴스 (${themeDetail.recent_news.length}개)</h3>
                            <div class="news-list">
                                ${this.renderNewsList(themeDetail.recent_news)}
                            </div>
                        </div>
                    </div>
                    
                    <div class="modal-footer">
                        <button class="btn secondary" onclick="window.topRateAnalysis.closeModal()">닫기</button>
                        <button class="btn primary" onclick="window.topRateAnalysis.addToWatchlist('${themeDetail.theme_name}')">⭐ 관심등록</button>
                        <button class="btn info" onclick="window.topRateAnalysis.refreshThemeDetail('${themeDetail.theme_name}')">🔄 새로고침</button>
                    </div>
                </div>
            </div>
        `;

        // 모달 표시
        this.elements.themeModal.innerHTML = modalHtml;
        this.elements.themeModal.style.display = 'block';
        document.body.style.overflow = 'hidden';

        this.addLog(`📋 ${themeDetail.theme_name} 상세 정보를 표시했습니다.`, 'success');
    }

    renderStockRows(stocks) {
        return stocks.map(stock => {
            const changeClass = stock.change_rate >= 0 ? 'positive' : 'negative';
            const changeSign = stock.change_rate >= 0 ? '+' : '';
            
            return `
                <div class="table-row ${changeClass}">
                    <span class="col-rank">${stock.rank}</span>
                    <span class="col-name">
                        <strong>${stock.stock_name}</strong>
                    </span>
                    <span class="col-code">${stock.stock_code}</span>
                    <span class="col-price">${this.formatNumber(stock.current_price)}원</span>
                    <span class="col-change ${changeClass}">
                        ${changeSign}${stock.change_rate}%
                    </span>
                    <span class="col-volume">${this.formatNumber(stock.volume)}</span>
                    <span class="col-news">${stock.news_count}개</span>
                </div>
            `;
        }).join('');
    }

    renderNewsList(newsList) {
        if (newsList.length === 0) {
            return '<div class="no-news">최신 뉴스가 없습니다.</div>';
        }

        return newsList.map(news => `
            <div class="news-item">
                <div class="news-header">
                    <span class="news-time ${news.is_today ? 'today' : 'yesterday'}">
                        ${news.time}
                    </span>
                    <span class="news-source">${news.source}</span>
                </div>
                <div class="news-title">
                    <a href="${news.url}" target="_blank" rel="noopener noreferrer">
                        ${news.title}
                    </a>
                </div>
            </div>
        `).join('');
    }

    closeModal() {
        if (this.elements.themeModal) {
            this.elements.themeModal.style.display = 'none';
            this.elements.themeModal.innerHTML = '';
        }
        document.body.style.overflow = 'auto';
    }

    // ============= 📅 날짜 관리 =============

    async onDateChange() {
        try {
            this.addLog(`📅 분석 날짜를 ${this.currentDate}로 변경했습니다.`, 'info');

            // 기존 결과 초기화
            this.clearAnalysisResults();

            // 새 날짜 데이터 확인
            const hasData = await this.checkDataExists(this.currentDate);

            if (hasData) {
                this.showAnalyzeButton();
                this.addLog(`💡 ${this.currentDate} 데이터가 있습니다. 분석 버튼을 클릭하세요.`, 'success');
                
                // 기존 분석 결과가 있다면 자동 로드
                this.loadExistingAnalysis();
            } else {
                this.hideAnalyzeButton();
                this.addLog(`ℹ️ ${this.currentDate} 데이터가 없습니다. 먼저 데이터를 수집하세요.`, 'info');
            }

        } catch (error) {
            console.error('날짜 변경 처리 실패:', error);
            this.addLog('❌ 날짜 변경 처리 중 오류가 발생했습니다.', 'error');
        }
    }

    async checkDataExists(date) {
        try {
            const response = await this.apiCall('/check-date-data', 'GET', null, { date });
            return response.success && response.has_data;
        } catch (error) {
            console.error('데이터 존재 확인 실패:', error);
            return false;
        }
    }

    async loadExistingAnalysis() {
        try {
            // 기존 분석 결과가 있는지 확인하고 자동 로드
            const response = await this.apiCall('/daily-summary', 'GET', null, {
                date: this.currentDate
            });

            if (response.success) {
                this.addLog('📊 기존 분석 결과를 불러왔습니다.', 'info');
                // 요약 정보만 표시 (전체 분석은 사용자가 버튼 클릭시)
                this.displayQuickSummary(response.daily_summary);
            }
        } catch (error) {
            // 기존 분석 결과가 없어도 문제 없음
            console.log('기존 분석 결과 없음:', error);
        }
    }

    displayQuickSummary(summary) {
        const summaryText = `${summary.total_themes}개 테마, ${summary.total_stocks}개 종목 (평균 ${summary.avg_change_rate}%)`;
        this.addLog(`📊 기존 분석: ${summaryText}`, 'info');
    }

    // ============= 🖥️ 시스템 모니터링 =============

    startSystemMonitoring() {
        // 초기 상태 로드
        this.refreshSystemStatus();

        // 30초마다 시스템 상태 확인
        this.systemMonitorInterval = setInterval(() => {
            this.refreshSystemStatus();
        }, 30000);
    }

    async refreshSystemStatus() {
        try {
            const response = await this.apiCall('/system-status');
            
            if (response.success) {
                this.systemStatus = response.system_status;
                this.updateSystemStatusDisplay();
            }
        } catch (error) {
            console.error('시스템 상태 조회 실패:', error);
            this.updateSystemStatusDisplay(true);
        }
    }

    updateSystemStatusDisplay(isError = false) {
        // DB 상태
        if (this.elements.dbStatus) {
            const dbStatus = isError ? 'error' : (this.systemStatus.database?.status || 'unknown');
            this.elements.dbStatus.className = `status-indicator ${dbStatus}`;
            this.elements.dbStatus.title = isError ? 'DB 연결 오류' : 
                `DB 상태: ${dbStatus} (응답시간: ${this.systemStatus.database?.response_time || 'N/A'})`;
        }

        // 크롤링 상태
        if (this.elements.crawlingStatus) {
            const isRunning = this.systemStatus.crawling?.is_running || false;
            this.elements.crawlingStatus.className = `status-indicator ${isRunning ? 'running' : 'idle'}`;
            this.elements.crawlingStatus.title = isRunning ? '크롤링 실행 중' : '크롤링 대기 중';
        }

        // 마지막 업데이트
        if (this.elements.lastUpdate) {
            const lastUpdate = this.systemStatus.latest_data?.last_update || 'N/A';
            this.elements.lastUpdate.textContent = lastUpdate;
        }

        // 시스템 상태 요약 로그
        if (!isError && this.systemStatus.latest_data) {
            const data = this.systemStatus.latest_data;
            this.addLog(`💻 시스템 상태: ${data.stock_count}개 종목, ${data.theme_count}개 테마 (최종: ${data.last_update})`, 'info');
        }
    }

    // ============= 🔧 유틸리티 함수 =============

    async apiCall(endpoint, method = 'GET', data = null, params = null) {
        const url = new URL(`${this.apiPrefix}${endpoint}`, window.location.origin);
        
        if (params) {
            Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));
        }

        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
            }
        };

        if (data && method !== 'GET') {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(url, options);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    }

    formatNumber(num) {
        if (!num || num === 0) return '0';
        
        if (num >= 100000000) {
            return `${(num / 100000000).toFixed(1)}억`;
        } else if (num >= 10000) {
            return `${(num / 10000).toFixed(1)}만`;
        } else {
            return num.toLocaleString();
        }
    }

    addLog(message, type = 'info') {
        if (!this.elements.logContainer) return;

        const timestamp = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${type}`;
        logEntry.innerHTML = `<span class="log-time">[${timestamp}]</span> <span class="log-message">${message}</span>`;

        this.elements.logContainer.appendChild(logEntry);
        this.elements.logContainer.scrollTop = this.elements.logContainer.scrollHeight;

        // 로그 항목 수 제한 (최대 100개)
        const logEntries = this.elements.logContainer.querySelectorAll('.log-entry');
        if (logEntries.length > 100) {
            logEntries[0].remove();
        }
    }

    showToast(message, type = 'info') {
        // 토스트 알림 표시
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('show');
        }, 100);

        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 300);
        }, 3000);
    }

    showProgressSection() {
        if (this.elements.progressSection) {
            this.elements.progressSection.style.display = 'block';
        }
    }

    hideProgressSection() {
        if (this.elements.progressSection) {
            this.elements.progressSection.style.display = 'none';
        }
    }

    showAnalyzeButton() {
        if (this.elements.analyzeBtn) {
            this.elements.analyzeBtn.style.display = 'inline-block';
            this.elements.analyzeBtn.disabled = false;
        }
    }

    hideAnalyzeButton() {
        if (this.elements.analyzeBtn) {
            this.elements.analyzeBtn.style.display = 'none';
        }
    }

    clearAnalysisResults() {
        if (this.elements.themeGrid) {
            this.elements.themeGrid.innerHTML = '';
        }
        
        // 요약 정보 제거
        const summary = document.querySelector('.analysis-summary');
        if (summary) {
            summary.remove();
        }
        
        this.themeResults = [];
    }

    showEmptyState(message) {
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

    adjustLayout() {
        // 반응형 레이아웃 조정
        const cards = document.querySelectorAll('.theme-card');
        cards.forEach(card => {
            if (window.innerWidth < 768) {
                card.classList.add('mobile');
            } else {
                card.classList.remove('mobile');
            }
        });
    }

    // ============= 🎯 사용자 액션 =============

    async addToWatchlist(themeName) {
        // 관심 테마 등록 (향후 구현)
        this.showToast(`${themeName}을 관심 목록에 추가했습니다.`, 'success');
        this.addLog(`⭐ ${themeName} 관심 등록`, 'info');
    }

    async refreshThemeDetail(themeName) {
        this.closeModal();
        await this.openThemeModal(themeName);
    }

    async refreshData() {
        this.addLog('🔄 데이터를 새로고침합니다...', 'info');
        await this.loadInitialData();
        await this.refreshSystemStatus();
        this.showToast('데이터 새로고침 완료', 'success');
    }

    async loadInitialData() {
        try {
            // 현재 날짜의 분석 결과가 있는지 확인
            const hasData = await this.checkDataExists(this.currentDate);

            if (hasData) {
                this.showAnalyzeButton();
                this.addLog(`💡 ${this.currentDate} 데이터가 있습니다.`, 'success');
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

    // ============= 정리 작업 =============

    cleanup() {
        // 인터벌 정리
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }

        if (this.systemMonitorInterval) {
            clearInterval(this.systemMonitorInterval);
            this.systemMonitorInterval = null;
        }

        // 모달 닫기
        this.closeModal();

        console.log('🧹 TopRateAnalysis 정리 완료');
    }

    // ============= 디버그 도구 =============

    debug() {
        return {
            currentDate: this.currentDate,
            isCollecting: this.isCollecting,
            isAnalyzing: this.isAnalyzing,
            themeResults: this.themeResults,
            systemStatus: this.systemStatus,
            progressInterval: !!this.progressInterval,
            systemMonitorInterval: !!this.systemMonitorInterval
        };
    }
}

// ============= 전역 함수 (HTML에서 직접 호출용) =============

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

// ============= 페이지 로드 완료시 자동 초기화 =============

document.addEventListener('DOMContentLoaded', function() {
    // 설정 확인
    if (!window.APP_CONFIG) {
        console.warn('⚠️ APP_CONFIG가 설정되지 않았습니다. 기본값을 사용합니다.');
        window.APP_CONFIG = {
            apiPrefix: '/top-rate/api',
            currentDate: new Date().toISOString().split('T')[0],
            availableDates: [],
            moduleName: '등락율상위분석',
            moduleVersion: '4.0.0'
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
            refreshData: () => window.topRateAnalysis.refreshData(),
            collect: () => window.topRateAnalysis.startRealDataCollection(),
            analyze: () => window.topRateAnalysis.startRealAnalysis()
        };
        console.log('🎯 개발자 도구 사용법:');
        console.log('  topRateDebug() - 현재 상태 확인');
        console.log('  topRateTest.collect() - 데이터 수집 테스트');
        console.log('  topRateTest.analyze() - 분석 실행 테스트');
    }

    console.log('🎉 등락율상위분석 실제 모듈 로드 완료');
});

// 모듈 익스포트 (ES6 환경에서 사용 가능)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TopRateAnalysis;
}