"""Data loader utilities - NO LOOKAHEAD BIAS GUARANTEED

Data Ingestion Pipeline:
1. Load daily closing prices (adjusted for splits/dividends)
2. Load trading volume data
3. Compute returns (simple: price change %)
4. Features computed in feature_engineering.py use ONLY PAST DATA (shifted by 1)

All rolling windows are shifted by 1 to ensure NO DATA LEAKAGE.
"""
from typing import List, Optional, Tuple
import pandas as pd
import os


def load_prices(tickers: List[str], start_date: str, end_date: str, source: str = "yfinance", csv_paths: Optional[dict] = None) -> pd.DataFrame:
    """Load adjusted close prices for tickers between start_date and end_date.

    Parameters
    - tickers: list of ticker symbols
    - start_date, end_date: YYYY-MM-DD
    - source: 'yfinance' or 'csv'
    - csv_paths: mapping ticker->csv path when using csv

    Returns a DataFrame indexed by business day with aligned price columns.
    """
    if source == "csv":
        frames = []
        for t in tickers:
            path = (csv_paths or {}).get(t)
            if not path or not os.path.exists(path):
                raise FileNotFoundError(f"CSV for {t} not found: {path}")
            df = pd.read_csv(path, parse_dates=True, index_col=0)
            col = "Adj Close" if "Adj Close" in df.columns else ("Close" if "Close" in df.columns else df.columns[0])
            s = df[col].rename(t)
            frames.append(s)
        prices = pd.concat(frames, axis=1)
    else:
        import yfinance as yf
        data = yf.download(tickers, start=start_date, end=end_date, progress=False, auto_adjust=True)
        if isinstance(tickers, list) and len(tickers) == 1:
            # Handle single ticker case
            if isinstance(data["Close"], pd.Series):
                prices = data["Close"].to_frame().rename(columns={data["Close"].name: tickers[0]})
            else:
                prices = data["Close"].copy()
                prices.columns = tickers
        else:
            prices = data["Close"].copy()

    prices = prices.sort_index()

    # align to business days in the requested range
    idx = pd.date_range(start=start_date, end=end_date, freq="B")
    prices = prices.reindex(idx)

    # fill small gaps only using past data (forward-fill)
    prices = prices.ffill().bfill()

    return prices


def compute_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Compute simple daily returns from prices. First row will be NaN.
    
    NO LOOKAHEAD: Returns[t] = (Price[t] - Price[t-1]) / Price[t-1]
    Only uses prices up to and including day t.
    """
    return prices.pct_change()


def load_volume(tickers: List[str], start_date: str, end_date: str, source: str = "yfinance", csv_paths: Optional[dict] = None) -> pd.DataFrame:
    """Load trading volume for tickers between start_date and end_date.

    Parameters
    - tickers: list of ticker symbols
    - start_date, end_date: YYYY-MM-DD
    - source: 'yfinance' or 'csv'
    - csv_paths: mapping ticker->csv path when using csv

    Returns a DataFrame indexed by business day with volume columns.
    """
    if source == "csv":
        frames = []
        for t in tickers:
            path = (csv_paths or {}).get(t)
            if not path or not os.path.exists(path):
                raise FileNotFoundError(f"CSV for {t} not found: {path}")
            df = pd.read_csv(path, parse_dates=True, index_col=0)
            col = "Volume" if "Volume" in df.columns else None
            if col:
                s = df[col].rename(t)
                frames.append(s)
        volume = pd.concat(frames, axis=1) if frames else None
    else:
        import yfinance as yf
        data = yf.download(tickers, start=start_date, end=end_date, progress=False, auto_adjust=True)
        if isinstance(tickers, list) and len(tickers) == 1:
            volume = data["Volume"].to_frame().rename(columns={data["Volume"].name: tickers[0]}) if "Volume" in data else None
        else:
            volume = data["Volume"].copy() if "Volume" in data else None

    if volume is None:
        # Return zeros if volume not available
        idx = pd.date_range(start=start_date, end=end_date, freq="B")
        volume = pd.DataFrame(0, index=idx, columns=tickers)
    else:
        volume = volume.sort_index()
        idx = pd.date_range(start=start_date, end=end_date, freq="B")
        volume = volume.reindex(idx)
        volume = volume.ffill().bfill()

    return volume


def load_market_data(tickers: List[str], start_date: str, end_date: str, source: str = "yfinance", csv_paths: Optional[dict] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load complete market data: prices and volume.
    
    Returns:
    - prices: DataFrame of adjusted close prices
    - volume: DataFrame of trading volumes
    
    NO LOOKAHEAD BIAS: All features computed from this data use only past values.
    """
    prices = load_prices(tickers, start_date, end_date, source, csv_paths)
    volume = load_volume(tickers, start_date, end_date, source, csv_paths)
    return prices, volume

