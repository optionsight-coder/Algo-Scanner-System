import pandas as pd
import pandas_ta as ta
import numpy as np

def convert_to_3_line_break(df):
    if df is None or df.empty: return df
    close_col = 'Close' if 'Close' in df.columns else 'close' if 'close' in df.columns else None
    if not close_col: return df
        
    df = df.copy()
    df[close_col] = pd.to_numeric(df[close_col], errors='coerce')
    
    lb_closes, lb_dates = [], []
    last_price = df[close_col].iloc[0]
    lb_closes.append(last_price)
    lb_dates.append(df.index[0])
    
    trend = 0 
    up_blocks, down_blocks = [], []
    
    for i in range(1, len(df)):
        current_price = df[close_col].iloc[i]
        date = df.index[i]
        if pd.isna(current_price): continue
        
        if trend == 0:
            if current_price > last_price:
                trend = 1
                up_blocks.append(current_price)
                lb_closes.append(current_price)
                lb_dates.append(date)
                last_price = current_price
            elif current_price < last_price:
                trend = -1
                down_blocks.append(current_price)
                lb_closes.append(current_price)
                lb_dates.append(date)
                last_price = current_price
        elif trend == 1: 
            reversal_price = min(up_blocks[-3:]) if len(up_blocks) >= 3 else up_blocks[0]
            if current_price < reversal_price:
                trend = -1 
                down_blocks = [current_price]
                lb_closes.append(current_price)
                lb_dates.append(date)
                last_price = current_price
            elif current_price > last_price:
                up_blocks.append(current_price)
                lb_closes.append(current_price)
                lb_dates.append(date)
                last_price = current_price
        elif trend == -1: 
            reversal_price = max(down_blocks[-3:]) if len(down_blocks) >= 3 else down_blocks[0]
            if current_price > reversal_price:
                trend = 1 
                up_blocks = [current_price]
                lb_closes.append(current_price)
                lb_dates.append(date)
                last_price = current_price
            elif current_price < last_price:
                down_blocks.append(current_price)
                lb_closes.append(current_price)
                lb_dates.append(date)
                last_price = current_price
                
    lb_df = pd.DataFrame({close_col: lb_closes}, index=lb_dates)
    return lb_df

def calculate_indicators(df, fast_ema=21, slow_ema=44):
    if df is not None and not df.empty:
        target_col = 'Close' if 'Close' in df.columns else 'close' if 'close' in df.columns else df.columns[0]
        df[target_col] = pd.to_numeric(df[target_col], errors='coerce')
        
        # EMA Calculation
        df['EMA_Fast'] = ta.ema(df[target_col], length=fast_ema)
        df['EMA_Slow'] = ta.ema(df[target_col], length=slow_ema)
        
        # 🔴 REPAINTING FIX: Pichli 2 closed candles ka data nikalna
        df['EMA_Fast_t1'] = df['EMA_Fast'].shift(1)
        df['EMA_Slow_t1'] = df['EMA_Slow'].shift(1)
        
        df['EMA_Fast_t2'] = df['EMA_Fast'].shift(2)
        df['EMA_Slow_t2'] = df['EMA_Slow'].shift(2)
        
        # Default Signal aur Trend
        df['Signal'] = 0
        df['Trend'] = np.where(df['EMA_Fast'] > df['EMA_Slow'], 1, -1)
        
        # 🟢 EXACT CROSSOVER LOGIC (On Closed Candles Only)
        # Bullish: Pichli se pichli me Fast niche/barabar tha, aur latest closed me upar aa gaya
        bullish_cond = (df['EMA_Fast_t2'] <= df['EMA_Slow_t2']) & (df['EMA_Fast_t1'] > df['EMA_Slow_t1'])
        
        # 🔴 EXACT CROSSOVER LOGIC (On Closed Candles Only)
        # Bearish: Pichli se pichli me Fast upar/barabar tha, aur latest closed me niche aa gaya
        bearish_cond = (df['EMA_Fast_t2'] >= df['EMA_Slow_t2']) & (df['EMA_Fast_t1'] < df['EMA_Slow_t1'])
        
        # Compatible numbering (2 for Bullish, -2 for Bearish)
        df.loc[bullish_cond, 'Signal'] = 2
        df.loc[bearish_cond, 'Signal'] = -2
        
        # Extra columns drop karna taaki system halka rahe
        df.drop(columns=['EMA_Fast_t1', 'EMA_Slow_t1', 'EMA_Fast_t2', 'EMA_Slow_t2'], inplace=True, errors='ignore')
        
    return df

def check_rules(df, max_signals=7):
    signals = []
    if df is not None and not df.empty:
        temp_df = df.dropna(subset=['EMA_Fast', 'EMA_Slow', 'Signal'])
        # Signal 2 (Bullish) aur -2 (Bearish) check kar raha hai
        signal_rows = temp_df[temp_df['Signal'].isin([2, -2])].tail(max_signals)
        
        for index, row in signal_rows.iterrows():
            sig_type = "Bullish Crossover 🟢" if row['Signal'] == 2 else "Bearish Crossover 🔴"
            close_col = 'Close' if 'Close' in row else 'close' if 'close' in row else df.columns[0]
            try: formatted_time = pd.to_datetime(index).strftime('%Y-%m-%d %H:%M')
            except: formatted_time = str(index)
                
            signals.append({
                "rule_no": "EMA Crossover",
                "signal": sig_type,
                "close": row[close_col],
                "time": formatted_time
            })
    return signals[::-1]
