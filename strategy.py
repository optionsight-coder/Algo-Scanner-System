import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def create_line_break_with_emas(df, line_break_df, fast_ema=21, slow_ema=44):
    """
    Line Break chart with EMAs plotted on it
    """
    if df is None or line_break_df is None:
        return None
    
    # ========== 1. LINE BREAK CHART BANAYEIN ==========
    # Line break blocks ka OHLC data
    lb_ohlc = line_break_df.copy()
    
    # ========== 2. EMAs CALCULATE KAREIN (Sahi tareeke se) ==========
    # Method 1: Original data pe EMAs calculate karein, phir line break points pe map karein
    close_col = 'Close' if 'Close' in df.columns else 'close' if 'close' in df.columns else None
    if not close_col:
        return None
    
    # Original data pe EMAs
    df['EMA_Fast'] = df[close_col].ewm(span=fast_ema, adjust=False).mean()
    df['EMA_Slow'] = df[close_col].ewm(span=slow_ema, adjust=False).mean()
    
    # ========== 3. EMAs ko Line Break points pe map karein ==========
    ema_fast_values = []
    ema_slow_values = []
    lb_dates = []
    
    for idx, row in line_break_df.iterrows():
        # Us line break block ke corresponding original data points
        if idx in df.index:
            # Direct match
            ema_fast_values.append(df.loc[idx, 'EMA_Fast'])
            ema_slow_values.append(df.loc[idx, 'EMA_Slow'])
            lb_dates.append(idx)
        else:
            # Find nearest valid date in original data
            # Line break date se pehle ka last valid EMA value
            try:
                prev_data = df[df.index <= idx]
                if not prev_data.empty:
                    ema_fast_values.append(prev_data.iloc[-1]['EMA_Fast'])
                    ema_slow_values.append(prev_data.iloc[-1]['EMA_Slow'])
                    lb_dates.append(idx)
                else:
                    # Agar koi match nahi milta toh forward fill
                    next_data = df[df.index >= idx]
                    if not next_data.empty:
                        ema_fast_values.append(next_data.iloc[0]['EMA_Fast'])
                        ema_slow_values.append(next_data.iloc[0]['EMA_Slow'])
                        lb_dates.append(idx)
                    else:
                        ema_fast_values.append(np.nan)
                        ema_slow_values.append(np.nan)
                        lb_dates.append(idx)
            except:
                ema_fast_values.append(np.nan)
                ema_slow_values.append(np.nan)
                lb_dates.append(idx)
    
    # Line break DataFrame mein EMAs add karein
    line_break_df['EMA_Fast'] = ema_fast_values
    line_break_df['EMA_Slow'] = ema_slow_values
    
    # ========== 4. CROSSOVER SIGNALS GENERATE KAREIN ==========
    line_break_df['Crossover'] = 0
    
    # Bullish Crossover: Fast EMA crosses above Slow EMA
    for i in range(1, len(line_break_df)):
        if (line_break_df.iloc[i-1]['EMA_Fast'] <= line_break_df.iloc[i-1]['EMA_Slow'] and 
            line_break_df.iloc[i]['EMA_Fast'] > line_break_df.iloc[i]['EMA_Slow']):
            line_break_df.loc[line_break_df.index[i], 'Crossover'] = 1  # Bullish
            
        # Bearish Crossover: Fast EMA crosses below Slow EMA
        elif (line_break_df.iloc[i-1]['EMA_Fast'] >= line_break_df.iloc[i-1]['EMA_Slow'] and 
              line_break_df.iloc[i]['EMA_Fast'] < line_break_df.iloc[i]['EMA_Slow']):
            line_break_df.loc[line_break_df.index[i], 'Crossover'] = -1  # Bearish
    
    return line_break_df


