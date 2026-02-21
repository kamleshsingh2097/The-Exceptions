"""Comprehensive Risk Management Engine.

Implements all critical risk management components:
A) Volatility Targeting: Reduce position size when portfolio volatility > threshold
B) Drawdown Protection: Cut exposure when portfolio drawdown > X%
C) Position Sizing: Larger weights for low-risk assets (risk parity)
D) Stop-Loss Logic: Reduce exposure during sharp losses

This is the most important part - risk control is harder than prediction.
"""
from typing import Dict, Optional, Tuple, Union
import pandas as pd
import numpy as np


def volatility_targeting(weights: pd.Series,
                         current_portfolio_vol: float,
                         target_vol: float,
                         max_scale_down: float = 0.3) -> pd.Series:
    """Advanced volatility targeting with minimum position limits.

    A) Volatility Targeting: If portfolio volatility > threshold → reduce position size

    Parameters:
    - weights: Current portfolio weights
    - current_portfolio_vol: Current portfolio volatility (annualized)
    - target_vol: Target portfolio volatility (annualized)
    - max_scale_down: Maximum allowed scale-down factor (e.g., 0.3 = max 70% reduction)

    Returns:
    - Adjusted weights scaled to meet volatility target
    """
    if current_portfolio_vol <= 0 or target_vol <= 0:
        return weights

    # Calculate required scaling factor
    scale_factor = target_vol / current_portfolio_vol

    # Limit maximum scale-down to prevent over-reduction
    scale_factor = max(scale_factor, max_scale_down)

    # Apply scaling
    scaled_weights = weights * scale_factor

    print(f"VOLATILITY TARGETING: Portfolio vol {current_portfolio_vol:.3f} > target {target_vol:.3f}, scaling down by {scale_factor:.2f}")
    print(f"   Weights scaled from {weights.sum():.3f} to {scaled_weights.sum():.3f}")

    return scaled_weights


def drawdown_protection(weights: pd.Series,
                       current_drawdown: float,
                       drawdown_limit: float,
                       reduction_factor: float = 0.5) -> pd.Series:
    """Advanced drawdown protection with progressive scaling.

    B) Drawdown Protection: If portfolio drawdown > X% → cut exposure

    Parameters:
    - weights: Current portfolio weights
    - current_drawdown: Current drawdown as decimal (e.g., -0.15 for -15%)
    - drawdown_limit: Drawdown threshold as decimal (e.g., -0.20 for -20%)
    - reduction_factor: Factor to reduce exposure by (e.g., 0.5 = 50% reduction)

    Returns:
    - Adjusted weights with reduced exposure if drawdown exceeded
    """
    if current_drawdown > -abs(drawdown_limit):  # Drawdown not exceeded
        return weights

    # Calculate how much drawdown exceeded the limit
    excess_drawdown = abs(current_drawdown) - abs(drawdown_limit)
    severity_factor = min(1.0, excess_drawdown / abs(drawdown_limit))  # 0-1 scale

    # Progressive reduction based on severity
    effective_reduction = reduction_factor * (0.5 + 0.5 * severity_factor)  # 50%-100% of reduction_factor

    reduced_weights = weights * effective_reduction

    print(f"DRAWDOWN PROTECTION: Drawdown {current_drawdown:.1%} exceeded limit {-abs(drawdown_limit):.1%}")
    print(f"   Reducing exposure by {effective_reduction:.0%} (severity: {severity_factor:.1%})")

    return reduced_weights


def position_sizing_risk_parity(volatilities: pd.Series,
                               risk_aversion: float = 1.0,
                               concentration_limit: float = 0.4) -> pd.Series:
    """Advanced position sizing using risk parity principles.

    C) Position Sizing: Larger weight for low-risk assets

    Parameters:
    - volatilities: Series of asset volatilities
    - risk_aversion: Risk aversion parameter (higher = more conservative)
    - concentration_limit: Maximum weight for any single asset

    Returns:
    - Risk parity weights with concentration limits
    """
    # Risk parity: weights proportional to 1/volatility
    inv_vol = 1.0 / volatilities.clip(lower=1e-8)

    # Apply risk aversion
    risk_weights = inv_vol ** risk_aversion

    # Normalize to sum to 1
    weights = risk_weights / risk_weights.sum()

    # Apply concentration limits
    if weights.max() > concentration_limit:
        # Redistribute excess weight from concentrated positions
        excess = weights[weights > concentration_limit] - concentration_limit
        weights[weights > concentration_limit] = concentration_limit

        # Redistribute to other assets proportionally
        remaining_weight = excess.sum()
        other_assets = weights[weights < concentration_limit]
        if len(other_assets) > 0:
            redistribution = remaining_weight * (other_assets / other_assets.sum())
            weights.update(other_assets + redistribution)

    return weights


