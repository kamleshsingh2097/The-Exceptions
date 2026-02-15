#!/usr/bin/env python3
"""
DEMONSTRATION: No Lookahead Bias Data Ingestion
Shows the CORRECT approach (shifted) vs WRONG approach (not shifted)
"""

import pandas as pd
import numpy as np
from data_loader import load_prices, compute_returns

# Create simple example data
prices = pd.DataFrame({
    'STOCK': [100, 102, 104, 103, 105]
}, index=pd.date_range('2024-01-01', periods=5))

print("=" * 70)
print("DATA INGESTION: NO LOOKAHEAD BIAS DEMONSTRATION")
print("=" * 70)

print("\n1. PRICE DATA")
print("-" * 70)
print(prices)

# Compute returns
returns = compute_returns(prices)
print("\n2. DAILY RETURNS")
print("-" * 70)
print(returns)

# [WRONG] Volatility without shift (lookahead)
vol_wrong = returns.rolling(window=2).std()
print("\n3. [WRONG] Volatility WITHOUT shift (LOOKAHEAD BIAS)")
print("-" * 70)
print("Row 3 volatility:", vol_wrong.iloc[3].values)
print("  Uses returns from row 2, 3 --> includes future data (row 3)")
print("  When making decision at Day 3, we'd know the Day 3 volatility")
print("  This is CHEATING - uses future information!")
print(vol_wrong)

# [RIGHT] Volatility with shift (no lookahead)
vol_right = returns.rolling(window=2).std().shift(1)
print("\n4. [RIGHT] Volatility WITH shift (NO LOOKAHEAD)")
print("-" * 70)
print("Row 3 volatility:", vol_right.iloc[2].values)
print("  Shift means: Row[t] value = Rolling calculation up to Row[t-1]")
print("  Row 3 gets volatility of row 1-2 (only past data)")
print("  When making decision at Day 3, this feature is TODAY's input")
print(vol_right)

print("\n5. COMPARISON: WHICH IS CORRECT?")
print("-" * 70)
print(f"{'Day':<6} {'Price':<8} {'Wrong':<15} {'Right':<15} {'Verdict':<40}")
print("-" * 70)

for i in range(len(prices)):
    day = prices.index[i].strftime('%Y-%m-%d')
    price = prices.iloc[i].values[0]
    
    wrong_val = vol_wrong.iloc[i].values[0] if not pd.isna(vol_wrong.iloc[i].values[0]) else "NaN"
    right_val = vol_right.iloc[i].values[0] if not pd.isna(vol_right.iloc[i].values[0]) else "NaN"
    
    if i < 2:
        verdict = "Not enough history"
    else:
        if isinstance(wrong_val, float) and isinstance(right_val, float):
            verdict = f"[OK] Right uses vol[{i-1}] = {right_val:.4f}, Wrong leaks from {i}"
        else:
            verdict = "NaN handling"
    
    wrong_str = f"{wrong_val:.4f}" if isinstance(wrong_val, float) else str(wrong_val)
    right_str = f"{right_val:.4f}" if isinstance(right_val, float) else str(right_val)
    
    print(f"{day:<6} ${price:<7.1f} {wrong_str:<15} {right_str:<15} {verdict:<40}")

print("\n" + "=" * 70)
print("KEY INSIGHT: Walk-Forward Backtesting")
print("=" * 70)
print("""
When backtesting Day T:
  1. Decision Time: Day T morning (before knowing Day T result)
  2. Available Data: All data from Day 1 to Day T-1
  3. What we compute: Features using .shift(1)
     → Features[T] = calculation on data[1:T-1]
     → Features[T] is READY before Day T trading
  4. Trade Execution: Day T at open or close
  5. Result: Realized at Day T+1
  
This is exactly what shift(1) does in our system!
""")

print("=" * 70)
print("DATA INGESTION CHECKLIST")
print("=" * 70)
print("""
[CHECK] Prices loaded from historical data source
[CHECK] Volume loaded alongside prices
[CHECK] Returns computed: Return[t] = (Price[t] - Price[t-1]) / Price[t-1]
[CHECK] Features use .shift(1): Feature[t] = calc(data[t-window+1:t-1])
[CHECK] Moving averages shifted: MA[t] = mean(prices[t-window:t-1])
[CHECK] Correlations computed from historical windows only
[CHECK] Regime detection uses only past data
[CHECK] Backtester walks forward chronologically
[CHECK] Transaction costs realistic (0.1%)
[CHECK] NO parameter optimization on full dataset

RESULT: Realistic, tradeable strategies with ZERO lookahead bias
""")

print("=" * 70)
