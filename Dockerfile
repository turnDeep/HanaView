FROM python:3.11-slim

WORKDIR /app

# 必要なパッケージのインストール
RUN apt-get update && apt-get install -y \
    cron \
    curl \
    wget \
    # Playwrightの依存関係
    libglib2.0-0 \
    libgconf-2-4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libgdk-pixbuf2.0-0 \
    libgtk-3-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    libnspr4 \
    libnss3 \
    && rm -rf /var/lib/apt/lists/*

# Pythonパッケージのインストール
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwrightブラウザのインストール
RUN playwright install chromium
RUN playwright install-deps

# アプリケーションファイルのコピー
COPY backend /app/backend
COPY frontend /app/frontend

# データディレクトリの作成
RUN mkdir -p /app/data /app/logs /app/screenshots

# cronジョブの設定
COPY crontab /etc/cron.d/data-fetch
RUN chmod 0644 /etc/cron.d/data-fetch && \
    crontab /etc/cron.d/data-fetch

# 実行権限の付与
RUN chmod +x /app/backend/cron_job.sh

EXPOSE 8000

# 起動スクリプト
CMD cron && cd /app/backend && uvicorn main:app --host 0.0.0.0 --port 8000