def visualize_line_break_with_emas(line_break_df, title="3-Line Break Chart with EMAs"):
    """
    Line Break chart ko EMAs ke saath visualize karein
    """
    if line_break_df is None or line_break_df.empty:
        return
    
    # Candlestick chart banayein
    fig = go.Figure(data=[
        go.Candlestick(
            x=line_break_df.index,
            open=line_break_df['Open'],
            high=line_break_df['High'],
            low=line_break_df['Low'],
            close=line_break_df['Close'],
            name='Line Break'
        ),
        # Fast EMA
        go.Scatter(
            x=line_break_df.index,
            y=line_break_df['EMA_Fast'],
            name=f'EMA {fast_ema}',
            line=dict(color='blue', width=2)
        ),
        # Slow EMA
        go.Scatter(
            x=line_break_df.index,
            y=line_break_df['EMA_Slow'],
            name=f'EMA {slow_ema}',
            line=dict(color='red', width=2)
        )
    ])
    
    # Crossover signals add karein
    bullish_signals = line_break_df[line_break_df['Crossover'] == 1]
    bearish_signals = line_break_df[line_break_df['Crossover'] == -1]
    
    # Bullish signals (green triangles pointing up)
    fig.add_trace(go.Scatter(
        x=bullish_signals.index,
        y=bullish_signals['Low'] * 0.99,  # Slightly below the candle
        mode='markers',
        marker=dict(symbol='triangle-up', size=15, color='green'),
        name='Bullish Crossover'
    ))
    
    # Bearish signals (red triangles pointing down)
    fig.add_trace(go.Scatter(
        x=bearish_signals.index,
        y=bearish_signals['High'] * 1.01,  # Slightly above the candle
        mode='markers',
        marker=dict(symbol='triangle-down', size=15, color='red'),
        name='Bearish Crossover'
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title='Date/Time',
        yaxis_title='Price',
        template='plotly_dark',
        height=600
    )
    
    fig.show()


def get_accurate_signals(line_break_df, max_signals=7):
    """
    Accurate signals extract karein
    """
    signals = []
    
    # Sirf crossover points
    crossovers = line_break_df[line_break_df['Crossover'] != 0]
    
    for idx, row in crossovers.iterrows():
        if row['Crossover'] == 1:
            sig_type = "Bullish Crossover 🟢"
        else:
            sig_type = "Bearish Crossover 🔴"
        
        signals.append({
            "signal": sig_type,
            "close": row['Close'],
            "time": str(idx),
            "fast_ema": row['EMA_Fast'],
            "slow_ema": row['EMA_Slow']
        })
    
    return signals[-max_signals:][::-1]  # Latest signals first


# ========== COMPLETE USAGE EXAMPLE ==========

# Step 1: Load original data
df = pd.read_csv('your_data.csv', index_col='Date', parse_dates=True)
# Ensure columns: ['Open', 'High', 'Low', 'Close']

# Step 2: Convert to 3-line break
line_break_df = convert_to_3_line_break(df)  # Your existing function

# Step 3: Line Break chart pe EMAs plot karein
result_df = create_line_break_with_emas(df, line_break_df, fast_ema=21, slow_ema=44)

# Step 4: Visualize
visualize_line_break_with_emas(result_df)

# Step 5: Extract signals
signals = get_accurate_signals(result_df, max_signals=7)

# Print signals with details
print("\n=== LATEST SIGNALS ===")
for sig in signals:
    print(f"Time: {sig['time']}")
    print(f"Signal: {sig['signal']}")
    print(f"Price: {sig['close']:.2f}")
    print(f"Fast EMA: {sig['fast_ema']:.2f}, Slow EMA: {sig['slow_ema']:.2f}")
    print("-" * 40)


# ========== ALTERNATIVE METHOD: Resample to Regular Intervals ==========

def create_resampled_line_break_with_emas(df, interval='1min'):
    """
    Regular interval pe line break + EMAs
    """
    # Pehle line break banayein
    line_break_df = convert_to_3_line_break(df)
    
    # Regular interval pe resample karein
    resampled_lb = line_break_df.resample(interval).agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last'
    }).dropna()
    
    # Ab EMAs calculate karein is regular data pe
    resampled_lb['EMA_Fast'] = resampled_lb['Close'].ewm(span=21, adjust=False).mean()
    resampled_lb['EMA_Slow'] = resampled_lb['Close'].ewm(span=44, adjust=False).mean()
    
    # Crossover signals
    resampled_lb['Crossover'] = 0
    for i in range(1, len(resampled_lb)):
        if (resampled_lb.iloc[i-1]['EMA_Fast'] <= resampled_lb.iloc[i-1]['EMA_Slow'] and 
            resampled_lb.iloc[i]['EMA_Fast'] > resampled_lb.iloc[i]['EMA_Slow']):
            resampled_lb.iloc[i, resampled_lb.columns.get_loc('Crossover')] = 1
        elif (resampled_lb.iloc[i-1]['EMA_Fast'] >= resampled_lb.iloc[i-1]['EMA_Slow'] and 
              resampled_lb.iloc[i]['EMA_Fast'] < resampled_lb.iloc[i]['EMA_Slow']):
            resampled_lb.iloc[i, resampled_lb.columns.get_loc('Crossover')] = -1
    
    return resampled_lb
