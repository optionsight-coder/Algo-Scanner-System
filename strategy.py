import pandas as pd
import numpy as np

def convert_to_3_line_break(df):
    """
    Converts standard OHLCV dataframe to 3-Line Break blocks.
    """
    if df is None or len(df) == 0:
        return None

df.columns = df.columns.str.lower()
    if 'time' not in df.columns:
        if 'date' in df.columns:
            df = df.rename(columns={'date': 'time'})
        elif 'datetime' in df.columns:
            df = df.rename(columns={'datetime': 'time'})
        elif 'timestamp' in df.columns:
            df = df.rename(columns={'timestamp': 'time'})
    
        
    blocks = []
    # Initialize with the first candle
    blocks.append({
        'time': df.iloc[0]['time'],
        'open': df.iloc[0]['open'],
        'high': df.iloc[0]['high'],
        'low': df.iloc[0]['low'],
        'close': df.iloc[0]['close'],
        'trend': 1 if df.iloc[0]['close'] >= df.iloc[0]['open'] else -1
    })
    
    for i in range(1, len(df)):
        curr_price = df.iloc[i]['close']
        curr_time = df.iloc[i]['time']
        
        last_block = blocks[-1]
        
        # Determine current trend blocks
        trend = last_block['trend']
        
        if trend == 1: # Current trend is Up
            if curr_price > last_block['close']:
                # Continue Up
                blocks.append({'time': curr_time, 'open': last_block['close'], 'high': curr_price, 'low': last_block['close'], 'close': curr_price, 'trend': 1})
            else:
                # Check for reversal (needs to break lowest low of last 3 UP blocks)
                up_blocks = [b for b in blocks if b['trend'] == 1][-3:]
                if len(up_blocks) == 3:
                    reversal_price = min([b['open'] for b in up_blocks])
                    if curr_price < reversal_price:
                        # Reversal Down
                        blocks.append({'time': curr_time, 'open': last_block['close'], 'high': last_block['close'], 'low': curr_price, 'close': curr_price, 'trend': -1})
        
        elif trend == -1: # Current trend is Down
            if curr_price < last_block['close']:
                # Continue Down
                blocks.append({'time': curr_time, 'open': last_block['close'], 'high': last_block['close'], 'low': curr_price, 'close': curr_price, 'trend': -1})
            else:
                # Check for reversal (needs to break highest high of last 3 DOWN blocks)
                down_blocks = [b for b in blocks if b['trend'] == -1][-3:]
                if len(down_blocks) == 3:
                    reversal_price = max([b['open'] for b in down_blocks])
                    if curr_price > reversal_price:
                        # Reversal Up
                        blocks.append({'time': curr_time, 'open': last_block['close'], 'high': curr_price, 'low': last_block['close'], 'close': curr_price, 'trend': 1})
                        
    return pd.DataFrame(blocks)


def calculate_indicators(df, fast_ema=21, slow_ema=44, macd_fast=12, macd_slow=26, signal_period=9):
    """
    Calculates EMA, MACD, and new Video-based Filters (Contraction & Histogram Slope)
    """
    if df is None or len(df) < 50:
        return df

    # 1. --- EMA 21/44 ---
    df['ema_fast'] = df['close'].ewm(span=fast_ema, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=slow_ema, adjust=False).mean()
    df['ema_fast_prev'] = df['ema_fast'].shift(1)
    df['ema_slow_prev'] = df['ema_slow'].shift(1)
    
    # 🌟 NEW: EMA Gap Percentage (Contraction Filter)
    df['ema_gap_pct'] = (abs(df['ema_fast'] - df['ema_slow']) / df['ema_slow']) * 100

    # 2. --- MACD ---
    df['macd_ema_fast'] = df['close'].ewm(span=macd_fast, adjust=False).mean()
    df['macd_ema_slow'] = df['close'].ewm(span=macd_slow, adjust=False).mean()
    df['macd'] = df['macd_ema_fast'] - df['macd_ema_slow']
    
    df['macd_signal'] = df['macd'].ewm(span=signal_period, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    df['macd_prev'] = df['macd'].shift(1)
    df['macd_signal_prev'] = df['macd_signal'].shift(1)
    
    # 🌟 NEW: Histogram Slope Checker
    df['macd_hist_prev'] = df['macd_hist'].shift(1)
    
    # 🌟 NEW: Previous Block High/Low for Stoploss Calculation
    df['block_high'] = df[['open', 'close']].max(axis=1)
    df['block_low'] = df[['open', 'close']].min(axis=1)
    df['prev_block_high'] = df['block_high'].shift(1)
    df['prev_block_low'] = df['block_low'].shift(1)
    
    return df


def check_rules(df, max_signals=6, max_expansion_pct=1.0):
    """
    Checks logic and calculates 1:2 Risk-Reward Targets.
    """
    signals = []
    if df is None or len(df) < 2:
        return signals
        
    for i in range(len(df)-1, 0, -1):
        row = df.iloc[i]
        
        # --- FILTERS ---
        is_expanded = row['ema_gap_pct'] > max_expansion_pct
        gap_status = "⚠️ Expanded" if is_expanded else "✅ Contracted"
        
        hist_rising = row['macd_hist'] > row['macd_hist_prev']
        hist_falling = row['macd_hist'] < row['macd_hist_prev']

        # --- LOGIC ---
        ema_cross_above = (row['ema_fast'] > row['ema_slow']) and (row['ema_fast_prev'] <= row['ema_slow_prev'])
        ema_cross_below = (row['ema_fast'] < row['ema_slow']) and (row['ema_fast_prev'] >= row['ema_slow_prev'])
        
        macd_cross_above = (row['macd'] > row['macd_signal']) and (row['macd_prev'] <= row['macd_signal_prev'])
        macd_cross_below = (row['macd'] < row['macd_signal']) and (row['macd_prev'] >= row['macd_signal_prev'])
        
        detected_signals = []
        sl = 0
        target = 0
        
        # 🌟 Check combinations: Crossover MUST be supported by Histogram Slope
        if ema_cross_above and hist_rising: 
            detected_signals.append(f"🟢 Bullish (EMA) [{gap_status}]")
            sl = row['prev_block_low']
            target = row['close'] + ((row['close'] - sl) * 2) 
            
        if ema_cross_below and hist_falling: 
            detected_signals.append(f"🔴 Bearish (EMA) [{gap_status}]")
            sl = row['prev_block_high']
            target = row['close'] - ((sl - row['close']) * 2) 
            
        if macd_cross_above and hist_rising: 
            detected_signals.append(f"🟢 Bullish (MACD) [{gap_status}]")
            if sl == 0:
                sl = row['prev_block_low']
                target = row['close'] + ((row['close'] - sl) * 2)

        if macd_cross_below and hist_falling: 
            detected_signals.append(f"🔴 Bearish (MACD) [{gap_status}]")
            if sl == 0:
                sl = row['prev_block_high']
                target = row['close'] - ((sl - row['close']) * 2)

        for sig_type in detected_signals:
            final_signal_str = f"{sig_type} | SL: ₹{round(sl, 2)} | TGT: ₹{round(target, 2)}"
            
            signals.append({
                "time": row['time'],
                "close": row['close'],
                "signal": final_signal_str,
                "histogram_val": round(row['macd_hist'], 2)
            })
            
        if len(signals) >= max_signals:
            break
            
    return signals[:max_signals]
