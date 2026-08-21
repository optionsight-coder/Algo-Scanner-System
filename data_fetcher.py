import pandas as pd
import datetime
import os
from fyers_apiv3 import fyersModel

# Aapke Fyers API Credentials
APP_ID = "ZF5ZUHTUQN-100"
SECRET_KEY = "MYQSBOIJDA"
REDIRECT_URI = "https://127.0.0.1"
TOKEN_FILE = "fyers_token.txt"

def get_fyers_login_link():
    """Streamlit me dikhane ke liye Login Link generate karta hai."""
    session = fyersModel.SessionModel(
        client_id=APP_ID,
        secret_key=SECRET_KEY,
        redirect_uri=REDIRECT_URI,
        response_type="code",
        grant_type="authorization_code"
    )
    return session.generate_authcode()

def generate_and_save_token(auth_code):
    """User ke diye auth_code se Access Token banakar save karta hai."""
    session = fyersModel.SessionModel(
        client_id=APP_ID,
        secret_key=SECRET_KEY,
        redirect_uri=REDIRECT_URI,
        response_type="code",
        grant_type="authorization_code"
    )
    # White space hatane ke liye strip() lagaya hai
    session.set_token(auth_code.strip()) 
    response = session.generate_token()
    
    if "access_token" in response:
        with open(TOKEN_FILE, 'w') as f:
            f.write(response['access_token'])
        return True, "Connected!"
    else:
        # Fyers ka exact error message bhejega
        error_msg = response.get("message", str(response))
        return False, f"API Error: {error_msg}"

def is_authenticated():
    """Check karta hai ki token file exist karti hai ya nahi."""
    return os.path.exists(TOKEN_FILE)

def fetch_script_data(symbol, interval, period='max'):
    """Fyers API se data fetch karta hai."""
    if not is_authenticated():
        return None 
        
    try:
        with open(TOKEN_FILE, 'r') as f:
            access_token = f.read().strip()
            
        fyers = fyersModel.FyersModel(client_id=APP_ID, is_async=False, token=access_token, log_path="")
        
        # Symbol Formatting
        if symbol.endswith('.NS'):
            fyers_sym = f"NSE:{symbol.replace('.NS', '')}-EQ"
        else:
            fyers_sym = symbol
            
        tf_map = {'15m': '15', '1h': '60', '3h': '180', '1d': 'D'}
        res = tf_map.get(interval, 'D')
        
        to_date = datetime.date.today()
        if interval in ['15m', '1h', '3h']:
            from_date = to_date - datetime.timedelta(days=99) 
        else:
            from_date = to_date - datetime.timedelta(days=700) 
            
        data = {
            "symbol": fyers_sym,
            "resolution": res,
            "date_format": "1",
            "range_from": from_date.strftime('%Y-%m-%d'),
            "range_to": to_date.strftime('%Y-%m-%d'),
            "cont_flag": "1"
        }
        
        response = fyers.history(data=data)
        
        if response.get('s') == 'ok':
            df = pd.DataFrame(response['candles'], columns=['datetime', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['datetime'] = pd.to_datetime(df['datetime'], unit='s')
            df['datetime'] = df['datetime'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)
            df.set_index('datetime', inplace=True)
            return df
        else:
            return None
            
    except Exception as e:
        return None
