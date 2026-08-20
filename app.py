import streamlit as st
import pandas as pd
import warnings
import requests
import json
import os
from datetime import datetime

from data_fetcher import fetch_script_data
from strategy import convert_to_3_line_break, calculate_indicators, check_rules

warnings.filterwarnings('ignore')

# 1. Page Configuration (Must be first)
st.set_page_config(
    page_title="Hybrid Trading System", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern dashboard look
st.markdown("""
    <style>
    .metric-card {
        background-color: #1E1E2E;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        border: 1px solid #333;
    }
    .stProgress > div > div > div > div {
        background-color: #00ff00;
    }
    </style>
""", unsafe_allow_html=True)

def send_telegram_alert(script_name, timeframe, signal_type, price, time_str):
    bot_token = "YAHAN_APNA_BOT_TOKEN_DAALEIN"
    chat_id = "YAHAN_APNA_CHAT_ID_DAALEIN"
    if bot_token == "YAHAN_APNA_BOT_TOKEN_DAALEIN": return 
        
    message = f"🚨 *ALGO ALERT* 🚨\n\n📈 *Script:* {script_name}\n🕒 *Timeframe:* {timeframe}\n⚡ *Signal:* {signal_type}\n💵 *Price:* ₹{price}\n📅 *Time:* {time_str}"
    try: 
        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", data={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"})
    except: pass

def load_optimized_params():
    if os.path.exists("optimized_params.json"):
        with open("optimized_params.json", "r") as f: return json.load(f)
    return {}

# --- MAIN DASHBOARD HEADER ---
st.title("⚡ Hybrid 3-Line Break Scanner")
st.markdown("**(Live API + yfinance)** | Institutional Grade Dashboard")

WATCHLIST = {
    "RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "HDFCBANK": "HDFCBANK.NS", 
    "INFY": "INFY.NS", "ICICIBANK": "ICICIBANK.NS", "SBIN": "SBIN.NS"
}

# --- SIDEBAR CONTROLS ---
st.sidebar.header("⚙️ Controls")
selected_timeframes = st.sidebar.multiselect("Timeframes:", ["15m", "1h", "3h", "1d"], default=["1h", "1d"])
enable_telegram = st.sidebar.checkbox("📲 Telegram Alerts", value=False)

best_rules_data = load_optimized_params()
use_optimized = st.sidebar.checkbox("🤖 Apply AI Parameters", value=False) if best_rules_data else False

if st.sidebar.button("🚀 Run Scan", use_container_width=True):
    alert_results = []
    
    # KPI Counters
    total_bullish = 0
    total_bearish = 0
    
    # Placeholders for Top Metrics (will be updated after scan)
    metric_cols = st.columns(3)
    
    st.markdown("---")
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    today_date = datetime.now().date()
    
    for i, (name, symbol) in enumerate(WATCHLIST.items()):
        status_text.text(f"Scanning {name}... ({i+1}/{len(WATCHLIST)})")
        
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
                            # Count active signals
                            if "Bullish" in sig["signal"]: total_bullish += 1
                            elif "Bearish" in sig["signal"]: total_bearish += 1
                            
                            # Determine if signal is Fresh (Today) or Historical
                            try:
                                sig_date = pd.to_datetime(sig["time"]).date()
                                status = "🔥 Fresh" if sig_date == today_date else "⏳ History"
                            except:
                                status = "⏳ History"

                            alert_results.append({
                                "Script": name, 
                                "Timeframe": tf, 
                                "Signal": sig["signal"], 
                                "Price": round(sig["close"], 2), 
                                "Time": pd.to_datetime(sig["time"]),
                                "Status": status
                            })
                            
                            if enable_telegram and idx == 0 and status == "🔥 Fresh":
                                send_telegram_alert(name, tf, sig["signal"], round(sig["close"], 2), sig["time"])
                                
        progress_bar.progress(min((i + 1) / len(WATCHLIST), 1.0))
        
    progress_bar.empty()
    status_text.empty()
    
    # Update KPI Metrics
    with metric_cols[0]:
        st.metric(label="Total Stocks Scanned", value=len(WATCHLIST))
    with metric_cols[1]:
        st.metric(label="🟢 Active Bullish Signals", value=total_bullish)
    with metric_cols[2]:
        st.metric(label="🔴 Active Bearish Signals", value=total_bearish)
    
    if alert_results:
        result_df = pd.DataFrame(alert_results)
        # Sort by Time descending so latest signals are always on top
        result_df = result_df.sort_values(by="Time", ascending=False)
        
        tabs = st.tabs([f"🕒 {tf}" for tf in result_df['Timeframe'].unique()])
        
        for i, tf in enumerate(result_df['Timeframe'].unique()):
            with tabs[i]:
                tf_df = result_df[result_df['Timeframe'] == tf].drop(columns=['Timeframe']).reset_index(drop=True)
                
                # Pro-level Dataframe styling
                st.dataframe(
                    tf_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Script": st.column_config.TextColumn("📌 Script", width="small"),
                        "Status": st.column_config.TextColumn("Status", width="small"),
                        "Signal": st.column_config.TextColumn("🎯 Action", width="medium"),
                        "Price": st.column_config.NumberColumn("💵 Trigger Price", format="₹ %.2f"),
                        "Time": st.column_config.DatetimeColumn("🕒 Timestamp", format="DD-MMM-YYYY HH:mm")
                    }
                )
    else:
        st.info("No crossover signals found right now.")
