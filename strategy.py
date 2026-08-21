import pandas as pd
import pandas_ta as ta
import numpy as np

def convert_to_3_line_break(df, num_lines=3):
    if df is None or df.empty: return df
    
    close_col = 'Close' if 'Close' in df.columns else 'close' if 'close' in df.columns else None
    open_col = 'Open' if 'Open' in df.columns else 'open' if 'open' in df.columns else None
    
    if not close_col or not open_col: return df
        
    df = df.copy()
    lines = [] 
    
    first_close = df[close_col].iloc[0]
    first_open = df[open_col].iloc[0]
    initial_color = 'green' if first_close >= first_open else 'red'

    lines.append({
        'open': first_open, 'close': first_close,
        'high': max(first_open, first_close), 'low': min(first_open, first_close),
        'color': initial_color, 'date': df.index[0] 
    })

    for i in range(1, len(df)):
        current_close = df[close_col].iloc[i]
        current_date = df.index[i]
        
        if pd.isna(current_close): continue
            
        recent_lines = lines[-num_lines:]
        highest_extreme = max(l['high'] for l in recent_lines)
        lowest_extreme = min(l['low'] for l in recent_lines)
        last_line = lines[-1]

        if last_line['color'] == 'green':
            if current_close > last_line['high']:
                lines.append({'open': last_line['close'], 'close': current_close, 'high': current_close, 'low': last_line['close'], 'color': 'green', 'date': current_date})
            elif current_close < lowest_extreme:
                lines.append({'open': last_line['close'], 'close': current_close, 'high': last_line['close'], 'low': current_close, 'color': 'red', 'date': current_date})
        else:  
            if current_close < last_line['low']:
                lines.append({'open': last_line['close'], 'close': current_close, 'high': last_line['close'], 'low': current_close, 'color': 'red', 'date': current_date})
            elif current_close > highest_extreme:
                lines.append({'open': last_line['close'], 'close': current_close, 'high': current_close, 'low': last_line['close'], 'color': 'green', 'date': current_date})

    lb_df = pd.DataFrame(lines)
    lb_df.set_index('date', inplace=True)
    lb_df.rename(columns={'close': 'Close'}, inplace=True)
    
    return lb_df

def calculate_indicators(df, fast_ema=21, slow_ema=44):
    if df is None or df.empty: return df
        
    df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    
    df['EMA_Fast'] = ta.ema(df['Close'], length=fast_ema)
    df['EMA_Slow'] = ta.ema(df['Close'], length=slow_ema)
    
    df['EMA_Fast_prev'] = df['EMA_Fast'].shift(1)
    df['EMA_Slow_prev'] = df['EMA_Slow'].shift(1)
    
    df['Signal'] = 0
    df['Trend'] = np.where(df['EMA_Fast'] > df['EMA_Slow'], 1, -1)
    
    bullish_cond = (df['EMA_Fast_prev'] <= df['EMA_Slow_prev']) & (df['EMA_Fast'] > df['EMA_Slow'])
    bearish_cond = (df['EMA_Fast_prev'] >= df['EMA_Slow_prev']) & (df['EMA_Fast'] < df['EMA_Slow'])
    
    df.loc[bullish_cond, 'Signal'] = 2
    df.loc[bearish_cond, 'Signal'] = -2
    
    df.drop(columns=['EMA_Fast_prev', 'EMA_Slow_prev'], inplace=True, errors='ignore')
    
    return df

def check_rules(df, max_signals=6):
    signals = []
    if df is None or df.empty: return signals
        
    temp_df = df.dropna(subset=['EMA_Fast', 'EMA_Slow', 'Signal'])
    signal_rows = temp_df[temp_df['Signal'].isin([2, -2])].tail(max_signals)
    
    for index, row in signal_rows.iterrows():
        sig_type = "Bullish Crossover 🟢" if row['Signal'] == 2 else "Bearish Crossover 🔴"
        close_col = 'Close' if 'Close' in row else 'close' 
        try: 
            formatted_time = pd.to_datetime(index).strftime('%Y-%m-%d %H:%M')
        except: 
            formatted_time = str(index)
            
        signals.append({"rule_no": "EMA Crossover (3LB)", "signal": sig_type, "close": row[close_col], "time": formatted_time})
        
    return signals[::-1]
