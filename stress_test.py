"""
Stress testing module (Corrected, Realistic, Stable)

Simulates market shocks and crisis scenarios without unrealistic compounding.
Ensures returns stay within real-world bounds.
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from backtester import run_backtest


# ---------------------------------------------------------
# Utility: Safe Equity Return Calculation
# ---------------------------------------------------------
def compute_total_return(equity: pd.Series) -> float:
    initial_value = equity.iloc[0]
    final_value = equity.iloc[-1]
    return (final_value / initial_value) - 1.0


# ---------------------------------------------------------
# Price Shock Scenario (Corrected)
# ---------------------------------------------------------
def inject_price_shock(
    prices: pd.DataFrame,
    shock_pct: float = -0.10,
    shock_start: int = 50,
    shock_duration: int = 10
) -> pd.DataFrame:

    shocked = prices.copy()

    for i in range(shock_start, min(shock_start + shock_duration, len(prices))):
        shocked.iloc[i] = shocked.iloc[i - 1] * (1.0 + shock_pct)

    return shocked


# ---------------------------------------------------------
# Volatility Spike Scenario (Corrected & Non-Explosive)
# ---------------------------------------------------------
def volatility_spike_scenario(prices: pd.DataFrame, factor: float = 1.5) -> pd.DataFrame:

    returns = prices.pct_change().fillna(0)

    # amplify returns but clamp safely
    amp_returns = returns * factor
    amp_returns = amp_returns.clip(lower=-0.2, upper=0.2)  # realistic bounds

    amp_prices = (1 + amp_returns).cumprod()
    amp_prices = amp_prices.multiply(prices.iloc[0], axis=1)

    return amp_prices


# ---------------------------------------------------------
# Correlation Spike Scenario (Stabilized)
# ---------------------------------------------------------
def correlation_spike_scenario(
    prices: pd.DataFrame,
    correlation_factor: float = 0.7
) -> pd.DataFrame:

    returns = prices.pct_change().dropna()
    blended_returns = pd.DataFrame(index=returns.index)

    common_factor = returns.mean(axis=1)

    for col in returns.columns:
        blended = (
            (1 - correlation_factor) * returns[col]
            + correlation_factor * common_factor
        )
        blended_returns[col] = blended

    blended_returns = blended_returns.clip(-0.15, 0.15)

    corr_prices = (1 + blended_returns).cumprod()
    corr_prices = corr_prices.multiply(prices.iloc[0], axis=1)

    return corr_prices


# ---------------------------------------------------------
# REALISTIC Crisis Scenario (Major Fix)
# ---------------------------------------------------------
def create_crisis_scenario(
    prices: pd.DataFrame,
    shock_start: int = 50,
    shock_duration: int = 20,
    crash_magnitude: float = -0.25,  # -25% cumulative crash
    vol_factor: float = 2.0
) -> pd.DataFrame:

    crisis = prices.copy()
    returns = prices.pct_change().fillna(0)

    crisis_end = min(shock_start + shock_duration, len(prices))

    # -------- CRASH PHASE --------
    for i in range(shock_start, crisis_end):

        base_ret = returns.iloc[i].copy()

        # distribute total crash magnitude across shock days
        daily_shock = crash_magnitude / shock_duration  # e.g. -0.25/20 = -1.25% daily
        noise = np.random.normal(0, 0.01 * vol_factor, len(base_ret))

        stressed_ret = base_ret + daily_shock + noise
        stressed_ret = stressed_ret.clip(-0.10, 0.10)  # cap to avoid exploding

        crisis.iloc[i] = crisis.iloc[i - 1] * (1 + stressed_ret)

    # -------- RECOVERY PHASE (REALISTIC) --------
    for i in range(crisis_end, len(prices)):

        # realistic daily drift (0 to +0.1%)
        recovery_noise = np.random.normal(0.0003, 0.005, len(prices.columns))
        recovery_noise = np.clip(recovery_noise, -0.02, 0.02)

        crisis.iloc[i] = crisis.iloc[i - 1] * (1 + recovery_noise)

    return crisis


# ---------------------------------------------------------
# Main Stress Test Runner (Corrected)
# ---------------------------------------------------------
def run_comprehensive_stress_test(
    prices: pd.DataFrame,
    features: pd.DataFrame,
    target_vol: float = 0.10,
    drawdown_limit: float = -0.2,
    defensive_asset: Optional[str] = None
) -> Dict[str, Any]:

    results = {}

    # ---------------- BASE CASE ----------------
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
    base_dd = (base_equity / base_equity.cummax() - 1).min()

    results["base"] = {
        "equity_curve": base_equity,
        "total_return": base_return,
        "max_drawdown": base_dd,
    }

    # ---------------- CRISIS ----------------
    from feature_engineering import rolling_features

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
    crisis_dd = (crisis_equity / crisis_equity.cummax() - 1).min()

    results["crisis"] = {
        "equity_curve": crisis_equity,
        "total_return": crisis_return,
        "max_drawdown": crisis_dd,
        "capital_preservation_ratio": crisis_equity.iloc[-1] / base_equity.iloc[-1],
    }

    # ---------------- VOLATILITY ----------------
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
    vol_return = compute_total_return(vol_equity)
    vol_dd = (vol_equity / vol_equity.cummax() - 1).min()

    results["volatility"] = {
        "equity_curve": vol_equity,
        "total_return": vol_return,
        "max_drawdown": vol_dd,
    }

    # ---------------- CORRELATION ----------------
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
    corr_return = compute_total_return(corr_equity)
    corr_dd = (corr_equity / corr_equity.cummax() - 1).min()

    results["correlation"] = {
        "equity_curve": corr_equity,
        "total_return": corr_return,
        "max_drawdown": corr_dd,
    }

    # ---------------- RISK ENGINE SCORE ----------------
    score = 0
    for scenario in ["crisis", "volatility", "correlation"]:
        if results[scenario]["max_drawdown"] >= drawdown_limit:
            score += 1

    rating = "EXCELLENT" if score == 3 else "GOOD" if score == 2 else "WEAK"

    results["risk_engine_analysis"] = {
        "score": score,
        "rating": rating,
    }

    return results