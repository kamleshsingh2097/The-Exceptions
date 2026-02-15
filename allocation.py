"""Advanced Allocation Engine - The Brain

Implements multiple sophisticated allocation strategies:
1. Risk Parity - inverse volatility weighting (equal risk contribution)
2. Mean-Variance Optimization - Markowitz efficient frontier
3. Momentum-based weighting - favor positive momentum assets
4. Correlation-aware diversification - minimize portfolio correlation
5. Regime-adaptive selection - choose method based on market regime

Core philosophy: Allocate changes when regime changes.
Different regimes demand different allocation strategies.
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict, Tuple
from scipy.optimize import minimize


def risk_parity_weights(volatility: pd.Series) -> pd.Series:
    """Compute risk parity weights: w_i ∝ 1 / volatility_i
    
    Parameters:
    - volatility: Series of volatilities indexed by asset name
    
    Returns:
    - Series of weights normalized to sum to 1.0
    
    Logic:
    - Assets with lower volatility get higher weights
    - Assets with higher volatility get lower weights
    - Ensures equal risk contribution across assets
    """
    # Avoid division by zero
    inv_vol = 1.0 / (volatility.clip(lower=1e-8))
    
    # Handle NaN and invalid values
    inv_vol = inv_vol.fillna(inv_vol.median())
    inv_vol = inv_vol.replace([np.inf, -np.inf], inv_vol[~np.isinf(inv_vol)].max())
    
    # Normalize to sum to 1.0
    total = inv_vol.sum()
    if total <= 0:
        # Fallback to equal weight if something goes wrong
        weights = pd.Series(1.0 / len(volatility), index=volatility.index)
    else:
        weights = inv_vol / total
    
    return weights


def mean_variance_optimization(volatility: pd.Series, 
                               expected_returns: pd.Series,
                               correlation_matrix: Optional[np.ndarray] = None,
                               risk_aversion: float = 2.0) -> pd.Series:
    """Mean-Variance Optimization (Markowitz efficient frontier).
    
    Finds allocation that maximizes:
    portfolio_return - risk_aversion * portfolio_variance
    
    Parameters:
    - volatility: Asset volatilities (pd.Series indexed by asset name)
    - expected_returns: Expected returns per asset (pd.Series)
    - correlation_matrix: Asset correlation matrix (NxN numpy array)
      If None, assumes zero correlation (diagonal covariance matrix)
    - risk_aversion: Higher values = more conservative (default 2.0)
    
    Returns:
    - pd.Series of normalized weights
    
    Philosophy:
    - Balances return and risk trade-off
    - More sophisticated than simple risk parity
    - Incorporates return forecasts and correlations
    - Adapts aggressively in trending markets (positive returns)
    - Becomes defensive when expected returns decline
    """
    n_assets = len(volatility)
    
    # Build covariance matrix
    if correlation_matrix is not None and correlation_matrix.shape == (n_assets, n_assets):
        # Scale correlation matrix by volatilities
        vol_vec = volatility.values.reshape(-1, 1)
        cov_matrix = correlation_matrix * (vol_vec @ vol_vec.T)
    else:
        # Diagonal covariance (assume zero correlation if not provided)
        cov_matrix = np.diag(volatility.values ** 2)
    
    ret_vec = expected_returns.values
    
    # Objective: minimize negative Sharpe (maximize return - risk_aversion * variance)
    def neg_objective(w):
        portfolio_ret = np.sum(w * ret_vec)
        portfolio_var = w @ cov_matrix @ w
        return -(portfolio_ret - risk_aversion * portfolio_var)
    
    # Constraints: sum to 1
    constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
    
    # Bounds: no shorting (0 to 1 per asset)
    bounds = tuple((0, 1) for _ in range(n_assets))
    
    # Initial guess: equal weight
    w_init = np.array([1.0 / n_assets] * n_assets)
    
    try:
        result = minimize(neg_objective, w_init, method='SLSQP', 
                        bounds=bounds, constraints=constraints,
                        options={'ftol': 1e-9})
        
        if result.success:
            weights = pd.Series(result.x, index=volatility.index)
            weights = weights.clip(lower=0)  # Ensure non-negative
            weights = weights / weights.sum()  # Re-normalize
            return weights
        else:
            # Fallback to risk parity if optimization fails
            return risk_parity_weights(volatility)
    except Exception:
        # Fallback to risk parity if any error occurs
        return risk_parity_weights(volatility)


def momentum_based_weights(momentum: pd.Series, 
                          volatility: pd.Series,
                          momentum_threshold: float = 0.0) -> pd.Series:
    """Momentum-based allocation: favor assets with positive momentum.
    
    Allocation weights scale with momentum strength while accounting for volatility.
    
    Formula: w_i ∝ (1 + momentum_i) / volatility_i^2
    
    Parameters:
    - momentum: Momentum score per asset (returns, trend strength, etc.)
      Can be negative (bad momentum), positive (good momentum)
    - volatility: Asset volatilities (for risk normalization)
    - momentum_threshold: Only allocate to assets with momentum > threshold
      Default 0.0 = allocate to all, positive threshold = momentum-only
    
    Returns:
    - pd.Series of weights normalized to sum to 1.0
    
    Philosophy:
    - "Follow the winners" - concentrate in assets with positive momentum
    - Higher volatility = lower weight (risk-adjusted momentum)
    - Naturally de-rates underperforming assets
    - Ideal for trending markets (trending up/down regimes)
    - More aggressive than risk parity in bull markets
    - Defensive in bear markets (low/negative momentum)
    """
    # Scale momentum by (1 + momentum) to handle negative values
    momentum_adjusted = 1.0 + momentum
    
    # Zero out below-threshold momentum
    momentum_adjusted = momentum_adjusted.copy()
    momentum_adjusted[momentum < momentum_threshold] = 1e-8
    
    # Risk-adjusted: divide by volatility squared
    inv_vol_sq = 1.0 / (volatility.clip(lower=1e-8) ** 2)
    
    # Combine momentum and risk adjustment
    weights_raw = momentum_adjusted * inv_vol_sq
    
    # Handle edge cases
    weights_raw = weights_raw.fillna(weights_raw.median())
    weights_raw = weights_raw.replace([np.inf, -np.inf], weights_raw[~np.isinf(weights_raw)].max())
    
    # Normalize
    total = weights_raw.sum()
    if total > 0:
        weights = weights_raw / total
    else:
        weights = pd.Series(1.0 / len(momentum), index=momentum.index)
    
    return weights


def correlation_aware_weights(volatility: pd.Series,
                             correlation_matrix: Optional[np.ndarray] = None,
                             diversification_strength: float = 1.0) -> pd.Series:
    """Correlation-aware diversification: avoid highly correlated assets.
    
    Reduces allocation to assets with high average correlation to others.
    Increases allocation to assets that add diversification.
    
    Parameters:
    - volatility: Asset volatilities (for baseline weighting)
    - correlation_matrix: Asset correlation matrix (NxN numpy array)
      If None, assumes independent assets (equal weight)
    - diversification_strength: How much to penalize correlation (0-2)
      0 = ignore correlations (equal weight)
      1 = moderate diversification penalty
      2 = strong diversification focus
    
    Returns:
    - pd.Series of weights normalized to sum to 1.0
    
    Philosophy:
    - Start with risk parity weights (inverse volatility)
    - Penalize assets with high average correlation
    - Reward assets with low average correlation
    - Reduces portfolio concentration risk
    - Ideal for high volatility regime (correlation-aware defensive)
    - Also good for building resilient portfolios in normal regimes
    """
    # Start with risk parity as baseline
    rp_weights = risk_parity_weights(volatility)
    
    if correlation_matrix is None or correlation_matrix.shape[0] != len(volatility):
        # No correlation data: return risk parity
        return rp_weights
    
    # Calculate average correlation per asset (excluding self-correlation)
    n_assets = correlation_matrix.shape[0]
    avg_corr = np.array([
        np.mean([correlation_matrix[i, j] for j in range(n_assets) if i != j])
        for i in range(n_assets)
    ])
    
    # Diversification benefit: assets with lower avg correlation
    diversification_factor = 1.0 - (diversification_strength * avg_corr / 2.0)
    diversification_factor = np.clip(diversification_factor, 0.1, np.inf)  # Don't zero out
    
    # Apply to risk parity weights
    adjusted_weights = rp_weights.values * diversification_factor
    adjusted_weights = adjusted_weights / np.sum(adjusted_weights)
    
    weights = pd.Series(adjusted_weights, index=volatility.index)
    return weights


def regime_adaptive_allocation(volatility: pd.Series,
                             regime: Optional[str],
                             momentum: Optional[pd.Series] = None,
                             expected_returns: Optional[pd.Series] = None,
                             correlation_matrix: Optional[np.ndarray] = None) -> pd.Series:
    """Regime-adaptive allocation: select method based on market regime.
    
    Different regimes demand different allocation strategies:
    - Trending Up: Momentum-based allocation (follow winners)
    - Trending Down: Risk parity with reduced scale (steady but defensive)
    - High Volatility: Correlation-aware (diversify in chaos)
    - Crash: Risk parity with crisis adjustments
    - Normal: Mean-variance optimization (balanced approach)
    
    Parameters:
    - volatility: Asset volatilities
    - regime: Market regime ("Trending Up", "Trending Down", "High Volatility", "Crash", "Normal")
    - momentum: (optional) Momentum scores for trending regimes
    - expected_returns: (optional) Return forecasts for mean-variance
    - correlation_matrix: (optional) Correlation data for diversification
    
    Returns:
    - pd.Series of weights appropriate for current regime
    
    Philosophy:
    - Allocations change when regime changes (the key insight)
    - Trending markets: concentrate in winning assets (momentum)
    - Volatile markets: spread capital across uncorrelated assets
    - Crisis: protect capital with low-risk diversification
    - Normal: optimize return-risk balance
    """
    if regime is None:
        regime = "Normal"
    
    regime_lower = str(regime).lower()
    
    # Trending Up: momentum-based (aggressive, follow winners)
    if "trending" in regime_lower and "up" in regime_lower:
        if momentum is not None:
            return momentum_based_weights(momentum, volatility, momentum_threshold=-0.01)
        else:
            # Fallback: risk parity with positive scaling
            return risk_parity_weights(volatility)
    
    # Trending Down: risk parity but reduced
    elif "trending" in regime_lower and "down" in regime_lower:
        rp = risk_parity_weights(volatility)
        return rp * 0.5  # Reduce scale, keep diversification
    
    # High Volatility: correlation-aware diversification
    elif "high" in regime_lower and "volatility" in regime_lower:
        return correlation_aware_weights(volatility, correlation_matrix, 
                                        diversification_strength=2.0)
    
    # Crash: risk parity (defensive, simple)
    elif "crash" in regime_lower:
        return risk_parity_weights(volatility) * 0.3  # Minimal exposure
    
    # Normal: mean-variance optimization
    else:  # Normal regime
        if expected_returns is not None:
            return mean_variance_optimization(volatility, expected_returns, 
                                            correlation_matrix, risk_aversion=2.0)
        else:
            return risk_parity_weights(volatility)


def adjust_for_regime(weights: pd.Series, regime: Optional[str], defensive_asset: Optional[str] = None) -> pd.Series:
    """Adjust portfolio allocation based on detected market regime.
    
    Regime rules:
    - 'Crash': Reduce risky assets by 50%, shift to defensive if available
    - 'High Vol': Scale all positions down by 30%
    - 'Bear': Scale all positions down by 20%
    - 'Bull' or None: No change (keep as-is)
    
    Parameters:
    - weights: Current allocation weights
    - regime: Market regime label (Bull, Bear, High Vol, Crash)
    - defensive_asset: Asset to shift capital to during crashes
    
    Returns:
    - Adjusted weights normalized to sum to 1.0
    """
    w = weights.copy()
    
    if regime is None:
        return w
    
    # Handle both old and new regime names for backward compatibility
    regime_lower = str(regime).lower()
    
    if "crash" in regime_lower:
        # Severe risk reduction during crash
        print(f"Market regime detected: Crash.")
        print("Portfolio drawdown exceeded threshold.")
        print("Reducing equity allocation by 80%.")
        if defensive_asset is not None and defensive_asset in w.index:
            print(f"Increasing {defensive_asset} exposure.")
        w = w * 0.2  # Cut risky assets to 20%
        
        if defensive_asset is not None and defensive_asset in w.index:
            # Allocate freed-up capital to defensive asset
            freed_capital = 1.0 - w.sum()
            w.loc[defensive_asset] = w.loc[defensive_asset] + freed_capital
        else:
            if w.sum() > 0:
                w = w / w.sum()
            else:
                w = pd.Series(1.0 / len(w), index=w.index)
    
    elif "high" in regime_lower and "volatility" in regime_lower:
        # Moderate risk reduction when volatility spikes
        print(f"Market regime detected: High Volatility.")
        print("Portfolio volatility exceeded threshold.")
        print("Reducing equity allocation by 40%.")
        if defensive_asset is not None and defensive_asset in w.index:
            print(f"Increasing {defensive_asset} exposure.")
        w = w * 0.6  # Scale down to 60%
        
        if defensive_asset is not None and defensive_asset in w.index:
            freed_capital = 1.0 - w.sum()
            w.loc[defensive_asset] = w.loc[defensive_asset] + freed_capital * 0.5
            remaining_capital = 1.0 - w.loc[defensive_asset]
            if remaining_capital > 0 and w.sum() > w.loc[defensive_asset]:
                equity_weights = w[w.index != defensive_asset]
                equity_weights = equity_weights / equity_weights.sum() * remaining_capital
                w.update(equity_weights)
        
        if w.sum() > 0:
            w = w / w.sum()
        else:
            w = pd.Series(1.0 / len(w), index=w.index)
    
    elif "trending down" in regime_lower:
        print(f"Market regime detected: Trending Down.")
        print("Strong downtrend detected.")
        print("Reducing equity allocation by 50%.")
        if defensive_asset is not None and defensive_asset in w.index:
            print(f"Increasing {defensive_asset} exposure.")
        w = w * 0.5
        
        if w.sum() > 0:
            w = w / w.sum()
        else:
            w = pd.Series(1.0 / len(w), index=w.index)
    
    elif "trending up" in regime_lower:
        print(f"Market regime detected: Trending Up.")
        print("Strong uptrend detected.")
        print("Increasing equity allocation by 20%.")
        w = w * 1.2
        
        if w.sum() > 0:
            w = w / w.sum()
        else:
            w = pd.Series(1.0 / len(w), index=w.index)
    
    elif regime == "Bear":
        print(f"Market regime detected: Bear market.")
        print("Reducing equity allocation by 20%.")
        w = w * 0.8  # Scale down to 80%
        
        if w.sum() > 0:
            w = w / w.sum()
        else:
            w = pd.Series(1.0 / len(w), index=w.index)
    
    elif regime == "High Vol":
        print(f"Market regime detected: High volatility.")
        print("Portfolio volatility exceeded threshold.")
        print("Reducing equity allocation by 30%.")
        if defensive_asset is not None and defensive_asset in w.index:
            print(f"Increasing {defensive_asset} exposure.")
        w = w * 0.7
        
        if defensive_asset is not None and defensive_asset in w.index:
            freed_capital = 1.0 - w.sum()
            w.loc[defensive_asset] = w.loc[defensive_asset] + freed_capital * 0.5
            remaining_capital = 1.0 - w.loc[defensive_asset]
            if remaining_capital > 0 and w.sum() > w.loc[defensive_asset]:
                equity_weights = w[w.index != defensive_asset]
                equity_weights = equity_weights / equity_weights.sum() * remaining_capital
                w.update(equity_weights)
        
        if w.sum() > 0:
            w = w / w.sum()
        else:
            w = pd.Series(1.0 / len(w), index=w.index)
    
    return w
