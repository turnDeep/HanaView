import json
import logging
from datetime import datetime, timedelta
import yfinance as yf
from curl_cffi import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from openai import OpenAI
import pytz
from config import *

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# OpenAI クライアント初期化
client = OpenAI(api_key=OPENAI_API_KEY)

class MarketDataFetcher:
    def __init__(self):
        self.data = {
            'date': datetime.now(TZ_JST).strftime('%Y-%m-%d'),
            'last_updated': datetime.now(TZ_JST).isoformat(),
            'market': {},
            'nasdaq_heatmap': {},
            'sp500_heatmap': {},
            'news': [],
            'indicators': {},
            'column': {}
        }
    
    def fetch_fear_greed_index(self):
        """Fear & Greed Indexを取得"""
        try:
            # CNN Fear & Greed APIから取得
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            url = f"{CNN_FEAR_GREED_URL}{start_date}"
            
            response = requests.get(url, impersonate="chrome110", timeout=30)
            data = response.json()
            
            # 最新データと履歴データを整理
            fear_greed_data = data.get('fear_and_greed_historical', {}).get('data', [])
            
            if fear_greed_data:
                # 現在の値
                current = fear_greed_data[-1]
                current_value = current['y']
                
                # 過去の値を計算
                now = datetime.now()
                prev_close = self._get_historical_value(fear_greed_data, 1)
                week_ago = self._get_historical_value(fear_greed_data, 7)
                month_ago = self._get_historical_value(fear_greed_data, 30)
                year_ago = self._get_historical_value(fear_greed_data, 365)
                
                self.data['market']['fear_and_greed'] = {
                    'now': round(current_value),
                    'previous_close': round(prev_close) if prev_close else None,
                    'prev_week': round(week_ago) if week_ago else None,
                    'prev_month': round(month_ago) if month_ago else None,
                    'prev_year': round(year_ago) if year_ago else None,
                    'category': self._get_fear_greed_category(current_value)
                }
                logger.info(f"Fear & Greed Index fetched: {current_value}")
            
        except Exception as e:
            logger.error(f"Error fetching Fear & Greed Index: {e}")
            self.data['market']['fear_and_greed'] = {
                'now': None,
                'error': str(e)
            }
    
    def _get_historical_value(self, data, days_ago):
        """指定日前のデータを取得"""
        target_timestamp = (datetime.now() - timedelta(days=days_ago)).timestamp() * 1000
        
        # 最も近いタイムスタンプのデータを探す
        closest_data = None
        min_diff = float('inf')
        
        for item in data:
            diff = abs(item['x'] - target_timestamp)
            if diff < min_diff:
                min_diff = diff
                closest_data = item
        
        return closest_data['y'] if closest_data else None
    
    def _get_fear_greed_category(self, value):
        """Fear & Greedのカテゴリを判定"""
        if value <= 25:
            return "Extreme Fear"
        elif value <= 45:
            return "Fear"
        elif value <= 55:
            return "Neutral"
        elif value <= 75:
            return "Greed"
        else:
            return "Extreme Greed"
    
    def fetch_vix_data(self):
        """VIXデータを取得（4時間足）"""
        try:
            ticker = yf.Ticker("^VIX")
            # 過去5日分の4時間足データを取得
            hist = ticker.history(period="5d", interval="1h")
            
            # 4時間足に変換
            four_hour_data = []
            for i in range(0, len(hist), 4):
                if i + 3 < len(hist):
                    four_hour_data.append({
                        'time': hist.index[i].isoformat(),
                        'open': float(hist['Open'].iloc[i]),
                        'high': float(hist['High'].iloc[i:i+4].max()),
                        'low': float(hist['Low'].iloc[i:i+4].min()),
                        'close': float(hist['Close'].iloc[i+3])
                    })
            
            self.data['market']['vix'] = {
                'current': float(hist['Close'].iloc[-1]),
                'history': four_hour_data
            }
            logger.info(f"VIX data fetched: {self.data['market']['vix']['current']}")
            
        except Exception as e:
            logger.error(f"Error fetching VIX data: {e}")
            self.data['market']['vix'] = {'error': str(e)}
    
    def fetch_treasury_yield(self):
        """米国10年債利回りデータを取得（4時間足）"""
        try:
            ticker = yf.Ticker("^TNX")
            hist = ticker.history(period="5d", interval="1h")
            
            # 4時間足に変換
            four_hour_data = []
            for i in range(0, len(hist), 4):
                if i + 3 < len(hist):
                    four_hour_data.append({
                        'time': hist.index[i].isoformat(),
                        'open': float(hist['Open'].iloc[i]),
                        'high': float(hist['High'].iloc[i:i+4].max()),
                        'low': float(hist['Low'].iloc[i:i+4].min()),
                        'close': float(hist['Close'].iloc[i+3])
                    })
            
            self.data['market']['us_10y_yield'] = {
                'current': float(hist['Close'].iloc[-1]),
                'history': four_hour_data
            }
            logger.info(f"10Y Treasury yield fetched: {self.data['market']['us_10y_yield']['current']}")
            
        except Exception as e:
            logger.error(f"Error fetching treasury yield: {e}")
            self.data['market']['us_10y_yield'] = {'error': str(e)}
    
    def fetch_nasdaq_heatmap_data(self):
        """NASDAQ 100のヒートマップデータを取得"""
        try:
            # NASDAQ 100の構成銘柄を取得
            nasdaq100 = yf.Ticker("^NDX")
            
            # NASDAQ 100の主要構成銘柄（上位30銘柄）
            nasdaq_symbols = [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO',
                'ASML', 'COST', 'NFLX', 'AMD', 'PEP', 'ADBE', 'CSCO', 'INTC',
                'CMCSA', 'TMUS', 'TXN', 'QCOM', 'AMGN', 'HON', 'INTU', 'AMAT',
                'ISRG', 'VRTX', 'BKNG', 'SBUX', 'ADP', 'GILD', 'MU', 'ADI',
                'LRCX', 'REGN', 'MDLZ', 'KLAC', 'SNPS', 'CDNS', 'PANW', 'MRVL'
            ]
            
            heatmap_data = {
                'type': 'contribution',
                'day': [],
                'week': [],
                'month': []
            }
            
            # 各銘柄のデータを取得
            for symbol in nasdaq_symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    hist = ticker.history(period="1mo")
                    
                    if not hist.empty:
                        # パフォーマンス計算
                        day_perf = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2] * 100) if len(hist) > 1 else 0
                        week_perf = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-5]) / hist['Close'].iloc[-5] * 100) if len(hist) > 5 else 0
                        month_perf = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0] * 100)
                        
                        # 時価総額を取得
                        market_cap = info.get('marketCap', 0)
                        
                        # ヒートマップデータに追加
                        heatmap_data['day'].append({
                            'ticker': symbol,
                            'name': info.get('shortName', symbol),
                            'sector': info.get('sector', 'Technology'),
                            'performance': round(day_perf, 2),
                            'market_cap': market_cap
                        })
                        
                        heatmap_data['week'].append({
                            'ticker': symbol,
                            'performance': round(week_perf, 2)
                        })
                        
                        heatmap_data['month'].append({
                            'ticker': symbol,
                            'performance': round(month_perf, 2)
                        })
                        
                except Exception as e:
                    logger.warning(f"Error fetching data for {symbol}: {e}")
                    continue
            
            self.data['nasdaq_heatmap'] = heatmap_data
            logger.info(f"NASDAQ heatmap data fetched for {len(nasdaq_symbols)} symbols")
            
        except Exception as e:
            logger.error(f"Error fetching NASDAQ heatmap data: {e}")
            self.data['nasdaq_heatmap'] = {'error': str(e)}
    
    def fetch_sp500_heatmap_data(self):
        """S&P 500のヒートマップデータを取得"""
        try:
            # S&P 500の主要銘柄（各セクターの代表銘柄）
            sp500_symbols = {
                'Technology': ['AAPL', 'MSFT', 'NVDA', 'AVGO', 'ORCL', 'CRM', 'ADBE', 'CSCO'],
                'Healthcare': ['LLY', 'UNH', 'JNJ', 'ABBV', 'MRK', 'PFE', 'TMO', 'ABT'],
                'Financials': ['BRK-B', 'JPM', 'V', 'MA', 'BAC', 'WFC', 'GS', 'MS'],
                'Consumer Discretionary': ['AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'SBUX', 'LOW', 'TJX'],
                'Communication Services': ['GOOGL', 'META', 'NFLX', 'DIS', 'CMCSA', 'VZ', 'T', 'TMUS'],
                'Industrials': ['BA', 'UNH', 'CAT', 'HON', 'UPS', 'RTX', 'GE', 'LMT'],
                'Consumer Staples': ['PG', 'WMT', 'KO', 'PEP', 'COST', 'PM', 'CVS', 'MDLZ'],
                'Energy': ['XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PXD', 'VLO'],
                'Utilities': ['NEE', 'SO', 'DUK', 'D', 'AEP', 'SRE', 'EXC', 'XEL'],
                'Real Estate': ['PLD', 'AMT', 'CCI', 'EQIX', 'PSA', 'SPG', 'WELL', 'DLR'],
                'Materials': ['LIN', 'APD', 'SHW', 'FCX', 'ECL', 'NUE', 'DD', 'NEM']
            }
            
            heatmap_data = {
                'type': 'performance',
                'day': [],
                'week': [],
                'month': []
            }
            
            # 各セクターの銘柄データを取得
            for sector, symbols in sp500_symbols.items():
                for symbol in symbols:
                    try:
                        ticker = yf.Ticker(symbol)
                        info = ticker.info
                        hist = ticker.history(period="1mo")
                        
                        if not hist.empty:
                            # パフォーマンス計算
                            day_perf = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2] * 100) if len(hist) > 1 else 0
                            week_perf = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-5]) / hist['Close'].iloc[-5] * 100) if len(hist) > 5 else 0
                            month_perf = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0] * 100)
                            
                            # 時価総額を取得
                            market_cap = info.get('marketCap', 0)
                            
                            # ヒートマップデータに追加
                            heatmap_data['day'].append({
                                'ticker': symbol,
                                'name': info.get('shortName', symbol),
                                'sector': sector,
                                'performance': round(day_perf, 2),
                                'market_cap': market_cap
                            })
                            
                            heatmap_data['week'].append({
                                'ticker': symbol,
                                'sector': sector,
                                'performance': round(week_perf, 2)
                            })
                            
                            heatmap_data['month'].append({
                                'ticker': symbol,
                                'sector': sector,
                                'performance': round(month_perf, 2)
                            })
                            
                    except Exception as e:
                        logger.warning(f"Error fetching data for {symbol}: {e}")
                        continue
            
            self.data['sp500_heatmap'] = heatmap_data
            logger.info(f"S&P 500 heatmap data fetched")
            
        except Exception as e:
            logger.error(f"Error fetching S&P 500 heatmap data: {e}")
            self.data['sp500_heatmap'] = {'error': str(e)}
    
    def fetch_economic_indicators(self):
        """経済指標カレンダーをみんかぶから取得"""
        try:
            response = requests.get(MINKABU_INDICATORS_URL, impersonate="chrome110", timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            indicators = []
            
            # 経済指標テーブルを探す
            indicator_tables = soup.find_all('div', class_='indicator-table')
            
            for table in indicator_tables:
                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 3:
                        time = cols[0].text.strip()
                        importance = len(cols[1].find_all('span', class_='star'))
                        name = cols[2].text.strip()
                        
                        # 重要度2以上のみ表示
                        if importance >= 2:
                            indicators.append({
                                'time': time,
                                'name': name,
                                'importance': importance
                            })
            
            self.data['indicators']['economic'] = indicators
            logger.info(f"Economic indicators fetched: {len(indicators)} items")
            
        except Exception as e:
            logger.error(f"Error fetching economic indicators: {e}")
            self.data['indicators']['economic'] = []
    
    def fetch_news(self):
        """最新の米国株関連ニュースを取得"""
        try:
            # Yahoo Financeからニュースを取得（例）
            tickers = ['^GSPC', '^IXIC', '^DJI']  # S&P 500, NASDAQ, DOW
            news_items = []
            
            for ticker_symbol in tickers:
                ticker = yf.Ticker(ticker_symbol)
                news = ticker.news
                
                for item in news[:3]:  # 各インデックスから上位3件
                    news_items.append({
                        'title': item.get('title', ''),
                        'publisher': item.get('publisher', ''),
                        'link': item.get('link', ''),
                        'published': datetime.fromtimestamp(item.get('providerPublishTime', 0)).isoformat()
                    })
            
            # 重複を除去
            seen = set()
            unique_news = []
            for item in news_items:
                if item['title'] not in seen:
                    seen.add(item['title'])
                    unique_news.append(item)
            
            self.data['news'] = unique_news[:5]  # 上位5件
            logger.info(f"News fetched: {len(self.data['news'])} items")
            
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            self.data['news'] = []
    
    def generate_ai_commentary(self):
        """AIによる市況解説を生成"""
        try:
            # プロンプト構築
            market_data = self.data['market']
            
            prompt = f"""
            以下の市場データを基に、日本の個人投資家向けに本日の米国市場の状況を簡潔に解説してください。

            Fear & Greed Index: {market_data.get('fear_and_greed', {}).get('now', 'N/A')} ({market_data.get('fear_and_greed', {}).get('category', '')})
            - 前日比: {market_data.get('fear_and_greed', {}).get('previous_close', 'N/A')}
            - 1週間前: {market_data.get('fear_and_greed', {}).get('prev_week', 'N/A')}
            - 1ヶ月前: {market_data.get('fear_and_greed', {}).get('prev_month', 'N/A')}

            VIX: {market_data.get('vix', {}).get('current', 'N/A')}
            米国10年債利回り: {market_data.get('us_10y_yield', {}).get('current', 'N/A')}%

            以下の観点で150文字程度で解説してください：
            1. 現在の市場センチメント
            2. 注意すべきポイント
            3. 今後の見通し
            """
            
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "あなたは金融市場の専門家です。初心者にもわかりやすく、かつ的確な市場解説を提供してください。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            self.data['market']['ai_commentary'] = response.choices[0].message.content
            logger.info("AI commentary generated")
            
        except Exception as e:
            logger.error(f"Error generating AI commentary: {e}")
            self.data['market']['ai_commentary'] = "市況解説の生成に失敗しました。"
    
    def generate_ai_column(self):
        """AIによる週次コラムを生成"""
        try:
            # 週次レポート（月曜日更新）
            today = datetime.now(TZ_JST)
            is_monday = today.weekday() == 0
            
            if is_monday:
                prompt = """
                今週の米国株市場の注目ポイントについて、個人投資家向けに週次レポートを作成してください。
                以下の項目を含めてください：
                1. 先週の振り返り（主要指数の動き）
                2. 今週の注目イベント（FOMC、雇用統計など）
                3. 注目セクター・個別銘柄
                4. 投資戦略のヒント
                
                300文字程度でまとめてください。
                """
                
                response = client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": "あなたは経験豊富な投資アドバイザーです。"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500,
                    temperature=0.8
                )
                
                self.data['column']['weekly_report'] = {
                    'title': '今週の注目ポイント',
                    'content': response.choices[0].message.content,
                    'date': today.strftime('%Y-%m-%d')
                }
            
            logger.info("AI column generated")
            
        except Exception as e:
            logger.error(f"Error generating AI column: {e}")
    
    def save_data(self):
        """データをJSON形式で保存"""
        try:
            filename = f"{DATA_DIR}/data_{self.data['date']}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            logger.info(f"Data saved to {filename}")
            
            # 1週間前のデータを削除
            week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            old_file = f"{DATA_DIR}/data_{week_ago}.json"
            if os.path.exists(old_file):
                os.remove(old_file)
                logger.info(f"Old data file removed: {old_file}")
                
        except Exception as e:
            logger.error(f"Error saving data: {e}")
    
    def fetch_all(self):
        """全データを取得"""
        logger.info("Starting data fetch...")
        
        self.fetch_fear_greed_index()
        self.fetch_vix_data()
        self.fetch_treasury_yield()
        self.fetch_nasdaq_heatmap_data()
        self.fetch_sp500_heatmap_data()
        self.fetch_economic_indicators()
        self.fetch_news()
        self.generate_ai_commentary()
        self.generate_ai_column()
        self.save_data()
        
        logger.info("Data fetch completed")

if __name__ == "__main__":
    fetcher = MarketDataFetcher()
    fetcher.fetch_all()