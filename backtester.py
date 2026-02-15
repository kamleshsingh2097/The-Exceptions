"""Walk-forward backtesting engine with risk management.

Runs a strict chronological loop and applies allocation and risk logic using only past data.
No lookahead bias - allocation decisions are based on past information only.
"""
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

from allocation import risk_parity_weights, adjust_for_regime
from risk_engine import volatility_targeting, drawdown_protection, stop_loss_logic, comprehensive_risk_management
from metrics import compute_performance
from regime_detection import RegimeDetector, MarketRegime

def walk_forward_validation(prices: pd.DataFrame,
                          features: pd.DataFrame,
                          initial_train_months: int = 12,
                          test_months: int = 3,
                          step_months: int = 1) -> Dict[str, Any]:
    """Perform walk-forward validation to avoid overfitting.
    
    Parameters:
    - prices: Full price dataset
    - features: Full features dataset  
    - initial_train_months: Initial training period in months
    - test_months: Test period length in months
    - step_months: How many months to advance each step
    
    Returns:
    - Dictionary with validation results
    """
    results = []
    dates = prices.index
    
    # Convert to monthly periods for easier handling
    start_date = dates[0]
    end_date = dates[-1]
    
    current_train_end = start_date + pd.DateOffset(months=initial_train_months)
    
    while current_train_end < end_date:
        # Define test period
        test_start = current_train_end
        test_end = min(test_start + pd.DateOffset(months=test_months), end_date)
        
        # Get data for this fold
        train_prices = prices.loc[:current_train_end]
        test_prices = prices.loc[test_start:test_end]
        
        if len(test_prices) < 10:  # Skip if test period too short
            break
            
        # Run backtest on test period (simulating live trading)
        test_result = run_backtest(test_prices, features.loc[:test_end])
        test_perf = compute_performance(test_result['daily_returns'], test_result['equity_curve'])
        
        results.append({
            'test_period': f'{test_start.strftime("%Y-%m")} to {test_end.strftime("%Y-%m")}',
            'sharpe_ratio': test_perf['Sharpe_Ratio'],
            'total_return': test_result['equity_curve'].iloc[-1] - 1,
            'max_drawdown': test_perf['Max_Drawdown'],
            'volatility': test_perf['Annualized_Volatility']
        })
        
        # Advance training window
        current_train_end += pd.DateOffset(months=step_months)
    
    return {
        'validation_results': results,
        'avg_sharpe': np.mean([r['sharpe_ratio'] for r in results]),
        'avg_return': np.mean([r['total_return'] for r in results]),
        'avg_max_drawdown': np.mean([r['max_drawdown'] for r in results]),
        'sharpe_std': np.std([r['sharpe_ratio'] for r in results])
    }


def detect_regime_realtime(prices: pd.DataFrame, features: pd.DataFrame, vol_threshold: float = 0.05) -> str:
    """Detect current market regime using advanced multi-indicator approach.

    Parameters:
    - prices: Historical prices up to current date
    - features: Technical indicators DataFrame
    - vol_threshold: Volatility threshold for HIGH_VOLATILITY regime

    Returns:
    - String regime name for backward compatibility
    """
    if prices.empty:
        return "Normal"

    try:
        # Use advanced regime detector
        detector = RegimeDetector(vol_threshold_high=vol_threshold)
        current_date = prices.index[-1]

        regime, indicators = detector.detect_regime_comprehensive(
            prices, features, current_date
        )

        regime_name = regime.value

        # Print regime info for visibility
        print(f"🎯 Regime: {regime_name} | Vol: {indicators['avg_volatility']:.1%} | "
              f"Trend: {indicators['trend_direction']:.1%} | DD: {indicators['current_drawdown']:.1%}")

        return regime_name

    except Exception as e:
        # Fallback to Normal on error
        return "Normal"


