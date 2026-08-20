import pandas as pd
import numpy as np
from datetime import timedelta

def convert_to_3_line_break_with_time(df):
    """
    3-Line Break chart with proper time tracking
    """
    if df is None or df.empty:
        return df
    
    close_col = 'Close' if 'Close' in df.columns else 'close' if 'close' in df.columns else None
    high_col = 'High' if 'High' in df.columns else 'high' if 'high' in df.columns else None
    low_col = 'Low' if 'Low' in df.columns else 'low' if 'low' in df.columns else None
    
    if not close_col:
        return df
    
    df = df.copy()
    df[close_col] = pd.to_numeric(df[close_col], errors='coerce')
    
    blocks = []
    block_start_time = df.index[0]
    block_end_time = df.index[0]
    
    # FIRST BLOCK
    first_price = df[close_col].iloc[0]
    start_idx = 1
    
    for i in range(1, len(df)):
        if not pd.isna(df[close_col].iloc[i]) and df[close_col].iloc[i] != first_price:
            current_price = df[close_col].iloc[i]
            
            if current_price > first_price:
                blocks.append({
                    'open': first_price,
                    'high': df[high_col].iloc[:i+1].max() if high_col else current_price,
                    'low': df[low_col].iloc[:i+1].min() if low_col else first_price,
                    'close': current_price,
                    'trend': 1,
                    'start_time': df.index[0],
                    'end_time': df.index[i],
                    'duration': df.index[i] - df.index[0]
                })
            else:
                blocks.append({
                    'open': first_price,
                    'high': df[high_col].iloc[:i+1].max() if high_col else first_price,
                    'low': df[low_col].iloc[:i+1].min() if low_col else current_price,
                    'close': current_price,
                    'trend': -1,
                    'start_time': df.index[0],
                    'end_time': df.index[i],
                    'duration': df.index[i] - df.index[0]
                })
            start_idx = i + 1
            break
    
    if not blocks:
        return df
    
    # MAIN 3-LINE BREAK LOGIC
    for i in range(start_idx, len(df)):
        current_close = df[close_col].iloc[i]
        current_high = df[high_col].iloc[i] if high_col else current_close
        current_low = df[low_col].iloc[i] if low_col else current_close
        current_time = df.index[i]
        
        if pd.isna(current_close):
            continue
        
        last_block = blocks[-1]
        last_3_blocks = blocks[-3:] if len(blocks) >= 3 else blocks
        
        if last_block['trend'] == 1:
            if current_high > last_block['high']:
                # Continuation UP
                blocks.append({
                    'open': last_block['close'],
                    'high': current_high,
                    'low': last_block['low'],
                    'close': current_close,
                    'trend': 1,
                    'start_time': last_block['end_time'],
                    'end_time': current_time,
                    'duration': current_time - last_block['end_time']
                })
            else:
                reversal_price = min([block['low'] for block in last_3_blocks])
                if current_low < reversal_price:
                    # Reversal DOWN
                    blocks.append({
                        'open': last_block['close'],
                        'high': last_block['high'],
                        'low': current_low,
                        'close': current_close,
                        'trend': -1,
                        'start_time': last_block['end_time'],
                        'end_time': current_time,
                        'duration': current_time - last_block['end_time']
                    })
                else:
                    # Extend current block
                    blocks[-1]['high'] = max(blocks[-1]['high'], current_high)
                    blocks[-1]['low'] = min(blocks[-1]['low'], current_low)
                    blocks[-1]['close'] = current_close
                    blocks[-1]['end_time'] = current_time
                    blocks[-1]['duration'] = current_time - blocks[-1]['start_time']
                    
        elif last_block['trend'] == -1:
            if current_low < last_block['low']:
                # Continuation DOWN
                blocks.append({
                    'open': last_block['close'],
                    'high': last_block['high'],
                    'low': current_low,
                    'close': current_close,
                    'trend': -1,
                    'start_time': last_block['end_time'],
                    'end_time': current_time,
                    'duration': current_time - last_block['end_time']
                })
            else:
                reversal_price = max([block['high'] for block in last_3_blocks])
                if current_high > reversal_price:
                    # Reversal UP
                    blocks.append({
                        'open': last_block['close'],
                        'high': current_high,
                        'low': last_block['low'],
                        'close': current_close,
                        'trend': 1,
                        'start_time': last_block['end_time'],
                        'end_time': current_time,
                        'duration': current_time - last_block['end_time']
                    })
                else:
                    # Extend current block
                    blocks[-1]['high'] = max(blocks[-1]['high'], current_high)
                    blocks[-1]['low'] = min(blocks[-1]['low'], current_low)
                    blocks[-1]['close'] = current_close
                    blocks[-1]['end_time'] = current_time
                    blocks[-1]['duration'] = current_time - blocks[-1]['start_time']
    
    # Create DataFrame with proper time tracking
    lb_data = []
    for block in blocks:
        lb_data.append({
            'Open': block['open'],
            'High': block['high'],
            'Low': block['low'],
            'Close': block['close'],
            'Trend': block['trend'],
            'Start_Time': block['start_time'],
            'End_Time': block['end_time'],
            'Duration': block['duration']
        })
    
    lb_df = pd.DataFrame(lb_data)
    lb_df.set_index('End_Time', inplace=True)
    
    return lb_df


