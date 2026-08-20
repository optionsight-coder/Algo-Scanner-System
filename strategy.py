import pandas as pd
import pandas_ta as ta
import numpy as np

def convert_to_3_line_break(df):
    if df is None or df.empty: return df
    close_col = 'Close' if 'Close' in df.columns else 'close' if 'close' in df.columns else None
    if not close_col: return df
        
    df = df.copy()
    df[close_col] = pd.to_numeric(df[close_col], errors='coerce')
    
    blocks = []
    first_price = df[close_col].iloc[0]
    start_idx = 1
    
    # 1. Pehla block banana
    for i in range(1, len(df)):
        if not pd.isna(df[close_col].iloc[i]) and df[close_col].iloc[i] != first_price:
            current_price = df[close_col].iloc[i]
            if current_price > first_price:
                blocks.append({'high': current_price, 'low': first_price, 'close': current_price, 'trend': 1, 'date': df.index[i]})
            else:
                blocks.append({'high': first_price, 'low': current_price, 'close': current_price, 'trend': -1, 'date': df.index[i]})
            start_idx = i + 1
            break

    if not blocks:
        return df

    # 2. Main 3-Line Break Logic (With TradingView High/Low & Error Fixes)
    for i in range(start_idx, len(df)):
        current_price = df[close_col].iloc[i]
        date = df.index[i]
        if pd.isna(current_price): continue
        
        last_block = blocks[-1]
        
        if last_block['trend'] == 1: # Trend UP hai
            if current_price > last_block['high']:
                # Continuation UP
                blocks.append({'high': current_price, 'low': last_block['high'], 'close': current_price, 'trend': 1, 'date': date})
            else:
                # Reversal Check DOWN (Pichle max 3 blocks ka lowest Low)
                up_blocks = [b for b in blocks if b['trend'] == 1]
                if not up_blocks:
                    reversal_price = last_block['low']
                else:
                    last_3_up = up_blocks[-3:]
                    reversal_price = min([b['low'] for b in last_3_up])
                
                if current_price < reversal_price:
                    # Reversal DOWN
                    blocks.append({'high': last_block['high'], 'low': current_price, 'close': current_price, 'trend': -1, 'date': date})
                    
        elif last_block['trend'] == -1: # Trend DOWN hai
            if current_price < last_block['low']:
                # Continuation DOWN
                blocks.append({'high': last_block['low'], 'low': current_price, 'close': current_price, 'trend': -1, 'date': date})
            else:
                # Reversal Check UP (Pichle max 3 blocks ka highest High)
                down_blocks = [b for b in blocks if b['trend'] == -1]
                if not down_blocks:
                    reversal_price = last_block['high']
                else:
                    last_3_down = down_blocks[-3:]
                    reversal_price = max([b['high'] for b in last_3_down])
                
                if current_price > reversal_price:
                    # Reversal UP
                    blocks.append({'high': current_price, 'low': last_block['low'], 'close': current_price, 'trend': 1, 'date': date})

    # 3. Blocks se wapas dataframe banana jise EMA padh sake
    lb_closes = [b['close'] for b in blocks]
    lb_dates = [b['date'] for b in blocks]
    lb_df = pd.DataFrame({close_col: lb_closes}, index=lb_dates)
    
    return lb_df

def calculate_indicators(df, fast_ema=21, slow_ema=44):
    if df is not None and not df.empty:
        target_col = 'Close' if 'Close' in df.columns else 'close' if 'close' in df.columns else df.columns[0]
        df[target_col] = pd.to_numeric(df[target_col], errors='coerce')
        
        # EMA Calculations
        df['EMA_Fast'] = ta.ema(df[target_col], length=fast_ema)
        df['EMA_Slow'] = ta.ema(df[target_col], length=slow_ema)
        
        # Repainting Fix: Shift data by 1 and 2 to strictly use closed candles
        df['EMA_Fast_t1'] = df['EMA_Fast'].shift(1)
        df['EMA_Slow_t1'] = df['EMA_Slow'].shift(1)
        
        df['EMA_Fast_t2'] = df['EMA_Fast'].shift(2)
        df['EMA_Slow_t2'] = df['EMA_Slow'].shift(2)
        
        df['Signal'] = 0
        df['Trend'] = np.where(df['EMA_Fast'] > df['EMA_Slow'], 1, -1)
        
        # Buy/Sell Conditions
        bullish_cond = (df['EMA_Fast_t2'] <= df['EMA_Slow_t2']) & (df['EMA_Fast_t1'] > df['EMA_Slow_t1'])
        bearish_cond = (df['EMA_Fast_t2'] >= df['EMA_Slow_t2']) & (df['EMA_Fast_t1'] < df['EMA_Slow_t1'])
        
        df.loc[bullish_cond, 'Signal'] = 2
        df.loc[bearish_cond, 'Signal'] = -2
        
        # Clean up columns
        df.drop(columns=['EMA_Fast_t1', 'EMA_Slow_t1', 'EMA_Fast_t2', 'EMA_Slow_t2'], inplace=True, errors='ignore')
        
    return df

def check_rules(df, max_signals=7):
    signals = []
    if df is not None and not df.empty:
        temp_df = df.dropna(subset=['EMA_Fast', 'EMA_Slow', 'Signal'])
        # Filter only valid crossovers
        signal_rows = temp_df[temp_df['Signal'].isin([2, -2])].tail(max_signals)
        
        for index, row in signal_rows.iterrows():
            sig_type = "Bullish Crossover 🟢" if row['Signal'] == 2 else "Bearish Crossover 🔴"
            close_col = 'Close' if 'Close' in row else 'close' if 'close' in row else df.columns[0]
            try: 
                formatted_time = pd.to_datetime(index).strftime('%Y-%m-%d %H:%M')
            except: 
                formatted_time = str(index)
                
            signals.append({
                "rule_no": "EMA Crossover",
                "signal": sig_type,
                "close": row[close_col],
                "time": formatted_time
            })
    return signals[::-1]
