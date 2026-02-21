"""Performance metrics computed from equity or returns."""
from typing import Dict
import numpy as np
import pandas as pd


def annualize_factor(days_per_year: int = 252):
    return days_per_year


def CAGR(equity: pd.Series) -> float:
    days = len(equity)
    if days < 2:
        return 0.0
    start, end = equity.iloc[0], equity.iloc[-1]
    years = days / 252.0
    return (end / start) ** (1.0 / years) - 1.0 if start > 0 else 0.0


def annualized_vol(returns: pd.Series) -> float:
    return returns.std() * np.sqrt(252)


def sharpe_ratio(returns: pd.Series, rf: float = 0.0) -> float:
    ann_ret = returns.mean() * 252
    ann_vol = annualized_vol(returns)
    return (ann_ret - rf) / ann_vol if ann_vol > 0 else 0.0


def sortino_ratio(returns: pd.Series, rf: float = 0.0) -> float:
    neg = returns[returns < 0]
    downside = neg.std() * np.sqrt(252) if not neg.empty else 0.0
    ann_ret = returns.mean() * 252
    return (ann_ret - rf) / downside if downside > 0 else 0.0


def max_drawdown(equity: pd.Series) -> float:
    roll_max = equity.cummax()
    drawdown = equity / roll_max - 1
    return drawdown.min()


def calmar_ratio(equity: pd.Series) -> float:
    cagr = CAGR(equity)
    mdd = abs(max_drawdown(equity))
    return cagr / mdd if mdd > 0 else 0.0


def compute_performance(returns: pd.Series, equity: pd.Series) -> Dict[str, float]:
    return {
        "CAGR": float(CAGR(equity)),
        "Annualized_Volatility": float(annualized_vol(returns)),
        "Sharpe_Ratio": float(sharpe_ratio(returns)),
        "Sortino_Ratio": float(sortino_ratio(returns)),
        "Max_Drawdown": float(max_drawdown(equity)),
        "Calmar_Ratio": float(calmar_ratio(equity))
    }