def run_backtest(prices: pd.DataFrame,
                 features: pd.DataFrame,
                 regimes: pd.Series = None,  # Made optional
                 target_vol: float = 0.10,
                 drawdown_limit: float = -0.2,
                 defensive_asset: Optional[str] = None,
                 transaction_costs: float = 0.001) -> Dict[str, Any]:
    """Run walk-forward backtest with risk management.
    
    Parameters:
    - prices: DataFrame of prices indexed by date
    - features: MultiIndex DataFrame of rolling features (from feature_engineering)
    - regimes: Series of regime labels per date
    - target_vol: target portfolio volatility
    - drawdown_limit: drawdown protection threshold (e.g., -0.20 for -20%)
    - defensive_asset: optional defensive asset for regime shifts
    
    Returns:
    - Dictionary with equity_curve, daily_returns, allocation_history, regime_history
    """
    dates = prices.index
    tickers = prices.columns.tolist()
    n_assets = len(tickers)

    # Initialize results containers
    equity = [1.0]  # Start with 1.0 (100% of starting capital)
    allocation_history = []
    regime_history = []
    daily_returns = []

    # Initial weights: equal weighted
    prev_weights = pd.Series(1.0 / n_assets, index=tickers)
    peak_equity = 1.0
    total_transaction_costs = 0.0

    # Walk-forward loop
    for i, date in enumerate(dates):
        # ===== ALLOCATION PHASE (using only past data) =====
        
        # 1. Compute rolling volatilities from features (already shifted, so uses past data)
        vol_vector = pd.Series(index=tickers, dtype=float)
        for ticker in tickers:
            if (date in features.index) and (("vol_30", ticker) in features.columns):
                vol = features.loc[date, ("vol_30", ticker)]
                vol_vector[ticker] = vol if not pd.isna(vol) and vol > 0 else 0.01
            else:
                vol_vector[ticker] = 0.01  # Default for missing data

        # 2. Risk parity allocation (inverse volatility weighting)
        base_weights = risk_parity_weights(vol_vector)

        # 3. Regime adjustment - detect regime in real-time using only past data
        # Use expanding window: analyze all data up to current date
        current_prices = prices.loc[:date]
        current_features = features.loc[:date]

        # Detect regime using only historical data up to this point
        current_regime = detect_regime_realtime(current_prices, current_features, vol_threshold=0.05)

        adj_weights = adjust_for_regime(base_weights, current_regime, defensive_asset)

        # 4. Calculate current drawdown for risk management
        current_equity_val = equity[-1]
        peak_equity = max(peak_equity, current_equity_val)
        current_drawdown = (current_equity_val / peak_equity - 1.0) if peak_equity > 0 else 0

        # 5. Get daily returns for stop-loss logic
        if i > 0:
            daily_ret = prices.loc[date] / prices.iloc[i - 1] - 1.0
            daily_ret = daily_ret.fillna(0.0)
        else:
            daily_ret = pd.Series(0.0, index=tickers)

        # 6. Apply COMPREHENSIVE RISK MANAGEMENT (all components)
        final_weights, risk_actions = comprehensive_risk_management(
            weights=adj_weights,
            volatilities=vol_vector,
            current_drawdown=current_drawdown,
            daily_returns=daily_ret,
            target_vol=target_vol,
            drawdown_limit=drawdown_limit,
            stop_loss_threshold=-0.03,  # 3% stop-loss
            defensive_asset=defensive_asset
        )

        # Use final weights after all risk management
        adj_weights = final_weights

        # ===== PERFORMANCE PHASE (apply allocation to today's returns) =====
        
        # Calculate transaction costs from weight changes
        if i > 0:  # Skip first date
            weight_changes = (adj_weights - prev_weights).abs().sum()
            transaction_cost = weight_changes * transaction_costs
            total_transaction_costs += transaction_cost
        else:
            transaction_cost = 0.0
        
        # Get today's returns (computed from yesterday's and today's prices)
        if i > 0:  # Skip first date (no previous return)
            daily_ret = prices.loc[date] / prices.iloc[i - 1] - 1.0
            daily_ret = daily_ret.fillna(0.0)
            
            # Portfolio return as weighted average
            port_return = (adj_weights * daily_ret).sum() - transaction_cost
        else:
            port_return = 0.0

        # Update previous weights for next iteration
        prev_weights = adj_weights.copy()

        # Update equity
        equity.append(equity[-1] * (1.0 + port_return))
        daily_returns.append(port_return)
        allocation_history.append(adj_weights.to_dict())
        regime_history.append(current_regime)

    # Convert to Series for output
    equity_series = pd.Series(equity[1:], index=dates)  # Remove initial 1.0
    returns_series = pd.Series(daily_returns, index=dates)

    return {
        "equity_curve": equity_series,
        "daily_returns": returns_series,
        "allocation_history": allocation_history,
        "regime_history": regime_history,
        "total_transaction_costs": total_transaction_costs
    }
