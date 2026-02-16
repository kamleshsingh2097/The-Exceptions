"""
Stress Testing Module (Production-Grade, Realistic, Stable)

Simulates:
- Crisis crash scenario
- Volatility spike
- Correlation spike

Designed for institutional-style evaluation.
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
import logging

from backtester import run_backtest


# ---------------------------------------------------------
# Utility: Safe Total Return
# ---------------------------------------------------------
def compute_total_return(equity: pd.Series) -> float:
    initial_value = equity.iloc[0]
    final_value = equity.iloc[-1]
    return (final_value / initial_value) - 1.0


# ---------------------------------------------------------
# Utility: Max Drawdown
# ---------------------------------------------------------
def compute_max_drawdown(equity: pd.Series) -> float:
    return (equity / equity.cummax() - 1).min()


# ---------------------------------------------------------
# Volatility Spike Scenario
# ---------------------------------------------------------
def volatility_spike_scenario(prices: pd.DataFrame, factor: float = 1.5) -> pd.DataFrame:

    returns = prices.pct_change().fillna(0)

    amplified = returns * factor
    amplified = amplified.clip(-0.2, 0.2)  # safety bounds

    new_prices = (1 + amplified).cumprod()
    new_prices = new_prices.multiply(prices.iloc[0], axis=1)

    return new_prices


# ---------------------------------------------------------
# Correlation Spike Scenario
# ---------------------------------------------------------
def correlation_spike_scenario(
    prices: pd.DataFrame,
    correlation_factor: float = 0.7
) -> pd.DataFrame:

    returns = prices.pct_change().dropna()
    blended_returns = pd.DataFrame(index=returns.index)

    common_factor = returns.mean(axis=1)

    for col in returns.columns:
        blended_returns[col] = (
            (1 - correlation_factor) * returns[col]
            + correlation_factor * common_factor
        )

    blended_returns = blended_returns.clip(-0.15, 0.15)

    corr_prices = (1 + blended_returns).cumprod()
    corr_prices = corr_prices.multiply(prices.iloc[0], axis=1)

    return corr_prices


# ---------------------------------------------------------
# Crisis Scenario (Geometric Crash + Controlled Recovery)
# ---------------------------------------------------------
def create_crisis_scenario(
    prices: pd.DataFrame,
    shock_start: int = 50,
    shock_duration: int = 20,
    crash_magnitude: float = -0.25,   # -25% cumulative crash
    vol_factor: float = 2.0
) -> pd.DataFrame:

    crisis = prices.copy()
    returns = prices.pct_change().fillna(0)

    crisis_end = min(shock_start + shock_duration, len(prices))

    # Geometric crash distribution (realistic)
    daily_crash = (1 + crash_magnitude) ** (1 / shock_duration) - 1

    # -------- CRASH PHASE --------
    for i in range(shock_start, crisis_end):

        base_ret = returns.iloc[i].copy()

        noise = np.random.normal(0, 0.01 * vol_factor, len(base_ret))
        stressed_ret = base_ret + daily_crash + noise
        stressed_ret = stressed_ret.clip(-0.10, 0.10)

        crisis.iloc[i] = crisis.iloc[i - 1] * (1 + stressed_ret)

    # -------- RECOVERY PHASE --------
    for i in range(crisis_end, len(prices)):

        recovery_noise = np.random.normal(0.0003, 0.005, len(prices.columns))
        recovery_noise = np.clip(recovery_noise, -0.02, 0.02)

        crisis.iloc[i] = crisis.iloc[i - 1] * (1 + recovery_noise)

    return crisis


# ---------------------------------------------------------
# Main Stress Test Engine
# ---------------------------------------------------------
def run_comprehensive_stress_test(
    prices: pd.DataFrame,
    features: pd.DataFrame,
    target_vol: float = 0.10,
    drawdown_limit: float = -0.20,
    defensive_asset: Optional[str] = None
) -> Dict[str, Any]:

    logger = logging.getLogger(__name__)
    logger.info(
        f"Stress test running from {prices.index[0]} to {prices.index[-1]} "
        f"({len(prices)} trading days)"
    )

    results = {}

    # ===============================
    # BASE CASE
    # ===============================
    base_result = run_backtest(
        prices,
        features,
        None,
        target_vol=target_vol,
        drawdown_limit=drawdown_limit,
        defensive_asset=defensive_asset
    )

    base_equity = base_result["equity_curve"]
    base_return = compute_total_return(base_equity)
    base_dd = compute_max_drawdown(base_equity)

    results["base"] = {
        "total_return": base_return,
        "max_drawdown": base_dd,
    }

    logger.info(f"Base: Return={base_return:.2%}, MaxDD={base_dd:.2%}")

    # Import here to avoid circular imports
    from feature_engineering import rolling_features

    # ===============================
    # CRISIS SCENARIO
    # ===============================
    crisis_prices = create_crisis_scenario(prices)
    crisis_features, _ = rolling_features(crisis_prices)

    crisis_result = run_backtest(
        crisis_prices,
        crisis_features,
        None,
        target_vol=target_vol,
        drawdown_limit=drawdown_limit,
        defensive_asset=defensive_asset
    )

    crisis_equity = crisis_result["equity_curve"]
    crisis_return = compute_total_return(crisis_equity)
    crisis_dd = compute_max_drawdown(crisis_equity)

    # --- Capital Preservation (Final Wealth Based) ---
    capital_preservation_ratio = crisis_equity.iloc[-1] / base_equity.iloc[-1]

    # --- Drawdown Protection (Professional Metric) ---
    if base_dd != 0:
        drawdown_protection = 1 - (abs(crisis_dd) / abs(base_dd))
    else:
        drawdown_protection = 0.0

    results["crisis"] = {
        "total_return": crisis_return,
        "max_drawdown": crisis_dd,
        "capital_preservation_ratio": capital_preservation_ratio,
        "drawdown_protection": drawdown_protection,
    }

    logger.info(
        f"Crisis: Return={crisis_return:.2%}, "
        f"MaxDD={crisis_dd:.2%}, "
        f"CapitalPreserved={capital_preservation_ratio:.1%}, "
        f"DDProtection={drawdown_protection:.1%}"
    )

    # ===============================
    # VOLATILITY SPIKE
    # ===============================
    vol_prices = volatility_spike_scenario(prices)
    vol_features, _ = rolling_features(vol_prices)

    vol_result = run_backtest(
        vol_prices,
        vol_features,
        None,
        target_vol=target_vol,
        drawdown_limit=drawdown_limit,
        defensive_asset=defensive_asset
    )

    vol_equity = vol_result["equity_curve"]

    results["volatility"] = {
        "total_return": compute_total_return(vol_equity),
        "max_drawdown": compute_max_drawdown(vol_equity),
    }

    # ===============================
    # CORRELATION SPIKE
    # ===============================
    corr_prices = correlation_spike_scenario(prices)
    corr_features, _ = rolling_features(corr_prices)

    corr_result = run_backtest(
        corr_prices,
        corr_features,
        None,
        target_vol=target_vol,
        drawdown_limit=drawdown_limit,
        defensive_asset=defensive_asset
    )

    corr_equity = corr_result["equity_curve"]

    results["correlation"] = {
        "total_return": compute_total_return(corr_equity),
        "max_drawdown": compute_max_drawdown(corr_equity),
    }

    # ===============================
    # RISK ENGINE SCORE
    # ===============================
    score = 0
    for scenario in ["crisis", "volatility", "correlation"]:
        if results[scenario]["max_drawdown"] >= drawdown_limit:
            score += 1

    rating = "EXCELLENT" if score == 3 else "GOOD" if score == 2 else "WEAK"

    results["risk_engine_analysis"] = {
        "score": score,
        "rating": rating,
        "capital_preservation_ratio": capital_preservation_ratio,
        "drawdown_protection": drawdown_protection,
    }

    return results