def stop_loss_logic(weights: pd.Series,
                   daily_returns: Union[pd.Series, pd.DataFrame],
                   stop_loss_threshold: float = -0.03,
                   recovery_period: int = 5,
                   defensive_asset: Optional[str] = None) -> Tuple[pd.Series, bool]:
    """Advanced stop-loss logic with recovery mechanism.

    D) Stop-Loss Logic: Reduce exposure during sharp loss

    Parameters:
    - weights: Current portfolio weights
    - daily_returns: Series of daily returns for each asset (or DataFrame for multiple assets)
    - stop_loss_threshold: Loss threshold to trigger stop-loss (e.g., -0.03 for -3%)
    - recovery_period: Days to wait before allowing position increases
    - defensive_asset: Asset to shift capital to during stop-loss

    Returns:
    - Tuple of (adjusted_weights, stop_loss_triggered)
    """
    stop_loss_triggered = False
    adjusted_weights = weights.copy()

    # Handle both Series (single asset) and DataFrame (multiple assets)
    if isinstance(daily_returns, pd.DataFrame):
        # For DataFrame, check the most recent day for each asset
        recent_returns = daily_returns.iloc[-1]  # Most recent day
        severe_losses = recent_returns <= -abs(stop_loss_threshold)
    else:
        # For Series, check the series directly
        severe_losses = daily_returns <= -abs(stop_loss_threshold)

    if severe_losses.any():
        stop_loss_triggered = True
        losing_assets = severe_losses[severe_losses].index.tolist()

        print(f"STOP-LOSS TRIGGERED: {len(losing_assets)} assets exceeded {stop_loss_threshold:.1%} loss threshold")

        # Reduce exposure to losing assets
        reduction_factor = 0.3  # Reduce to 30% of original position
        for asset in losing_assets:
            if asset in adjusted_weights.index:
                original_weight = adjusted_weights[asset]
                adjusted_weights[asset] *= reduction_factor
                print(f"   {asset}: {original_weight:.1%} -> {adjusted_weights[asset]:.1%}")

        # Shift capital to defensive asset if available
        if defensive_asset and defensive_asset in adjusted_weights.index:
            freed_capital = weights.sum() - adjusted_weights.sum()
            adjusted_weights[defensive_asset] += freed_capital
            print(f"   Capital shifted to {defensive_asset}: +{freed_capital:.1%}")

        # Renormalize
        if adjusted_weights.sum() > 0:
            adjusted_weights = adjusted_weights / adjusted_weights.sum()

    return adjusted_weights, stop_loss_triggered


def comprehensive_risk_management(weights: pd.Series,
                                volatilities: pd.Series,
                                current_drawdown: float,
                                daily_returns: pd.Series,
                                target_vol: float = 0.10,
                                drawdown_limit: float = -0.20,
                                stop_loss_threshold: float = -0.03,
                                defensive_asset: Optional[str] = None) -> Tuple[pd.Series, Dict[str, bool]]:
    """Comprehensive risk management combining all components.

    Applies all risk management rules in priority order:
    1. Stop-loss (immediate action)
    2. Drawdown protection (severe risk reduction)
    3. Volatility targeting (position sizing)

    Parameters:
    - weights: Current portfolio weights
    - volatilities: Current asset volatilities
    - current_drawdown: Current portfolio drawdown
    - daily_returns: Recent daily returns
    - target_vol: Target portfolio volatility
    - drawdown_limit: Drawdown protection threshold
    - stop_loss_threshold: Stop-loss trigger threshold
    - defensive_asset: Defensive asset for capital shifts

    Returns:
    - Tuple of (final_weights, risk_actions_taken)
    """
    risk_actions = {
        'stop_loss_triggered': False,
        'drawdown_protection_triggered': False,
        'volatility_targeting_applied': False
    }

    # Start with current weights
    final_weights = weights.copy()

    # 1. Check stop-loss first (immediate action)
    final_weights, stop_loss_triggered = stop_loss_logic(
        final_weights, daily_returns, stop_loss_threshold, defensive_asset=defensive_asset
    )
    risk_actions['stop_loss_triggered'] = stop_loss_triggered

    # 2. Apply drawdown protection
    if current_drawdown < drawdown_limit:
        final_weights = drawdown_protection(final_weights, current_drawdown, drawdown_limit)
        risk_actions['drawdown_protection_triggered'] = True

    # 3. Apply volatility targeting
    portfolio_vol = (final_weights * volatilities).sum()
    if portfolio_vol > target_vol * 1.1:  # Allow 10% tolerance
        final_weights = volatility_targeting(final_weights, portfolio_vol, target_vol)
        risk_actions['volatility_targeting_applied'] = True

    # Ensure weights sum to 1 and are non-negative
    final_weights = final_weights.clip(lower=0)
    if final_weights.sum() > 0:
        final_weights = final_weights / final_weights.sum()
    else:
        # Fallback to equal weight
        final_weights = pd.Series(1.0 / len(final_weights), index=final_weights.index)

    return final_weights, risk_actions


def correlation_spike_protection(weights: pd.Series,
                               corr_matrix: pd.DataFrame,
                               corr_threshold: float = 0.85) -> pd.Series:
    """Reduce exposure when correlations spike (flight to safety)."""
    avg_corr = corr_matrix.where(~np.eye(len(corr_matrix), dtype=bool)).mean().mean()
    if avg_corr > corr_threshold:
        factor = corr_threshold / avg_corr
        return weights * factor
    return weights
