import yfinance as yf
import requests
import pandas as pd
from datetime import datetime

# 🔴 AAPKI LIVE CLOUDFLARE API KA LINK
API_BASE_URL = "https://indian-stock-market-api.option-sight.workers.dev"

def fetch_script_data(symbol, interval="1d", period="365d"):
    """
    Hybrid Fetcher: Historical data from yfinance + Live Tick from Cloudflare API.
    """
    # 1. Historical Data (yfinance se laana)
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    
    if df is None or df.empty:
        return None
        
    # MultiIndex column fix (yfinance ke naye update ke liye)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # 2. Live Data Stitching (Aapki Cloudflare API se live tick laana)
    clean_symbol = symbol.replace(".NS", "") 
    api_url = f"{API_BASE_URL}/stock?symbol={clean_symbol}&res=num"
    
    try:
        response = requests.get(api_url, timeout=3)
        if response.status_code == 200:
            api_response = response.json()
            
            # 🔴 JSON se sahi data nikalna (Screenshot ke mutabiq)
            if api_response.get("status") == "success":
                live_price = api_response.get("data", {}).get("last_price")
                
                if live_price:
                    current_time = pd.to_datetime(datetime.now())
                    
                    # Live tick ko 'Aaj ki aakhri Candle' bana kar DataFrame me jodna
                    new_row = pd.DataFrame({
                        'Open': [live_price],
                        'High': [live_price],
                        'Low': [live_price],
                        'Close': [live_price],
                        'Volume': [0]
                    }, index=[current_time])
                    
                    df = pd.concat([df, new_row])
                    print(f"✅ {symbol}: Live Price (₹{live_price}) lag gaya!")
    except Exception as e:
        # Agar API ka server down ho, toh code crash nahi hoga, sirf yfinance data se chalega
        print(f"⚠️ Live API error for {symbol}, using yfinance data only: {e}")
        
    return df
