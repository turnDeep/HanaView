#!/bin/bash

# ログディレクトリ
LOG_DIR="/app/logs"
mkdir -p $LOG_DIR

# 現在時刻をログ
echo "$(date): Starting data fetch..." >> $LOG_DIR/cron.log

# Pythonスクリプトを実行
cd /app/backend
python data_fetcher.py >> $LOG_DIR/fetch.log 2>&1

echo "$(date): Data fetch completed" >> $LOG_DIR/cron.log