def calculate_emas_on_original_data(df, fast_ema=21, slow_ema=44):
    """
    Original data pe EMAs calculate karein
    """
    close_col = 'Close' if 'Close' in df.columns else 'close' if 'close' in df.columns else None
    if not close_col:
        return None
    
    df = df.copy()
    
    # EMAs on original data (hourly/daily)
    df['EMA_Fast'] = df[close_col].ewm(span=fast_ema, adjust=False).mean()
    df['EMA_Slow'] = df[close_col].ewm(span=slow_ema, adjust=False).mean()
    
    return df


def map_emas_to_line_break(lb_df, df_with_emas):
    """
    EMAs ko line break chart pe map karein (exact time matching)
    """
    if lb_df is None or df_with_emas is None:
        return None
    
    lb_df = lb_df.copy()
    
    # Create DateTimeIndex for faster lookup
    ema_df = df_with_emas[['EMA_Fast', 'EMA_Slow']].copy()
    
    # For each line break block, find the EMA value at its end time
    ema_fast_values = []
    ema_slow_values = []
    
    for idx in lb_df.index:
        # Try exact match first
        if idx in ema_df.index:
            ema_fast_values.append(ema_df.loc[idx, 'EMA_Fast'])
            ema_slow_values.append(ema_df.loc[idx, 'EMA_Slow'])
        else:
            # Find the nearest time in original data (before or at block end)
            # This is the KEY FIX - use asof for nearest value
            try:
                # Get the closest index that is <= block end time
                closest_idx = ema_df.index.asof(idx)
                if pd.notna(closest_idx):
                    ema_fast_values.append(ema_df.loc[closest_idx, 'EMA_Fast'])
                    ema_slow_values.append(ema_df.loc[closest_idx, 'EMA_Slow'])
                else:
                    ema_fast_values.append(np.nan)
                    ema_slow_values.append(np.nan)
            except:
                ema_fast_values.append(np.nan)
                ema_slow_values.append(np.nan)
    
    lb_df['EMA_Fast'] = ema_fast_values
    lb_df['EMA_Slow'] = ema_slow_values
    
    # Forward fill any NaN values
    lb_df['EMA_Fast'] = lb_df['EMA_Fast'].fillna(method='ffill')
    lb_df['EMA_Slow'] = lb_df['EMA_Slow'].fillna(method='ffill')
    
    return lb_df


