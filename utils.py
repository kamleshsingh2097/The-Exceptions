from datetime import datetime, time
import pytz
import logging
from typing import Optional
import json
import os

# File used to persist the selected ticker for cross-process sharing
_SELECTION_PATH = os.path.join(os.path.dirname(__file__), "selected_ticker.json")

# Setup logging
logger = logging.getLogger(__name__)

# IST timezone
IST = pytz.timezone('Asia/Kolkata')

# Market hours: 9:15 AM to 3:30 PM IST
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)


def is_market_hours() -> bool:
    """Check if current time is within market hours (9:15 AM - 3:30 PM IST)"""
    try:
        now = datetime.now(IST).time()
        return MARKET_OPEN <= now <= MARKET_CLOSE
    except Exception as e:
        logger.error(f"Error checking market hours: {e}")
        return False


def is_weekday() -> bool:
    """Check if today is a weekday (Monday-Friday)"""
    try:
        now = datetime.now(IST)
        return now.weekday() < 5  # 0-4 are Monday-Friday
    except Exception as e:
        logger.error(f"Error checking weekday: {e}")
        return False


def is_trading_hours() -> bool:
    """Combined check: market hours AND weekday"""
    return is_market_hours() and is_weekday()


def get_ist_now() -> datetime:
    """Get current datetime in IST timezone"""
    try:
        return datetime.now(IST)
    except Exception as e:
        logger.error(f"Error getting IST time: {e}")
        return datetime.now()


def get_ist_time_string(dt: Optional[datetime] = None) -> str:
    """Get formatted IST time string"""
    try:
        if dt is None:
            dt = get_ist_now()
        return dt.strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception as e:
        logger.error(f"Error formatting time: {e}")
        return "N/A"


def safe_get(obj: dict, key: str, default=None):
    """Safely get value from dictionary with default"""
    try:
        return obj.get(key, default) if isinstance(obj, dict) else default
    except Exception as e:
        logger.warning(f"Error accessing key {key}: {e}")
        return default


def safe_float(value, default: float = 0.0) -> float:
    """Safely convert value to float"""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def safe_int(value, default: int = 0) -> int:
    """Safely convert value to int"""
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def write_selected_ticker(ticker: str) -> None:
    """Persist the selected ticker to a small JSON file.

    This allows other processes (for example `api_server.py`) to
    read the current selection.
    """
    try:
        payload = {"ticker": str(ticker)}
        with open(_SELECTION_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f)
    except Exception:
        logger.exception("Failed to write selected ticker")


def read_selected_ticker() -> Optional[str]:
    """Read the persisted selected ticker (or return None)."""
    try:
        if not os.path.exists(_SELECTION_PATH):
            return None
        with open(_SELECTION_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)
            return payload.get("ticker")
    except Exception:
        logger.exception("Failed to read selected ticker")
        return None