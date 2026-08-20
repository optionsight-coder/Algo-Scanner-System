import yfinance as yf
import requests
import pandas as pd
from datetime import datetime

# 🔴 YAHAN APNI GITHUB API KA DEPLOYED LINK DAALEIN
API_BASE_URL = "https://your-deployed-api-url.com" 

def fetch_script_data(symbol, interval="1d", period="365d"):
    # 1. Historical Data (yfinance)
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    
    if df is None or df.empty:
        return None
        
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # 2. Live Data Stitching (GitHub API)
    clean_symbol = symbol.replace(".NS", "") 
    api_url = f"{API_BASE_URL}/stock?symbol={clean_symbol}&res=num"
    
    try:
        response = requests.get(api_url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            live_price = data.get("price") or data.get("currentPrice") 
            
            if live_price:
                current_time = pd.to_datetime(datetime.now())
                new_row = pd.DataFrame({
                    'Open': [live_price],
                    'High': [live_price],
                    'Low': [live_price],
                    'Close': [live_price],
                    'Volume': [0]
                }, index=[current_time])
                
                df = pd.concat([df, new_row])
    except Exception as e:
        pass # API fail hone par yfinance data use hoga
        
    return df
