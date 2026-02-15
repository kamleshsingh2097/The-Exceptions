import yfinance as yf
from datetime import datetime, timedelta
import sys
import os
import logging
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LOOKBACK_DAYS, TIMEFRAME

logger = logging.getLogger(__name__)

_data_cache = {}
CACHE_DURATION = 300

def _is_cache_valid(timestamp):
    """Check if cached data is still valid"""
    return (datetime.now() - timestamp).total_seconds() < CACHE_DURATION

def fetch(symbol: str, use_cache: bool = True) -> Optional[any]:
    """Fetch stock data from yfinance"""
    try:
        # Check cache
        if use_cache and symbol in _data_cache:
            df, timestamp = _data_cache[symbol]
            if _is_cache_valid(timestamp):
                logger.info(f"Using cached data for {symbol}")
                return df
        
        start = (datetime.now() - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
        df = yf.download(
            symbol, 
            interval=TIMEFRAME, 
            start=start, 
            progress=False, 
            auto_adjust=True,
            timeout=10
        )
        
        if df.empty:
            logger.warning(f"No data for {symbol}")
            return None
        
        _data_cache[symbol] = (df, datetime.now())
        logger.info(f"Fetched {len(df)} rows for {symbol}")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching {symbol}: {e}")
        return None

def clear_cache(symbol: Optional[str] = None):
    """Clear cache"""
    global _data_cache
    if symbol:
        _data_cache.pop(symbol, None)
    else:
        _data_cache.clear()
