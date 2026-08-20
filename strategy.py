import pandas as pd
import pandas_ta as ta
import numpy as np

def convert_to_3_line_break(df):
    """
    Dummy function: Kyunki ab hum regular candlesticks use kar rahe hain,
    ye function data ko bina change kiye aage bhej dega taaki app.py crash na ho.
    """
    return df

def calculate_indicators(df, fast_ema=21, slow_ema=44):
    """
    Regular Candlesticks par EMA aur Trend calculate karta hai.
    """
    if df is None or df.empty:
        return df
        
    # Close column ko dhundhna aur format karna
    close_col = 'Close' if 'Close' in df.columns else 'close'
    if close_col not in df.columns:
        return df
        
    df = df.copy()
    df[close_col] = pd.to_numeric(df[close_col], errors='coerce')
    
    # 1. EMA Calculation
    df['EMA_Fast'] = ta.ema(df[close_col], length=fast_ema)
    df['EMA_Slow'] = ta.ema(df[close_col], length=slow_ema)
    
    # 2. Repainting Protection (Pichli 2 closed candles ka data)
    df['EMA_Fast_t1'] = df['EMA_Fast'].shift(1)
    df['EMA_Slow_t1'] = df['EMA_Slow'].shift(1)
    
    df['EMA_Fast_t2'] = df['EMA_Fast'].shift(2)
    df['EMA_Slow_t2'] = df['EMA_Slow'].shift(2)
    
    # Default columns setup
    df['Signal'] = 0
    df['Trend'] = np.where(df['EMA_Fast'] > df['EMA_Slow'], 1, -1)
    
    # 3. Exact Crossover Logic (Only on closed candles)
    bullish_cond = (df['EMA_Fast_t2'] <= df['EMA_Slow_t2']) & (df['EMA_Fast_t1'] > df['EMA_Slow_t1'])
    bearish_cond = (df['EMA_Fast_t2'] >= df['EMA_Slow_t2']) & (df['EMA_Fast_t1'] < df['EMA_Slow_t1'])
    
    df.loc[bullish_cond, 'Signal'] = 2
    df.loc[bearish_cond, 'Signal'] = -2
    
    # Memory clean up (temporary columns hatana)
    df.drop(columns=['EMA_Fast_t1', 'EMA_Slow_t1', 'EMA_Fast_t2', 'EMA_Slow_t2'], inplace=True, errors='ignore')
    
    return df

def check_rules(df, max_signals=7):
    """
    Crossovers ko check karke dashboard ke liye final signals banata hai.
    """
    signals = []
    if df is None or df.empty:
        return signals
        
    # Sirf un rows ko filter karna jahan signal 2 (Buy) ya -2 (Sell) ho
    temp_df = df.dropna(subset=['EMA_Fast', 'EMA_Slow', 'Signal'])
    signal_rows = temp_df[temp_df['Signal'].isin([2, -2])].tail(max_signals)
    
    for index, row in signal_rows.iterrows():
        sig_type = "Bullish Crossover 🟢" if row['Signal'] == 2 else "Bearish Crossover 🔴"
        close_col = 'Close' if 'Close' in row else 'close'
        
        # Time formatting
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
        
    # Naye signals upar dikhane ke liye reverse order
    return signals[::-1]
