from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import json
import os
from datetime import datetime
from config import DATA_DIR

app = FastAPI(title="Investment Dashboard API")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静的ファイルのマウント
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

@app.get("/")
async def root():
    return {"message": "Investment Dashboard API"}

@app.get("/api/data")
async def get_market_data():
    """最新の市場データを返す"""
    try:
        # 今日のデータファイルを探す
        today = datetime.now().strftime('%Y-%m-%d')
        filename = f"{DATA_DIR}/data_{today}.json"
        
        if not os.path.exists(filename):
            # 今日のデータがない場合は最新のファイルを探す
            files = sorted([f for f in os.listdir(DATA_DIR) if f.startswith('data_')])
            if files:
                filename = f"{DATA_DIR}/{files[-1]}"
            else:
                raise HTTPException(status_code=404, detail="No data available")
        
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)