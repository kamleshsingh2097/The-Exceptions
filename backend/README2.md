# Risk Management & Regime Detection Engine

This repository provides a fully integrated research-to-production pipeline for regime-aware allocation, robust risk management, walk-forward backtesting, stress testing, and an interactive Streamlit dashboard backed by a FastAPI server.

This README contains an architecture overview and a comprehensive, function-level reference for every major file so developers can quickly find and extend behavior.

## Table of contents

- Overview
- Architecture & dataflow
- Quick start
- File-level reference (detailed functions and behavior)
- API endpoints
- Next steps & recommendations

---

## Overview

The system is organized into three logical layers:

- Presentation: `app.py` (Streamlit UI) — user-facing dashboard, charts, and controls.
- API: `api_server.py` (FastAPI) — programmatic access to backtests, regime analysis, and stress testing.
- Core Engines: allocation (`allocation.py`), regime detection (`regime_detection.py`), risk management (`risk_engine.py`), feature construction (`feature_engineering.py`), backtesting (`backtester.py`), and measurement (`metrics.py`).

All feature computations are explicitly shifted/lagged to prevent lookahead bias (see `VERIFY_NO_LOOKAHEAD.py` and `data_loader.py`).

---

## Architecture & dataflow

1. UI calls API endpoints (e.g., `POST /backtest`).
2. API calls `data_loader.load_prices` + `feature_engineering.rolling_features` to prepare inputs.
3. API runs `backtester.run_backtest` which loops chronologically and at each date uses only prior information to:
   - estimate volatilities from features,
   - compute a base allocation (e.g., `allocation.risk_parity_weights`),
   - detect regime using `regime_detection.RegimeDetector`,
   - apply regime scaling (`allocation.adjust_for_regime`),
   - run layered risk controls (`risk_engine.comprehensive_risk_management`),
   - compute costs & portfolio return for the day.
4. API computes performance (`metrics.compute_performance`) and returns sanitized JSON to the UI.

---

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# start API
python api_server.py