def generate_crossover_signals(lb_df):
    """
    Crossover signals generate karein
    """
    if lb_df is None or lb_df.empty:
        return lb_df
    
    lb_df = lb_df.copy()
    
    # Calculate crossover signals
    lb_df['Crossover'] = 0
    
    for i in range(1, len(lb_df)):
        # Bullish crossover: Fast EMA crosses above Slow EMA
        if (lb_df.iloc[i-1]['EMA_Fast'] <= lb_df.iloc[i-1]['EMA_Slow'] and 
            lb_df.iloc[i]['EMA_Fast'] > lb_df.iloc[i]['EMA_Slow']):
            lb_df.iloc[i, lb_df.columns.get_loc('Crossover')] = 1
        
        # Bearish crossover: Fast EMA crosses below Slow EMA
        elif (lb_df.iloc[i-1]['EMA_Fast'] >= lb_df.iloc[i-1]['EMA_Slow'] and 
              lb_df.iloc[i]['EMA_Fast'] < lb_df.iloc[i]['EMA_Slow']):
            lb_df.iloc[i, lb_df.columns.get_loc('Crossover')] = -1
    
    return lb_df


def get_signals_with_context(lb_df, max_signals=7):
    """
    Context ke saath signals extract karein
    """
    signals = []
    
    crossovers = lb_df[lb_df['Crossover'] != 0]
    
    for idx, row in crossovers.tail(max_signals).iterrows():
        if row['Crossover'] == 1:
            sig_type = "BUY - Bullish Crossover 🟢"
            ema_diff = row['EMA_Fast'] - row['EMA_Slow']
        else:
            sig_type = "SELL - Bearish Crossover 🔴"
            ema_diff = row['EMA_Fast'] - row['EMA_Slow']
        
        signals.append({
            "signal": sig_type,
            "price": row['Close'],
            "time": idx,
            "fast_ema": round(row['EMA_Fast'], 2),
            "slow_ema": round(row['EMA_Slow'], 2),
            "ema_diff": round(ema_diff, 2),
            "trend": "UP" if row['Trend'] == 1 else "DOWN"
        })
    
    return signals[::-1]  # Oldest to newest


# ========== COMPLETE USAGE ==========

def complete_strategy(df, fast_ema=21, slow_ema=44):
    """
    Complete strategy execution
    """
    print("📊 Step 1: Creating 3-Line Break Chart...")
    lb_df = convert_to_3_line_break_with_time(df)
    print(f"✅ Line Break Blocks: {len(lb_df)}")
    
    print("\n📊 Step 2: Calculating EMAs on original data...")
    df_with_emas = calculate_emas_on_original_data(df, fast_ema, slow_ema)
    print(f"✅ EMAs calculated on {len(df_with_emas)} data points")
    
    print("\n📊 Step 3: Mapping EMAs to Line Break chart...")
    lb_df_with_emas = map_emas_to_line_break(lb_df, df_with_emas)
    print(f"✅ EMAs mapped to {len(lb_df_with_emas)} line break blocks")
    
    print("\n📊 Step 4: Generating crossover signals...")
    lb_df_with_signals = generate_crossover_signals(lb_df_with_emas)
    
    print("\n📊 Step 5: Extracting signals...")
    signals = get_signals_with_context(lb_df_with_signals)
    
    return lb_df_with_signals, signals


# ========== EXECUTION ==========

# Load your data
df = pd.read_csv('your_data.csv', index_col='Date', parse_dates=True)

# Run the complete strategy
lb_df_final, signals = complete_strategy(df, fast_ema=21, slow_ema=44)

# Print signals
print("\n" + "="*60)
print("📈 LATEST SIGNALS")
print("="*60)

for sig in signals:
    print(f"\n⏰ Time: {sig['time']}")
    print(f"📊 Signal: {sig['signal']}")
    print(f"💰 Price: {sig['price']:.2f}")
    print(f"📈 Fast EMA: {sig['fast_ema']}, Slow EMA: {sig['slow_ema']}")
    print(f"📉 EMA Difference: {sig['ema_diff']}")
    print(f"📊 Line Break Trend: {sig['trend']}")
    print("-"*40)

# Optional: Save to CSV for analysis
lb_df_final.to_csv('line_break_with_emas.csv')
print("\n✅ Data saved to 'line_break_with_emas.csv'")
