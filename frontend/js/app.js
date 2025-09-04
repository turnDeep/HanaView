// アプリケーションのメインJS
class InvestmentDashboard {
    constructor() {
        this.data = null;
        this.charts = {};
        this.currentTab = 'market';
        this.currentNasdaqPeriod = 'day';
        this.currentSP500Period = 'day';
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

        // Fear & Greed Index スクリーンショット
        this.renderFearGreedScreenshot();

        // VIXチャート
        this.renderVIXChart();

        // 10年債利回りチャート
        this.renderTreasuryChart();

        // AI解説
        this.renderAICommentary();
    }

    renderFearGreedScreenshot() {
        const container = document.querySelector('.fear-greed-meter');
        if (!container) return;

        // Canvas要素を非表示にし、スクリーンショットを表示
        const canvas = document.getElementById('fearGreedCanvas');
        if (canvas) canvas.style.display = 'none';
        
        const valueDiv = document.getElementById('fearGreedValue');
        const historyDiv = document.getElementById('fearGreedHistory');
        
        if (this.data.screenshots && this.data.screenshots.fear_greed) {
            // スクリーンショットを表示
            if (valueDiv) {
                valueDiv.innerHTML = `
                    <img src="data:image/png;base64,${this.data.screenshots.fear_greed}" 
                         alt="Fear & Greed Index" 
                         style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                `;
            }
            // 履歴の表示は削除（スクリーンショットに含まれているため）
            if (historyDiv) {
                historyDiv.innerHTML = '';
            }
        } else {
            if (valueDiv) {
                valueDiv.innerHTML = '<p>Fear & Greed Indexを読み込み中...</p>';
            }
        }
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
            currentValue.style.marginTop = '10px';
            currentValue.style.fontSize = '1.1rem';
            currentValue.style.fontWeight = 'bold';
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

        // 10年債先物データをチャート用に変換
        if (this.data.market.t_note_future && this.data.market.t_note_future.history) {
            const chartData = this.data.market.t_note_future.history.map(item => ({
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
        if (this.data.market.t_note_future) {
            const currentValue = document.createElement('div');
            currentValue.className = 'current-value';
            currentValue.innerHTML = `現在値: <strong>${this.data.market.t_note_future.current}</strong>`;
            currentValue.style.marginTop = '10px';
            currentValue.style.fontSize = '1.1rem';
            currentValue.style.fontWeight = 'bold';
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
        const container = document.getElementById('nasdaqHeatmap');
        if (!container || !container.parentElement) return;

        // 期間セレクターを追加（まだない場合）
        let periodSelector = container.parentElement.querySelector('.period-selector');
        if (!periodSelector) {
            periodSelector = document.createElement('div');
            periodSelector.className = 'period-selector';
            periodSelector.innerHTML = `
                <button class="period-btn ${this.currentNasdaqPeriod === 'day' ? 'active' : ''}" data-period="day" data-index="nasdaq">1日</button>
                <button class="period-btn ${this.currentNasdaqPeriod === 'week' ? 'active' : ''}" data-period="week" data-index="nasdaq">1週間</button>
                <button class="period-btn ${this.currentNasdaqPeriod === 'month' ? 'active' : ''}" data-period="month" data-index="nasdaq">1ヶ月</button>
            `;
            container.parentElement.insertBefore(periodSelector, container);

            // イベントリスナーを追加
            periodSelector.querySelectorAll('.period-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const period = btn.dataset.period;
                    this.currentNasdaqPeriod = period;
                    
                    // ボタンのアクティブ状態を更新
                    periodSelector.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    
                    // ヒートマップを再描画
                    this.renderNasdaqHeatmap();
                });
            });
        }

        // スクリーンショットを表示
        if (this.data.screenshots && this.data.screenshots.nasdaq100 && this.data.screenshots.nasdaq100[this.currentNasdaqPeriod]) {
            container.innerHTML = `
                <img src="data:image/png;base64,${this.data.screenshots.nasdaq100[this.currentNasdaqPeriod]}" 
                     alt="NASDAQ 100 Heatmap - ${this.currentNasdaqPeriod}" 
                     style="max-width: 100%; height: auto; border-radius: 8px;">
            `;
        } else {
            container.innerHTML = '<p>ヒートマップを読み込み中...</p>';
        }
    }

    renderSP500Heatmap() {
        const container = document.getElementById('sp500Heatmap');
        if (!container || !container.parentElement) return;

        // 期間セレクターを追加（まだない場合）
        let periodSelector = container.parentElement.querySelector('.period-selector');
        if (!periodSelector) {
            periodSelector = document.createElement('div');
            periodSelector.className = 'period-selector';
            periodSelector.innerHTML = `
                <button class="period-btn ${this.currentSP500Period === 'day' ? 'active' : ''}" data-period="day" data-index="sp500">1日</button>
                <button class="period-btn ${this.currentSP500Period === 'week' ? 'active' : ''}" data-period="week" data-index="sp500">1週間</button>
                <button class="period-btn ${this.currentSP500Period === 'month' ? 'active' : ''}" data-period="month" data-index="sp500">1ヶ月</button>
            `;
            container.parentElement.insertBefore(periodSelector, container);

            // イベントリスナーを追加
            periodSelector.querySelectorAll('.period-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const period = btn.dataset.period;
                    this.currentSP500Period = period;
                    
                    // ボタンのアクティブ状態を更新
                    periodSelector.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    
                    // ヒートマップを再描画
                    this.renderSP500Heatmap();
                });
            });
        }

        // スクリーンショットを表示
        if (this.data.screenshots && this.data.screenshots.sp500 && this.data.screenshots.sp500[this.currentSP500Period]) {
            container.innerHTML = `
                <img src="data:image/png;base64,${this.data.screenshots.sp500[this.currentSP500Period]}" 
                     alt="S&P 500 Heatmap - ${this.currentSP500Period}" 
                     style="max-width: 100%; height: auto; border-radius: 8px;">
            `;
        } else {
            container.innerHTML = '<p>ヒートマップを読み込み中...</p>';
        }
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
