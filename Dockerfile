FROM python:3.11-slim

WORKDIR /app

# 基本パッケージのインストール
RUN apt-get update && apt-get install -y \
    cron \
    curl \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Pythonパッケージのインストール
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwrightのブラウザと依存関係をインストール
# playwright install-depsでシステムの依存関係を自動インストール
RUN playwright install --with-deps chromium

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
