"""Feature engineering utilities.

Compute rolling volatility, returns, moving averages, drawdown and correlations.
All rolling features use only past data (no lookahead) by shifting the rolling window.
"""
from typing import Tuple, Dict
import pandas as pd
import numpy as np


def rolling_features(prices: pd.DataFrame, vol_window: int = 30, ma_short: int = 50, ma_long: int = 200) -> Tuple[pd.DataFrame, Dict]:
    """Return (features_df, correlations_dict)

    features_df contains columns per asset with MultiIndex: (feature_name, ticker)
    correlations_dict is a simple dict storing rolling correlations per date
    
    Features computed:
    - vol_30: 30-day rolling volatility (based on past data only)
    - ret_30: 30-day cumulative return (based on past data only)
    - ma50, ma200: moving averages (based on past data only)
    - drawdown: rolling drawdown from peak
    """
    returns = prices.pct_change()

    # Rolling volatility - use past data only (shift by 1)
    vol_rolling = returns.rolling(window=vol_window, min_periods=5).std().shift(1)

    # Rolling returns - cumulative over vol_window days
    ret_rolling = (1 + returns).rolling(window=vol_window, min_periods=5).apply(lambda x: np.prod(x) - 1, raw=False).shift(1)

    # Moving averages - use past data only
    ma_short_val = prices.rolling(window=ma_short, min_periods=10).mean().shift(1)
    ma_long_val = prices.rolling(window=ma_long, min_periods=50).mean().shift(1)

    # Rolling drawdown from cumulative maximum
    rolling_max = prices.rolling(window=vol_window, min_periods=5).max().shift(1)
    drawdown_val = (prices / rolling_max - 1).fillna(0)

    # Aggregate into MultiIndex DataFrame
    feat_dict = {}
    for ticker in prices.columns:
        feat_dict[("vol_30", ticker)] = vol_rolling[ticker]
        feat_dict[("ret_30", ticker)] = ret_rolling[ticker]
        feat_dict[("ma50", ticker)] = ma_short_val[ticker]
        feat_dict[("ma200", ticker)] = ma_long_val[ticker]
        feat_dict[("drawdown", ticker)] = drawdown_val[ticker]

    features_df = pd.concat(feat_dict, axis=1)
    features_df = features_df.fillna(0)

    # Compute rolling correlations per date
    correlations = {}
    for date in returns.index:
        if date in returns.index:
            idx = returns.index.get_loc(date)
            if idx >= vol_window:
                past_returns = returns.iloc[idx-vol_window:idx]
                corr_matrix = past_returns.corr()
                correlations[str(date)] = corr_matrix.values.tolist()
            else:
                correlations[str(date)] = np.identity(len(prices.columns)).tolist()
        else:
            correlations[str(date)] = np.identity(len(prices.columns)).tolist()

    return features_df, correlations
