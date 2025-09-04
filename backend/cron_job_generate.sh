#!/bin/bash

# ログディレクトリ
LOG_DIR="/app/logs"
mkdir -p $LOG_DIR

# 現在時刻をログ
echo "$(date): Starting report generation..." >> $LOG_DIR/cron.log

# Pythonスクリプトを実行
cd /app/backend
python data_fetcher.py generate >> $LOG_DIR/generate.log 2>&1

echo "$(date): Report generation completed" >> $LOG_DIR/cron.log
