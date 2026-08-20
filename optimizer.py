import pandas as pd
import pandas_ta as ta
import numpy as np
import json
from datetime import datetime
from data_fetcher import fetch_script_data
from strategy import convert_to_3_line_break

CONFIG_FILE = "optimized_params.json"
MY_WATCHLIST = {"RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "HDFCBANK": "HDFCBANK.NS", "SBIN": "SBIN.NS"}

def simulate_trades(df, fast_col, slow_col):
    temp = df.dropna(subset=[fast_col, slow_col]).copy()
    temp['Trend'] = np.where(temp[fast_col] > temp[slow_col], 1, -1)
    temp['Signal'] = temp['Trend'].diff()
    net_profit, entry_price, in_pos = 0, 0, False
    
    for index, row in temp.iterrows():
        close_price = row['Close'] if 'Close' in row else row.get('close', 0)
        if row['Signal'] == 2 and not in_pos: 
            entry_price, in_pos = close_price, True
        elif row['Signal'] == -2 and in_pos: 
            net_profit += (close_price - entry_price)
            in_pos = False
    return net_profit

def run_daily_optimization():
    optimized_data = {}
    print(f"🚀 Started Optimization at {datetime.now()}")
    for name, symbol in MY_WATCHLIST.items():
        df = fetch_script_data(symbol, interval="1d", period="365d")
        if df is not None:
            lb_df = convert_to_3_line_break(df)
            best_profit, best_params = -99999, {"fast": 21, "slow": 44}
            
            target_col = 'Close' if 'Close' in lb_df.columns else lb_df.columns[0]
            lb_df[target_col] = pd.to_numeric(lb_df[target_col], errors='coerce')
            
            for f in range(5, 25, 2):
                for s in range(30, 61, 5):
                    temp = lb_df.copy()
                    temp[f'EMA_{f}'] = ta.ema(temp[target_col], length=f)
                    temp[f'EMA_{s}'] = ta.ema(temp[target_col], length=s)
                    profit = simulate_trades(temp, f'EMA_{f}', f'EMA_{s}')
                    if profit > best_profit:
                        best_profit, best_params = profit, {"fast": f, "slow": s}
            optimized_data[name] = best_params
            print(f"✅ {name}: {best_params} | Virtual Profit: ₹{round(best_profit, 2)}")
            
    with open(CONFIG_FILE, "w") as f: json.dump(optimized_data, f, indent=4)
    print("🎉 Done! JSON file updated.")

if __name__ == "__main__":
    run_daily_optimization()
