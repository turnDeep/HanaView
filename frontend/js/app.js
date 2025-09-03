// アプリケーションのメインJS
class InvestmentDashboard {
    constructor() {
        this.data = null;
        this.charts = {};
        this.currentTab = 'market';
        this.currentPeriod = 'day';
        this.init();
    }

    async init() {
        await this.loadData();
        this.setupEventListeners();
        this.renderCurrentTab();
        this.updateDateTime();
    }

    async loadData() {
        try {
            const response = await fetch('/api/data');
            this.data = await response.json();
            console.log('Data loaded:', this.data);
        } catch (error) {
            console.error('Error loading data:', error);
            this.showError('データの読み込みに失敗しました');
        }
    }

    setupEventListeners() {
        // タブ切り替え
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tab = btn.dataset.tab;
                this.switchTab(tab);
            });
        });

        // 期間切り替え
        document.querySelectorAll('.period-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const period = btn.dataset.period;
                this.switchPeriod(period);
            });
        });
    }

    switchTab(tab) {
        // タブボタンのアクティブ状態を更新
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tab}"]`).classList.add('active');

        // タブコンテンツの表示切り替え
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tab}-tab`).classList.add('active');

        this.currentTab = tab;
        this.renderCurrentTab();
    }

    switchPeriod(period) {
        document.querySelectorAll('.period-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        event.target.classList.add('active');

        this.currentPeriod = period;
        this.renderHeatmaps();
    }

    renderCurrentTab() {
        switch(this.currentTab) {
            case 'market':
                this.renderMarketTab();
                break;
            case 'nasdaq':
                this.renderNasdaqHeatmap();
                break;
            case 'sp500':
                this.renderSP500Heatmap();
                break;
            case 'news':
                this.renderNews();
                break;
            case 'indicators':
                this.renderIndicators();
                break;
            case 'column':
                this.renderColumn();
                break;
        }
    }

    renderMarketTab() {
        if (!this.data || !this.data.market) return;

        // Fear & Greed Index
        this.renderFearGreedMeter();

        // VIXチャート
        this.renderVIXChart();

        // 10年債利回りチャート
        this.renderTreasuryChart();

        // AI解説
        this.renderAICommentary();
    }

    renderFearGreedMeter() {
        const fg = this.data.market.fear_and_greed;
        if (!fg) return;

        const canvas = document.getElementById('fearGreedCanvas');
        const ctx = canvas.getContext('2d');
        const centerX = canvas.width / 2;
        const centerY = canvas.height - 20;
        const radius = 100;

        // メーターの背景を描画
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // 色のグラデーション
        const gradient = ctx.createLinearGradient(0, 0, canvas.width, 0);
        gradient.addColorStop(0, '#c62828');
        gradient.addColorStop(0.25, '#ef5350');
        gradient.addColorStop(0.5, '#9e9e9e');
        gradient.addColorStop(0.75, '#66bb6a');
        gradient.addColorStop(1, '#2e7d32');

        // 半円の背景
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, Math.PI, 0);
        ctx.lineWidth = 20;
        ctx.strokeStyle = gradient;
        ctx.stroke();

        // 現在値の針
        const angle = Math.PI + (fg.now / 100) * Math.PI;
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.lineTo(
            centerX + Math.cos(angle) * (radius - 25),
            centerY + Math.sin(angle) * (radius - 25)
        );
        ctx.lineWidth = 3;
        ctx.strokeStyle = '#333';
        ctx.stroke();

        // 値を表示
        document.getElementById('fearGreedValue').innerHTML = `
            <div style="font-size: 3rem; color: ${this.getFGColor(fg.now)}">${fg.now}</div>
            <div style="font-size: 1rem; color: #666">${fg.category}</div>
        `;

        // 履歴を表示
        document.getElementById('fearGreedHistory').innerHTML = `
            <div class="history-item">
                <span>前日終値</span>
                <span style="color: ${this.getFGColor(fg.previous_close)}">${fg.previous_close || 'N/A'}</span>
            </div>
            <div class="history-item">
                <span>1週間前</span>
                <span style="color: ${this.getFGColor(fg.prev_week)}">${fg.prev_week || 'N/A'}</span>
            </div>
            <div class="history-item">
                <span>1ヶ月前</span>
                <span style="color: ${this.getFGColor(fg.prev_month)}">${fg.prev_month || 'N/A'}</span>
            </div>
            <div class="history-item">
                <span>1年前</span>
                <span style="color: ${this.getFGColor(fg.prev_year)}">${fg.prev_year || 'N/A'}</span>
            </div>
        `;
    }

    getFGColor(value) {
        if (value <= 25) return '#c62828';
        if (value <= 45) return '#ef5350';
        if (value <= 55) return '#9e9e9e';
        if (value <= 75) return '#66bb6a';
        return '#2e7d32';
    }

    renderVIXChart() {
        const container = document.getElementById('vixChart');
        if (!container) return;

        // 既存のチャートをクリア
        container.innerHTML = '';

        const chart = LightweightCharts.createChart(container, {
            width: container.offsetWidth,
            height: 250,
            layout: {
                backgroundColor: '#ffffff',
                textColor: '#333333',
            },
            grid: {
                vertLines: { color: '#e0e0e0' },
                horzLines: { color: '#e0e0e0' },
            },
        });

        const candleSeries = chart.addCandlestickSeries({
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
        });

        // VIXデータをチャート用に変換
        if (this.data.market.vix && this.data.market.vix.history) {
            const chartData = this.data.market.vix.history.map(item => ({
                time: new Date(item.time).getTime() / 1000,
                open: item.open,
                high: item.high,
                low: item.low,
                close: item.close,
            }));
            candleSeries.setData(chartData);
        }

        chart.timeScale().fitContent();
        this.charts.vix = chart;

        // 現在値を表示
        if (this.data.market.vix) {
            const currentValue = document.createElement('div');
            currentValue.className = 'current-value';
            currentValue.innerHTML = `現在値: <strong>${this.data.market.vix.current}</strong>`;
            container.appendChild(currentValue);
        }
    }

    renderTreasuryChart() {
        const container = document.getElementById('treasuryChart');
        if (!container) return;

        // 既存のチャートをクリア
        container.innerHTML = '';

        const chart = LightweightCharts.createChart(container, {
            width: container.offsetWidth,
            height: 250,
            layout: {
                backgroundColor: '#ffffff',
                textColor: '#333333',
            },
            grid: {
                vertLines: { color: '#e0e0e0' },
                horzLines: { color: '#e0e0e0' },
            },
        });

        const candleSeries = chart.addCandlestickSeries({
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
        });

        // 10年債利回りデータをチャート用に変換
        if (this.data.market.us_10y_yield && this.data.market.us_10y_yield.history) {
            const chartData = this.data.market.us_10y_yield.history.map(item => ({
                time: new Date(item.time).getTime() / 1000,
                open: item.open,
                high: item.high,
                low: item.low,
                close: item.close,
            }));
            candleSeries.setData(chartData);
        }

        chart.timeScale().fitContent();
        this.charts.treasury = chart;

        // 現在値を表示
        if (this.data.market.us_10y_yield) {
            const currentValue = document.createElement('div');
            currentValue.className = 'current-value';
            currentValue.innerHTML = `現在値: <strong>${this.data.market.us_10y_yield.current}%</strong>`;
            container.appendChild(currentValue);
        }
    }

    renderAICommentary() {
        const container = document.getElementById('aiCommentary');
        if (!container) return;

        if (this.data.market.ai_commentary) {
            container.innerHTML = `<p>${this.data.market.ai_commentary}</p>`;
        } else {
            container.innerHTML = '<p>解説を読み込み中...</p>';
        }
    }

    renderNasdaqHeatmap() {
        this.renderHeatmap('nasdaq', 'nasdaqHeatmap');
    }

    renderSP500Heatmap() {
        this.renderHeatmap('sp500', 'sp500Heatmap');
    }

    renderHeatmap(index, containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const heatmapData = index === 'nasdaq' ? 
            this.data.nasdaq_heatmap : this.data.sp500_heatmap;

        if (!heatmapData) return;

        const periodData = heatmapData[this.currentPeriod];
        if (!periodData) return;

        // ヒートマップをクリア
        container.innerHTML = '';

        // セクターごとにグループ化（S&P 500の場合）
        let sectors = {};
        if (index === 'sp500') {
            periodData.forEach(stock => {
                if (!sectors[stock.sector]) {
                    sectors[stock.sector] = [];
                }
                sectors[stock.sector].push(stock);
            });

            // セクターごとに表示
            Object.keys(sectors).forEach(sector => {
                const sectorDiv = document.createElement('div');
                sectorDiv.className = 'sector-group';
                sectorDiv.innerHTML = `<h4 style="margin: 12px 0; font-size: 0.9rem; color: #666;">${sector}</h4>`;
                
                const sectorHeatmap = document.createElement('div');
                sectorHeatmap.className = 'heatmap';
                
                sectors[sector].forEach(stock => {
                    sectorHeatmap.appendChild(this.createHeatmapCell(stock));
                });
                
                sectorDiv.appendChild(sectorHeatmap);
                container.appendChild(sectorDiv);
            });
        } else {
            // NASDAQ（セクター分けなし）
            periodData.forEach(stock => {
                container.appendChild(this.createHeatmapCell(stock));
            });
        }
    }

    createHeatmapCell(stock) {
        const cell = document.createElement('div');
        cell.className = `heatmap-cell ${this.getPerformanceClass(stock.performance)}`;
        
        // 時価総額に応じたサイズ調整
        if (stock.market_cap) {
            const scale = Math.log10(stock.market_cap / 1e9) / 3; // 10億ドル単位でログスケール
            cell.style.transform = `scale(${Math.max(0.8, Math.min(1.2, scale))})`;
        }
        
        cell.innerHTML = `
            <div class="heatmap-ticker">${stock.ticker}</div>
            <div class="heatmap-performance">${stock.performance > 0 ? '+' : ''}${stock.performance}%</div>
        `;
        
        // ツールチップ
        cell.title = `${stock.name || stock.ticker}: ${stock.performance > 0 ? '+' : ''}${stock.performance}%`;
        
        return cell;
    }

    getPerformanceClass(performance) {
        if (performance >= 3) return 'performance-positive-high';
        if (performance >= 1) return 'performance-positive-mid';
        if (performance > 0) return 'performance-positive-low';
        if (performance === 0) return 'performance-neutral';
        if (performance > -1) return 'performance-negative-low';
        if (performance > -3) return 'performance-negative-mid';
        return 'performance-negative-high';
    }

    renderNews() {
        const container = document.getElementById('newsList');
        if (!container) return;

        container.innerHTML = '';

        if (!this.data.news || this.data.news.length === 0) {
            container.innerHTML = '<p>ニュースがありません</p>';
            return;
        }

        this.data.news.forEach(news => {
            const newsItem = document.createElement('div');
            newsItem.className = 'news-item';
            newsItem.innerHTML = `
                <div class="news-title">${news.title}</div>
                <div class="news-meta">
                    <span>${news.publisher}</span> • 
                    <span>${new Date(news.published).toLocaleString('ja-JP')}</span>
                </div>
            `;
            container.appendChild(newsItem);
        });
    }

    renderIndicators() {
        const economicContainer = document.getElementById('economicIndicators');
        const earningsContainer = document.getElementById('earningsUS');

        if (economicContainer && this.data.indicators && this.data.indicators.economic) {
            economicContainer.innerHTML = '';
            
            if (this.data.indicators.economic.length === 0) {
                economicContainer.innerHTML = '<p>本日の経済指標はありません</p>';
            } else {
                this.data.indicators.economic.forEach(indicator => {
                    const item = document.createElement('div');
                    item.className = 'indicator-item';
                    item.innerHTML = `
                        <span class="indicator-time">${indicator.time}</span>
                        <span class="indicator-importance">${'★'.repeat(indicator.importance)}</span>
                        <span class="indicator-name">${indicator.name}</span>
                    `;
                    economicContainer.appendChild(item);
                });
            }
        }

        if (earningsContainer) {
            earningsContainer.innerHTML = '<p>決算情報を読み込み中...</p>';
        }
    }

    renderColumn() {
        const container = document.getElementById('columnContent');
        if (!container) return;

        if (!this.data.column || Object.keys(this.data.column).length === 0) {
            container.innerHTML = '<p>コラムがありません</p>';
            return;
        }

        if (this.data.column.weekly_report) {
            container.innerHTML = `
                <div class="column-article">
                    <h3>${this.data.column.weekly_report.title}</h3>
                    <div class="column-date">${this.data.column.weekly_report.date}</div>
                    <div class="column-content">${this.data.column.weekly_report.content}</div>
                </div>
            `;
        }
    }

    updateDateTime() {
        const element = document.getElementById('updateTime');
        if (element && this.data) {
            const date = new Date(this.data.last_updated);
            element.textContent = date.toLocaleString('ja-JP');
        }
    }

    showError(message) {
        console.error(message);
        // エラー表示の実装
    }
}

// アプリケーションの初期化
document.addEventListener('DOMContentLoaded', () => {
    new InvestmentDashboard();
});