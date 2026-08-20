import streamlit as st
import pandas as pd
import warnings
import requests
import json
import os

from data_fetcher import fetch_script_data
from strategy import convert_to_3_line_break, calculate_indicators, check_rules

warnings.filterwarnings('ignore')
st.set_page_config(page_title="Hybrid Trading System", layout="wide")

def send_telegram_alert(script_name, timeframe, signal_type, price, time_str):
    bot_token = "YAHAN_APNA_BOT_TOKEN_DAALEIN"
    chat_id = "YAHAN_APNA_CHAT_ID_DAALEIN"
    if bot_token == "YAHAN_APNA_BOT_TOKEN_DAALEIN": return 
        
    message = f"🚨 *ALGO ALERT* 🚨\n\n📈 *Script:* {script_name}\n🕒 *Timeframe:* {timeframe}\n⚡ *Signal:* {signal_type}\n💵 *Price:* ₹{price}\n📅 *Time:* {time_str}"
    try: requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", data={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"})
    except: pass

def load_optimized_params():
    if os.path.exists("optimized_params.json"):
        with open("optimized_params.json", "r") as f: return json.load(f)
    return {}

st.title("⚡ Hybrid 3-Line Break Scanner (Live API + yfinance)")

WATCHLIST = {
    "RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "HDFCBANK": "HDFCBANK.NS", 
    "INFY": "INFY.NS", "ICICIBANK": "ICICIBANK.NS", "SBIN": "SBIN.NS"
}

st.sidebar.header("⚙️ Controls")
selected_timeframes = st.sidebar.multiselect("Timeframes:", ["15m", "1h", "3h", "1d"], default=["1h", "1d"])
enable_telegram = st.sidebar.checkbox("📲 Telegram Alerts", value=False)

best_rules_data = load_optimized_params()
use_optimized = st.sidebar.checkbox("⚙️ Apply AI Parameters", value=False) if best_rules_data else False

if st.sidebar.button("🚀 Run Scan"):
    alert_results = []
    progress_bar = st.progress(0)
    
    for i, (name, symbol) in enumerate(WATCHLIST.items()):
        for tf in selected_timeframes:
            period = "60d" if tf == "15m" else "730d" if tf in ["1h", "3h"] else "max"
            raw_df = fetch_script_data(symbol, interval=tf, period=period)
            
            if raw_df is not None:
                three_line_df = convert_to_3_line_break(raw_df)
                if three_line_df is not None:
                    f_ema, s_ema = (best_rules_data.get(name, {}).get("fast", 21), best_rules_data.get(name, {}).get("slow", 44)) if use_optimized else (21, 44)
                    processed_df = calculate_indicators(three_line_df, fast_ema=f_ema, slow_ema=s_ema)
                    signal_list = check_rules(processed_df, max_signals=5)
                    
                    if signal_list:
                        for idx, sig in enumerate(signal_list):
                            alert_results.append({
                                "Script": name, "Timeframe": tf, "Signal": sig["signal"], 
                                "Price": round(sig["close"], 2), "Time": sig["time"]
                            })
                            if enable_telegram and idx == 0:
                                send_telegram_alert(name, tf, sig["signal"], round(sig["close"], 2), sig["time"])
                                
        progress_bar.progress(min((i + 1) / len(WATCHLIST), 1.0))
        
    progress_bar.empty()
    st.markdown("---")
    
    if alert_results:
        result_df = pd.DataFrame(alert_results)
        tabs = st.tabs([f"🕒 {tf}" for tf in result_df['Timeframe'].unique()])
        for i, tf in enumerate(result_df['Timeframe'].unique()):
            with tabs[i]:
                st.dataframe(result_df[result_df['Timeframe'] == tf].drop(columns=['Timeframe']).reset_index(drop=True), use_container_width=True)
    else:
        st.info("No signals found.")
