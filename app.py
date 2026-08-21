import streamlit as st
import pandas as pd
import warnings
import requests
import json
import os
from datetime import datetime

import data_fetcher
from strategy import convert_to_3_line_break, calculate_indicators, check_rules

warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="Pro Quant Scanner", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    
    .kpi-container {
        display: flex;
        justify-content: space-between;
        gap: 20px;
        margin-bottom: 30px;
        margin-top: 10px;
    }
    .kpi-card {
        background-color: #1E222D;
        padding: 20px;
        border-radius: 10px;
        flex: 1;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        border-left: 5px solid #2962FF;
    }
    .kpi-card.bullish { border-left: 5px solid #089981; }
    .kpi-card.bearish { border-left: 5px solid #F23645; }
    .kpi-title { color: #8A93A6; font-size: 14px; text-transform: uppercase; font-weight: 600; letter-spacing: 1px; margin-bottom: 5px;}
    .kpi-value { color: #FFFFFF; font-size: 32px; font-weight: 700; }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stProgress > div > div > div > div { background-color: #2962FF; }
    th { font-size: 14px !important; color: #8A93A6 !important; }
    </style>
""", unsafe_allow_html=True)

def send_telegram_alert(script_name, timeframe, signal_type, price, time_str):
    bot_token = "YAHAN_APNA_BOT_TOKEN_DAALEIN"
    chat_id = "YAHAN_APNA_CHAT_ID_DAALEIN"
    if bot_token == "YAHAN_APNA_BOT_TOKEN_DAALEIN": return 
        
    message = f"🚨 *ALGO ALERT* \n\n📈 *Script:* {script_name}\n🕒 *Timeframe:* {timeframe}\n⚡ *Signal:* {signal_type}\n💵 *Price:* ₹{price}\n📅 *Time:* {time_str}"
    try: 
        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", data={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"})
    except: pass

st.markdown("<h1 style='text-align: center; color: #FFFFFF; margin-bottom: 0px;'>⚡ PRO QUANT SCANNER</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #8A93A6; font-size: 16px;'>Algorithmic 3-Line Break Detection Engine</p>", unsafe_allow_html=True)
st.markdown("---")

WATCHLIST = {
    "RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "HDFCBANK": "HDFCBANK.NS", 
    "INFY": "INFY.NS", "ICICIBANK": "ICICIBANK.NS", "SBIN": "SBIN.NS",
    "ITC": "ITC.NS", "BHARTIARTL": "BHARTIARTL.NS"
}

st.sidebar.markdown("### 🔑 API Auth (Fyers)")
if not data_fetcher.is_authenticated():
    st.sidebar.error("🔴 Disconnected")
    auth_link = data_fetcher.get_fyers_login_link()
    st.sidebar.markdown(f"**[🔗 Login to Fyers]({auth_link})**", unsafe_allow_html=True)
    
    auth_code = st.sidebar.text_input("Auth Code:")
    if st.sidebar.button("Connect System"):
        if auth_code:
            success, msg = data_fetcher.generate_and_save_token(auth_code)
            if success:
                st.sidebar.success("✅ Connected!")
                st.rerun()
            else:
                st.sidebar.error(msg) 
else:
    st.sidebar.success("🟢 Active Session")
    if st.sidebar.button("Disconnect API"):
        if os.path.exists("fyers_token.txt"):
            os.remove("fyers_token.txt")
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Scan Parameters")
# 3h TIMEFRAME ADDED HERE
selected_timeframes = st.sidebar.multiselect("Select Timeframes:", ["15m", "1h", "3h", "1d"], default=["1h", "3h", "1d"])
enable_telegram = st.sidebar.checkbox("📲 Enable Telegram Alerts", value=False)

st.sidebar.markdown("<br>", unsafe_allow_html=True)
start_scan = st.sidebar.button("🚀 INITIATE SCAN", use_container_width=True, type="primary")

if start_scan:
    if not data_fetcher.is_authenticated():
        st.error("⚠️ System Offline: Please connect Fyers API from the sidebar.")
        st.stop()
        
    alert_results = []
    total_bullish = 0
    total_bearish = 0
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    today_date = datetime.now().date()
    
    for i, (name, symbol) in enumerate(WATCHLIST.items()):
        status_text.markdown(f"**Scanning {name}...** `({i+1}/{len(WATCHLIST)})`")
        
        for tf in selected_timeframes:
            raw_df = data_fetcher.fetch_script_data(symbol, interval=tf)
            
            if raw_df is not None:
                three_line_df = convert_to_3_line_break(raw_df)
                if three_line_df is not None:
                    processed_df = calculate_indicators(three_line_df, fast_ema=21, slow_ema=44)
                    signal_list = check_rules(processed_df, max_signals=6)
                    
                    if signal_list:
                        for idx, sig in enumerate(signal_list):
                            if "Bullish" in sig["signal"]: total_bullish += 1
                            elif "Bearish" in sig["signal"]: total_bearish += 1
                            
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
    
    st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-card">
                <div class="kpi-title">Total Symbols Scanned</div>
                <div class="kpi-value">{len(WATCHLIST)}</div>
            </div>
            <div class="kpi-card bullish">
                <div class="kpi-title">Total Bullish Crossovers</div>
                <div class="kpi-value" style="color: #089981;">{total_bullish}</div>
            </div>
            <div class="kpi-card bearish">
                <div class="kpi-title">Total Bearish Crossovers</div>
                <div class="kpi-value" style="color: #F23645;">{total_bearish}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if alert_results:
        result_df = pd.DataFrame(alert_results)
        result_df = result_df.sort_values(by="Time", ascending=False)
        
        def color_signal(val):
            if isinstance(val, str):
                if 'Bullish' in val: return 'color: #089981; font-weight: bold;'
                if 'Bearish' in val: return 'color: #F23645; font-weight: bold;'
                if 'Fresh' in val: return 'color: #FF9800; font-weight: bold;'
            return ''
            
        tabs = st.tabs([f"🕒 {tf} Timeframe" for tf in result_df['Timeframe'].unique()])
        
        for i, tf in enumerate(result_df['Timeframe'].unique()):
            with tabs[i]:
                tf_df = result_df[result_df['Timeframe'] == tf].drop(columns=['Timeframe']).reset_index(drop=True)
                
                bull_df = tf_df[tf_df['Signal'].str.contains('Bullish', case=False, na=False)].reset_index(drop=True)
                bear_df = tf_df[tf_df['Signal'].str.contains('Bearish', case=False, na=False)].reset_index(drop=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("<h4 style='color: #089981; margin-bottom: 10px;'>🟢 Bullish Crossovers (Buy Alerts)</h4>", unsafe_allow_html=True)
                    if not bull_df.empty:
                        styled_bull = bull_df.style.map(color_signal, subset=['Signal', 'Status'])
                        st.dataframe(
                            styled_bull,
                            use_container_width=True,
                            hide_index=True,
                            height=400,
                            column_config={
                                "Script": st.column_config.TextColumn("📌 Symbol", width="small"),
                                "Status": st.column_config.TextColumn("Status", width="small"),
                                "Signal": st.column_config.TextColumn("🎯 Action", width="medium"),
                                "Price": st.column_config.NumberColumn("💵 Trigger Price", format="₹ %.2f"),
                                "Time": st.column_config.DatetimeColumn("🕒 Timestamp", format="DD-MMM-YYYY HH:mm")
                            }
                        )
                    else:
                        st.info("No Bullish signals found in this timeframe.")
                
                with col2:
                    st.markdown("<h4 style='color: #F23645; margin-bottom: 10px;'>🔴 Bearish Crossovers (Sell Alerts)</h4>", unsafe_allow_html=True)
                    if not bear_df.empty:
                        styled_bear = bear_df.style.map(color_signal, subset=['Signal', 'Status'])
                        st.dataframe(
                            styled_bear,
                            use_container_width=True,
                            hide_index=True,
                            height=400,
                            column_config={
                                "Script": st.column_config.TextColumn("📌 Symbol", width="small"),
                                "Status": st.column_config.TextColumn("Status", width="small"),
                                "Signal": st.column_config.TextColumn("🎯 Action", width="medium"),
                                "Price": st.column_config.NumberColumn("💵 Trigger Price", format="₹ %.2f"),
                                "Time": st.column_config.DatetimeColumn("🕒 Timestamp", format="DD-MMM-YYYY HH:mm")
                            }
                        )
                    else:
                        st.info("No Bearish signals found in this timeframe.")
    else:
        st.info("No crossover signals found right now.")
else:
    st.info("👈 Please Select Parameters from Sidebar and Click 'INITIATE SCAN'")
