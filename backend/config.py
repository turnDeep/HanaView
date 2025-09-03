import os
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# OpenAI API設定
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = 'gpt-4o-mini'

# タイムゾーン設定
TZ_JST = pytz.timezone('Asia/Tokyo')
TZ_US_EASTERN = pytz.timezone('US/Eastern')

# データ保存先
DATA_DIR = '../data'

# 市場時間設定（夏時間・冬時間考慮）
def is_dst():
    """米国が夏時間かどうかを判定"""
    now = datetime.now(TZ_US_EASTERN)
    return bool(now.dst())

def get_market_close_time_jst():
    """米国市場クローズ時間を日本時間で返す"""
    if is_dst():
        # 夏時間: 米国16:00 = 日本5:00（翌日）
        return 5
    else:
        # 冬時間: 米国16:00 = 日本6:00（翌日）
        return 6

# yfinanceのディレイ（15分）を考慮した取得時間
DATA_FETCH_DELAY_MINUTES = 15

# API URLs
CNN_FEAR_GREED_URL = 'https://production.dataviz.cnn.io/index/fearandgreed/graphdata/'
MINKABU_INDICATORS_URL = 'https://fx.minkabu.jp/indicators'