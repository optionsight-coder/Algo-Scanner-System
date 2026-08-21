import pandas as pd
import datetime
import time
import os
from fyers_apiv3 import fyersModel

APP_ID = "ZF5ZUHTUQN-100"
SECRET_KEY = "MYQSBOIJDA"
REDIRECT_URI = "https://127.0.0.1"
TOKEN_FILE = "fyers_token.txt"

def get_fyers_login_link():
    session = fyersModel.SessionModel(client_id=APP_ID, secret_key=SECRET_KEY, redirect_uri=REDIRECT_URI, response_type="code", grant_type="authorization_code")
    return session.generate_authcode()

def generate_and_save_token(auth_code):
    session = fyersModel.SessionModel(client_id=APP_ID, secret_key=SECRET_KEY, redirect_uri=REDIRECT_URI, response_type="code", grant_type="authorization_code")
    session.set_token(auth_code.strip()) 
    response = session.generate_token()
    
    if "access_token" in response:
        with open(TOKEN_FILE, 'w') as f:
            f.write(response['access_token'])
        return True, "Connected!"
    return False, f"API Error: {response.get('message', str(response))}"

def is_authenticated():
    return os.path.exists(TOKEN_FILE)

def fetch_script_data(symbol, interval):
    """
    100+ Stocks ke liye Optimized Pagination Logic.
    """
    if not is_authenticated(): return None 
        
    try:
        with open(TOKEN_FILE, 'r') as f:
            access_token = f.read().strip()
            
        fyers = fyersModel.FyersModel(client_id=APP_ID, is_async=False, token=access_token, log_path="")
        fyers_sym = f"NSE:{symbol.replace('.NS', '')}-EQ" if symbol.endswith('.NS') else symbol
            
        tf_map = {'15m': '15', '1h': '60', '3h': '180', '1d': 'D'}
        res = tf_map.get(interval, 'D')
        
        # SMART DATA SIZING FOR 100+ STOCKS
        if interval in ['15m', '1h', '3h']:
            chunk_days = 99
            total_days_needed = 99 
        else:
            chunk_days = 364
            total_days_needed = 1000 
        
        all_data = []
        current_end = datetime.date.today()
        
        while total_days_needed > 0:
            days_to_fetch = min(chunk_days, total_days_needed)
            current_start = current_end - datetime.timedelta(days=days_to_fetch)
            
            data = {
                "symbol": fyers_sym,
                "resolution": res,
                "date_format": "1",
                "range_from": current_start.strftime('%Y-%m-%d'),
                "range_to": current_end.strftime('%Y-%m-%d'),
                "cont_flag": "1"
            }
            
            response = fyers.history(data=data)
            
            if response.get('s') == 'ok' and response.get('candles'):
                all_data.extend(response['candles'])
                
            # MAGICAL SPEED BREAKER (0.33 sec pause to prevent API ban on 100 stocks)
            time.sleep(0.33) 
            
            current_end = current_start - datetime.timedelta(days=1)
            total_days_needed -= days_to_fetch
            
        if not all_data: return None
        
        df = pd.DataFrame(all_data, columns=['datetime', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['datetime'] = pd.to_datetime(df['datetime'], unit='s')
        df['datetime'] = df['datetime'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)
        
        df.drop_duplicates(subset=['datetime'], inplace=True)
        df.sort_values(by='datetime', inplace=True)
        df.set_index('datetime', inplace=True)
        
        return df
            
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None
