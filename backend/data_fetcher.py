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
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
import base64
from PIL import Image
import io
import os
import sys
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
            'column': {},
            'screenshots': {}  # スクリーンショットデータを格納
        }
        self.screenshots_dir = os.path.join(DATA_DIR, 'screenshots')
        os.makedirs(self.screenshots_dir, exist_ok=True)
        
        # curl_cffiセッションを作成（HWB-botと同じ方法）
        self.session = requests.Session(impersonate="safari15_5")
    
    async def capture_screenshot(self, url, selector=None, wait_time=3000):
        """指定URLのスクリーンショットをキャプチャ"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
                )
                page = await browser.new_page(
                    viewport={'width': 1920, 'height': 1080}
                )
                
                # ステルスモードを適用
                await stealth_async(page)

                # ページを読み込み
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(wait_time)  # 追加の待機時間
                
                # 特定の要素を指定してスクリーンショット
                if selector:
                    try:
                        element = page.locator(selector).first
                        await element.wait_for(state='visible', timeout=10000)
                        screenshot = await element.screenshot()
                    except Exception as e:
                        logger.warning(f"Selector {selector} not found: {e}, taking full page screenshot")
                        screenshot = await page.screenshot(full_page=False)
                else:
                    screenshot = await page.screenshot(full_page=False)
                
                await browser.close()
                
                # Base64エンコード
                screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')
                return screenshot_base64
                
        except Exception as e:
            logger.error(f"Error capturing screenshot from {url}: {e}")
            return None
    
    async def fetch_fear_greed_screenshot(self):
        """Fear & Greed Indexのスクリーンショットを取得"""
        try:
            logger.info("Capturing Fear & Greed Index screenshot...")
            screenshot = await self.capture_screenshot(
                'https://edition.cnn.com/markets/fear-and-greed',
                "div[data-uri*='fearandgreed']",  # Fear & Greedゲージのセレクター
                wait_time=5000
            )
            
            if screenshot:
                self.data['screenshots']['fear_greed'] = screenshot
                logger.info("Fear & Greed Index screenshot captured")
            
        except Exception as e:
            logger.error(f"Error fetching Fear & Greed screenshot: {e}")
    
    async def fetch_finviz_heatmaps(self):
        """FinvizからS&P500とNASDAQ100のヒートマップスクリーンショットを取得"""
        heatmap_configs = {
            'sp500': {
                'day': 'https://finviz.com/map.ashx?t=sec',
                'week': 'https://finviz.com/map.ashx?t=sec&st=w1',
                'month': 'https://finviz.com/map.ashx?t=sec&st=w4'
            },
            'nasdaq100': {
                'day': 'https://finviz.com/map.ashx?t=sec_ndx',
                'week': 'https://finviz.com/map.ashx?t=sec_ndx&st=w1',
                'month': 'https://finviz.com/map.ashx?t=sec_ndx&st=w4'
            }
        }
        
        for index_name, periods in heatmap_configs.items():
            self.data['screenshots'][index_name] = {}
            
            for period, url in periods.items():
                try:
                    logger.info(f"Capturing {index_name} {period} heatmap...")
                    screenshot = await self.capture_screenshot(
                        url,
                        '#content',  # Finvizのメインコンテンツエリア
                        wait_time=5000
                    )
                    
                    if screenshot:
                        self.data['screenshots'][index_name][period] = screenshot
                        logger.info(f"{index_name} {period} heatmap captured")
                        
                except Exception as e:
                    logger.error(f"Error capturing {index_name} {period} heatmap: {e}")
    
    def fetch_vix_data(self):
        """VIXデータを取得（curl_cffiセッション使用）"""
        try:
            ticker = yf.Ticker("VX=F", session=self.session)
            
            # 過去5日分の1時間足データを取得
            hist = ticker.history(period="5d", interval="1h")

            if hist.empty: 
                logger.error("VIX data is empty.")
                self.data['market']['vix'] = {'error': 'No data received from yfinance'}
                return
            
            # 4時間足にリサンプリング
            hist.index = pd.to_datetime(hist.index)
            agg_rules = {
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last'
            }
            four_hour_hist = hist.resample('4H', label='left', closed='left').agg(agg_rules).dropna()

            four_hour_data = [
                {
                    'time': index.isoformat(),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close'])
                }
                for index, row in four_hour_hist.iterrows()
            ]
            
            self.data['market']['vix'] = {
                'current': float(hist['Close'].iloc[-1]),
                'history': four_hour_data
            }
            logger.info(f"VIX data fetched: {self.data['market']['vix']['current']}")
            
        except Exception as e:
            logger.error(f"Error fetching VIX data: {e}")
            self.data['market']['vix'] = {'error': str(e)}
    
    def fetch_t_note_future(self):
        """米国10年債先物（ZN=F）のデータを取得"""
        try:
            ticker = yf.Ticker("ZN=F", session=self.session)
            hist = ticker.history(period="5d", interval="1h")

            if hist.empty:
                logger.error("T-Note future data is empty.")
                self.data['market']['t_note_future'] = {'error': 'No data received from yfinance'}
                return
            
            # 4時間足にリサンプリング
            hist.index = pd.to_datetime(hist.index)
            agg_rules = {
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last'
            }
            four_hour_hist = hist.resample('4H', label='left', closed='left').agg(agg_rules).dropna()

            four_hour_data = [
                {
                    'time': index.isoformat(),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close'])
                }
                for index, row in four_hour_hist.iterrows()
            ]

            self.data['market']['t_note_future'] = {
                'current': float(hist['Close'].iloc[-1]),
                'history': four_hour_data
            }
            logger.info(f"T-Note future fetched: {self.data['market']['t_note_future']['current']}")

        except Exception as e:
            logger.error(f"Error fetching T-Note future: {e}")
            self.data['market']['t_note_future'] = {'error': str(e)}
    
    def fetch_economic_indicators(self):
        """経済指標カレンダーをみんかぶから取得"""
        try:
            response = self.session.get(MINKABU_INDICATORS_URL, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')
            
            indicators = []
            
            # 日付ごとにテーブルを処理
            tables = soup.find_all('table', class_='tbl-border')
            
            for table in tables:
                caption = table.find('caption')
                date = caption.text.strip() if caption else ''

                rows = table.find_all('tr', attrs={'data_importance': True})

                for row in rows:
                    importance = int(row['data_importance'])

                    # 重要度3以上のみ表示
                    if importance >= 3:
                        cols = row.find_all('td')

                        time = cols[0].text.strip()
                        country = row['data_country']
                        name = cols[2].text.strip()
                        
                        # 前回ドル円変動幅
                        fluctuation_span = cols[4].find('span')
                        previous_fluctuation = fluctuation_span.text.strip() if fluctuation_span else '---'

                        # 前回・予想・結果
                        previous_value = cols[5].text.strip()
                        forecast = cols[6].text.strip()
                        result = cols[7].text.strip()

                        indicators.append({
                            'date': date,
                            'time': time,
                            'country': country,
                            'name': name,
                            'importance': importance,
                            'previous_fluctuation': previous_fluctuation,
                            'previous_value': previous_value,
                            'forecast': forecast,
                            'result': result
                        })
            
            self.data['indicators']['economic'] = indicators
            logger.info(f"Economic indicators fetched: {len(indicators)} items")
            
        except Exception as e:
            logger.error(f"Error fetching economic indicators: {e}")
            self.data['indicators']['economic'] = []
    
    def fetch_news(self):
        """最新の米国株関連ニュースを取得（curl_cffiセッション使用）"""
        try:
            # Yahoo Financeからニュースを取得
            tickers = ['^GSPC', '^IXIC', '^DJI']  # S&P 500, NASDAQ, DOW
            news_items = []
            
            for ticker_symbol in tickers:
                # curl_cffiセッションを使用
                ticker = yf.Ticker(ticker_symbol, session=self.session)
                news = ticker.news
                
                if news:  # newsが空でないかチェック
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
                if item['title'] not in seen and item['title']:  # タイトルが空でないことも確認
                    seen.add(item['title'])
                    unique_news.append(item)
            
            self.data['news'] = unique_news[:5]  # 上位5件
            logger.info(f"News fetched: {len(self.data['news'])} items")
            
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            self.data['news'] = []
    
    def generate_ai_commentary(self):
        """AIによる市況解説を生成（max_completion_tokens使用）"""
        try:
            # VIXと10年債先物のデータからプロンプトを構築
            market_data = self.data['market']
            
            # データが取得できているか確認
            vix_value = market_data.get('vix', {}).get('current', 'N/A')
            t_note_value = market_data.get('t_note_future', {}).get('current', 'N/A')
            
            # データが取得できていない場合はスキップ
            if vix_value == 'N/A' and t_note_value == 'N/A':
                self.data['market']['ai_commentary'] = "市場データの取得に失敗したため、解説を生成できませんでした。"
                logger.warning("No market data available for AI commentary")
                return
            
            prompt = f"""
            以下の市場データを基に、日本の個人投資家向けに本日の米国市場の状況を簡潔に解説してください。

            VIX: {vix_value}
            米国10年債先物: {t_note_value}

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
                max_completion_tokens=500,  # max_tokensの代わりにmax_completion_tokensを使用
                temperature=0.8
            )
            
            self.data['market']['ai_commentary'] = response.choices[0].message.content
            logger.info("AI commentary generated")
            
        except Exception as e:
            logger.error(f"Error generating AI commentary: {e}")
            self.data['market']['ai_commentary'] = "市況解説の生成に失敗しました。"
    
    def generate_ai_column(self):
        """AIによる週次コラムを生成（max_completion_tokens使用）"""
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
                    max_completion_tokens=500,  # max_tokensの代わりにmax_completion_tokensを使用
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
    
    def save_raw_data(self):
        """Saves intermediate data to a JSON file."""
        raw_data_path = os.path.join(DATA_DIR, 'data_raw.json')
        try:
            with open(raw_data_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            logger.info(f"Raw data saved to {raw_data_path}")
        except Exception as e:
            logger.error(f"Error saving raw data: {e}")

    def load_raw_data(self):
        """Loads intermediate data from a JSON file."""
        raw_data_path = os.path.join(DATA_DIR, 'data_raw.json')
        try:
            with open(raw_data_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            logger.info(f"Raw data loaded from {raw_data_path}")
        except Exception as e:
            logger.error(f"Error loading raw data: {e}")
            raise

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
    
    async def fetch_all_async(self):
        """非同期でスクリーンショットを取得"""
        logger.info("Starting screenshot capture...")
        
        # スクリーンショット取得タスク
        tasks = [
            self.fetch_fear_greed_screenshot(),
            self.fetch_finviz_heatmaps()
        ]
        
        await asyncio.gather(*tasks)
        logger.info("Screenshot capture completed")

    def fetch_raw_data(self):
        """Fetches raw market data and saves to a temporary file."""
        logger.info("Starting raw data fetch...")
        self.fetch_vix_data()
        self.fetch_t_note_future()
        self.fetch_economic_indicators()
        self.fetch_news()
        self.save_raw_data()
        logger.info("Raw data fetch completed.")

    async def generate_report_async(self):
        """Loads raw data, generates reports and screenshots, and saves final data."""
        logger.info("Starting report generation...")
        self.load_raw_data()

        # Update timestamp
        self.data['last_updated'] = datetime.now(TZ_JST).isoformat()

        # Fetch screenshots
        await self.fetch_all_async()

        # Generate AI content
        self.generate_ai_commentary()
        self.generate_ai_column()
        
        # Save final output
        self.save_data()
        logger.info("Report generation completed.")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ['fetch', 'generate']:
        print("Usage: python data_fetcher.py [fetch|generate]", file=sys.stderr)
        sys.exit(1)

    mode = sys.argv[1]
    fetcher = MarketDataFetcher()

    if mode == 'fetch':
        fetcher.fetch_raw_data()
    elif mode == 'generate':
        asyncio.run(fetcher.generate_report_async())