# open UI
streamlit run app.py
```

---

## File-level reference (detailed)

Below each file lists exported functions/classes with their behavior, inputs, and outputs.

### `data_loader.py`
- Purpose: load prices and volumes without lookahead; provide simple helpers used across the system.
- Functions:
  - `load_prices(tickers, start_date, end_date, source='yfinance', csv_paths=None) -> pd.DataFrame`
    - Loads adjusted close prices, reindexes to business days, forward/backfills small gaps. Returns a DataFrame with one column per ticker.
  - `compute_returns(prices) -> pd.DataFrame` — daily percent changes, no lookahead.
  - `load_volume(...) -> pd.DataFrame` — loads volume or returns zeros when missing.
  - `load_market_data(...) -> (prices, volume)` — convenience wrapper.

### `feature_engineering.py`
- Purpose: compute lagged rolling features used by regime detection, allocation, and risk logic.
- Key function:
  - `rolling_features(prices, vol_window=30, ma_short=50, ma_long=200) -> (features_df, correlations_dict)`
    - Builds MultiIndex features: `('vol_30', ticker)`, `('ret_30', ticker)`, `('ma50', ticker)`, `('ma200', ticker)`, `('drawdown', ticker)`.
    - All rolling windows are shifted by 1 (features[t] uses up to t-1) to guarantee no lookahead.
    - Returns a dict of rolling correlation matrices keyed by date string.

### `regime_detection.py`
- Purpose: multi-indicator regime detection and recommended actions.
- Exports:
  - `MarketRegime` enum: `TRENDING_UP`, `TRENDING_DOWN`, `HIGH_VOLATILITY`, `CRASH`, `NORMAL`.
  - `RegimeDetector` class with:
    - `detect_regime_comprehensive(prices, features, current_date) -> (MarketRegime, indicators_dict)` — returns the detected regime and numeric indicators such as `avg_volatility`, `trend_strength`, `trend_direction`, `max_drawdown`, `current_drawdown`, `momentum_score`, `market_breadth`.
    - Internal helpers: `_calculate_average_volatility`, `_calculate_trend_strength`, `_calculate_trend_direction`, `_calculate_max_drawdown`, `_calculate_current_drawdown`, `_calculate_momentum_score`, `_calculate_market_breadth`, `_calculate_max_volatility`.
    - `get_regime_characteristics(regime) -> dict` — high-level recommendations, position sizing guidance and defensive allocation suggestions.

### `allocation.py`
- Purpose: multiple allocation strategies and a regime-adaptive selector.
- Functions:
  - `risk_parity_weights(volatility) -> pd.Series` — inverse-volatility normalized weights with NaN/inf handling.
  - `mean_variance_optimization(volatility, expected_returns, correlation_matrix=None, risk_aversion=2.0) -> pd.Series` — builds covariance, solves constrained optimization (no shorting) using `scipy.optimize.minimize`, falls back to risk parity on failure.
  - `momentum_based_weights(momentum, volatility, momentum_threshold=0.0) -> pd.Series` — weights ∝ (1+momentum)/vol^2, thresholding, and normalization.
  - `correlation_aware_weights(volatility, correlation_matrix=None, diversification_strength=1.0) -> pd.Series` — penalizes high-average-correlation assets starting from RP baseline.
  - `regime_adaptive_allocation(volatility, regime, momentum=None, expected_returns=None, correlation_matrix=None) -> pd.Series` — selects strategy according to regime.
  - `adjust_for_regime(weights, regime, defensive_asset=None) -> pd.Series` — simple scaling rules for Crash/High-Vol/Trending regimes; may allocate freed capital to `defensive_asset`.

### `risk_engine.py`
- Purpose: layered risk controls.
- Functions and behavior:
  - `volatility_targeting(weights, current_portfolio_vol, target_vol, max_scale_down=0.3) -> pd.Series` — scales portfolio to meet target volatility within `max_scale_down` constraint.
  - `drawdown_protection(weights, current_drawdown, drawdown_limit, reduction_factor=0.5) -> pd.Series` — progressive exposure reduction when drawdown exceeded.
  - `position_sizing_risk_parity(volatilities, risk_aversion=1.0, concentration_limit=0.4) -> pd.Series` — RP sizing with concentration caps.
  - `stop_loss_logic(weights, daily_returns, stop_loss_threshold=-0.03, recovery_period=5, defensive_asset=None) -> (pd.Series, bool)` — reduce losing positions and optionally shift to defensive asset; returns whether stop-loss triggered.
  - `comprehensive_risk_management(weights, volatilities, current_drawdown, daily_returns, target_vol=0.10, drawdown_limit=-0.20, stop_loss_threshold=-0.03, defensive_asset=None) -> (final_weights, risk_actions)` — orchestrates stop-loss → drawdown protection → volatility targeting; returns flags for applied protections.
  - `correlation_spike_protection(weights, corr_matrix, corr_threshold=0.85) -> pd.Series` — optional defense when correlations spike.

### `backtester.py`
- Purpose: walk-forward backtesting engine that simulates live trading using only historical data at each step.
- Key functions:
  - `run_backtest(prices, features, regimes=None, target_vol=0.10, drawdown_limit=-0.2, defensive_asset=None, transaction_costs=0.001) -> dict`
    - For each date (chronologically):
      1. Build vol vector from `features` (past-only).
      2. Compute base allocation (risk parity).
      3. Detect regime using historical information only.
      4. Adjust weights for regime and call `comprehensive_risk_management`.
      5. Compute turnover-based transaction costs and apply today's returns.
    - Returns keys: `equity_curve`, `daily_returns`, `allocation_history`, `regime_history`, `total_transaction_costs`.

  - `walk_forward_validation(prices, features, initial_train_months=12, test_months=3, step_months=1)` — run multiple out-of-sample folds.

### `stress_test.py`
- Purpose: simulate crisis scenarios and measure how the system reacts.
- Functions of interest:
  - `inject_price_shock(prices, shock_pct=-0.10, shock_start=50, shock_duration=10) -> pd.DataFrame`.
  - `volatility_spike_scenario(prices, factor=1.5) -> pd.DataFrame`.
  - `correlation_spike_scenario(prices, correlation_factor=0.7) -> pd.DataFrame`.
  - `create_crisis_scenario(prices, shock_start=50, shock_duration=20, crash_magnitude=-0.25, vol_factor=2.0) -> pd.DataFrame`.
  - `run_comprehensive_stress_test(prices, features, target_vol=0.10, drawdown_limit=-0.2, defensive_asset=None) -> dict` — runs base and stressed backtests and returns a consolidated result including `risk_engine_analysis`.

### `metrics.py`
- Purpose: compute performance statistics.
- Exports: `CAGR`, `annualized_vol`, `sharpe_ratio`, `sortino_ratio`, `max_drawdown`, `calmar_ratio`, and `compute_performance(returns, equity)` which aggregates the important metrics into a dict.

### `api_server.py`
- Purpose: FastAPI server that exposes the system programmatically.
- Highlights:
  - `sanitize(obj)` — convert pandas/numpy objects to JSON-serializable structures.
  - `POST /backtest` — runs `run_backtest` and returns a `BacktestResponse` with performance metrics.
  - `POST /stress-test` — launches `run_comprehensive_stress_test` in the background and stores results in-memory under a UUID.
  - `POST /regime-analysis` — returns comprehensive regime indicators and recommendations.

### `app.py`
- Purpose: Streamlit UI that calls the API and visualizes results.
- Important helpers: `call_api(endpoint, method='GET', data=None)` and rendering helpers for metric cards and charts.

### `automation/auto_trader.py`
- Purpose: example auto-trader skeleton showing how to wire regime detection, allocation, risk, and execution.

### Demos and utilities
- `complete_system_demo.py`, `complete_trading_demo.py` — full-system demonstrations using synthetic data.
- `VERIFY_NO_LOOKAHEAD.py` — demonstration of correct (.shift(1)) vs incorrect feature construction.
- `data/downloader.py` — small yfinance wrapper with caching for intraday usage.
- `data/universe.py` — example ticker universe lists.

---

## API endpoints

- `GET /health` — service health
- `POST /backtest` — run backtest, returns `BacktestResponse` (metrics, final value)
- `POST /regime-analysis` — detect and return current regime indicators
- `POST /stress-test` — start background stress test, returns `task_id`
- `GET /stress-test/{task_id}` — poll for async test status/result

---

## Troubleshooting

### Streamlit Errors

**`StreamlitDuplicateElementId` on startup**: FIXED ✅
- All buttons now have unique `key=` parameters
- No more duplicate button declarations
- If error persists, clear cache: `streamlit cache clear`

**API connection errors**: 
- Ensure `python api_server.py` is running before `streamlit run app.py`
- API defaults to `http://localhost:8000`
- Check port availability: `lsof -i :8000`

**Missing metrics in results**:
- Ensure date range has ≥30 trading days
- Check that tickers have data for selected dates
- Try default dates: 2023-01-01 → 2024-12-31

### Expected Behavior (Not Bugs)

**Same dates → same backtest results**: Yes, this is correct. Identical inputs produce deterministic outputs. To see different results, change the date range.

**Stress test slower than backtest**: Expected. Stress test runs base + crisis scenario (2x computation).

## Version History

- **v1.0** (Current): Production-ready system with full regime detection, risk management, backtesting, and stress testing. All known issues fixed.

## Next steps & recommendations

- Add unit tests (pytest) for allocation functions, regime thresholds, and risk engine permutations.
- Add sample CSVs and an integration dataset for CI without yfinance.
- Add Docker + docker-compose for reproducible demos.
- Persist stress-test results to Redis or disk for durability.
- Add real-time execution hooks for live trading integration.
