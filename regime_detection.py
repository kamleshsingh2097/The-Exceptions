"""Advanced Regime Detection System

Detects market states like:
- Trending Up: Strong upward momentum with low volatility
- Trending Down: Strong downward momentum with low volatility
- High Volatility: Elevated volatility regardless of trend
- Crash: Severe drawdown with high volatility

Uses multiple indicators including volatility thresholds for robust detection.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from enum import Enum


class MarketRegime(Enum):
    """Market regime classifications."""
    TRENDING_UP = "Trending Up"
    TRENDING_DOWN = "Trending Down"
    HIGH_VOLATILITY = "High Volatility"
    CRASH = "Crash"
    NORMAL = "Normal"


class RegimeDetector:
    """Advanced market regime detection system."""

    def __init__(self,
                 vol_threshold_high: float = 0.08,  # 8% annualized volatility = high
                 vol_threshold_crash: float = 0.15,  # 15% = crash level
                 drawdown_crash_threshold: float = -0.12,  # -12% drawdown = crash
                 trend_strength_threshold: float = 0.02,  # 2% monthly trend = strong
                 lookback_periods: int = 20):  # 20 days for trend analysis

        self.vol_threshold_high = vol_threshold_high
        self.vol_threshold_crash = vol_threshold_crash
        self.drawdown_crash_threshold = drawdown_crash_threshold
        self.trend_strength_threshold = trend_strength_threshold
        self.lookback_periods = lookback_periods

    def detect_regime_comprehensive(self,
                                   prices: pd.DataFrame,
                                   features: pd.DataFrame,
                                   current_date: pd.Timestamp) -> Tuple[MarketRegime, Dict[str, float]]:
        """Comprehensive regime detection using multiple indicators.

        Parameters:
        - prices: Historical price data up to current_date
        - features: Feature DataFrame with technical indicators
        - current_date: Date for which to detect regime

        Returns:
        - Tuple of (detected_regime, regime_indicators_dict)
        """

        # Extract current market indicators
        indicators = self._calculate_regime_indicators(prices, features, current_date)

        # Apply regime detection logic in priority order
        regime = self._classify_regime(indicators)

        return regime, indicators

    def _calculate_regime_indicators(self,
                                    prices: pd.DataFrame,
                                    features: pd.DataFrame,
                                    current_date: pd.Timestamp) -> Dict[str, float]:
        """Calculate all regime detection indicators."""

        indicators = {}

        # Get data up to current date
        if current_date not in prices.index:
            # Fallback to most recent data
            current_date = prices.index[-1]

        recent_prices = prices.loc[:current_date]
        recent_features = features.loc[:current_date] if not features.empty else pd.DataFrame()

        # 1. Volatility indicators
        indicators['avg_volatility'] = self._calculate_average_volatility(recent_prices)
        indicators['max_volatility'] = self._calculate_max_volatility(recent_features, current_date)

        # 2. Trend indicators
        indicators['trend_strength'] = self._calculate_trend_strength(recent_prices)
        indicators['trend_direction'] = self._calculate_trend_direction(recent_prices)

        # 3. Drawdown indicators
        indicators['max_drawdown'] = self._calculate_max_drawdown(recent_prices)
        indicators['current_drawdown'] = self._calculate_current_drawdown(recent_prices)

        # 4. Momentum indicators
        indicators['momentum_score'] = self._calculate_momentum_score(recent_prices)

        # 5. Market breadth
        indicators['market_breadth'] = self._calculate_market_breadth(recent_features, current_date)

        return indicators

    def _calculate_average_volatility(self, prices: pd.DataFrame) -> float:
        """Calculate average annualized volatility across assets."""
        if len(prices) < 10:
            return 0.05  # Default 5%

        returns = prices.pct_change().dropna()
        if returns.empty:
            return 0.05

        # Calculate volatility for each asset
        volatilities = []
        for col in returns.columns:
            vol = returns[col].std() * np.sqrt(252)  # Annualized
            if not np.isnan(vol):
                volatilities.append(vol)

        return np.mean(volatilities) if volatilities else 0.05

    def _calculate_max_volatility(self, features: pd.DataFrame, current_date: pd.Timestamp) -> float:
        """Get maximum volatility from features."""
        if features.empty or current_date not in features.index:
            return 0.05

        vol_values = []
        for col in features.columns:
            if col[0] == 'vol_30' and not pd.isna(features.loc[current_date, col]):
                vol_values.append(features.loc[current_date, col])

        return max(vol_values) if vol_values else 0.05

    def _calculate_trend_strength(self, prices: pd.DataFrame) -> float:
        """Calculate trend strength using linear regression slope."""
        if len(prices) < self.lookback_periods:
            return 0.0

        recent_prices = prices.tail(self.lookback_periods)
        avg_prices = recent_prices.mean(axis=1)

        # Linear regression to find trend
        x = np.arange(len(avg_prices))
        y = avg_prices.values

        if len(x) < 2:
            return 0.0

        slope, _ = np.polyfit(x, y, 1)

        # Normalize by average price to get relative trend strength
        avg_price = np.mean(y)
        trend_strength = slope / avg_price if avg_price > 0 else 0.0

        # Annualize the daily trend
        return trend_strength * 252

    def _calculate_trend_direction(self, prices: pd.DataFrame) -> float:
        """Calculate trend direction (-1 to +1, negative = down, positive = up)."""
        if len(prices) < self.lookback_periods:
            return 0.0

        recent_prices = prices.tail(self.lookback_periods)
        start_price = recent_prices.iloc[0].mean()
        end_price = recent_prices.iloc[-1].mean()

        if start_price == 0:
            return 0.0

        return (end_price - start_price) / start_price

    def _calculate_max_drawdown(self, prices: pd.DataFrame) -> float:
        """Calculate maximum drawdown from peak."""
        if len(prices) < 10:
            return 0.0

        avg_prices = prices.mean(axis=1)
        peak = avg_prices.expanding().max()
        drawdown = (avg_prices - peak) / peak

        return drawdown.min()

    def _calculate_current_drawdown(self, prices: pd.DataFrame) -> float:
        """Calculate current drawdown from recent peak."""
        if len(prices) < 10:
            return 0.0

        avg_prices = prices.mean(axis=1)
        peak = avg_prices.expanding().max()

        return (avg_prices.iloc[-1] - peak.iloc[-1]) / peak.iloc[-1]

    def _calculate_momentum_score(self, prices: pd.DataFrame) -> float:
        """Calculate momentum score using rate of change."""
        if len(prices) < 20:
            return 0.0

        # Compare recent performance vs longer-term
        short_term = prices.tail(5).mean(axis=1)
        long_term = prices.tail(20).mean(axis=1)

        short_return = (short_term.iloc[-1] - short_term.iloc[0]) / short_term.iloc[0]
        long_return = (long_term.iloc[-1] - long_term.iloc[0]) / long_term.iloc[0]

        # Momentum = short-term performance relative to long-term
        return short_return - long_return

    def _calculate_market_breadth(self, features: pd.DataFrame, current_date: pd.Timestamp) -> float:
        """Calculate market breadth (fraction of assets above MA200)."""
        if features.empty or current_date not in features.index:
            return 0.5  # Neutral

        above_ma_count = 0
        total_count = 0

        for col in features.columns:
            if col[0] == 'ma200':
                total_count += 1
                if not pd.isna(features.loc[current_date, col]) and features.loc[current_date, col] > 0:
                    # This is a simplified check - in real implementation you'd compare price to MA
                    above_ma_count += 1

        return above_ma_count / total_count if total_count > 0 else 0.5

    def _classify_regime(self, indicators: Dict[str, float]) -> MarketRegime:
        """Classify market regime based on indicators in priority order."""

        # Priority 1: CRASH - Most severe condition
        if (indicators['max_drawdown'] < self.drawdown_crash_threshold or
            indicators['current_drawdown'] < self.drawdown_crash_threshold * 0.8):
            return MarketRegime.CRASH

        # Priority 2: HIGH VOLATILITY - Check volatility thresholds
        if (indicators['avg_volatility'] > self.vol_threshold_crash or
            indicators['max_volatility'] > self.vol_threshold_crash):
            return MarketRegime.CRASH  # Very high vol = crash regime

        if (indicators['avg_volatility'] > self.vol_threshold_high or
            indicators['max_volatility'] > self.vol_threshold_high):
            return MarketRegime.HIGH_VOLATILITY

        # Priority 3: TRENDING REGIMES - Check trend strength and direction
        if abs(indicators['trend_strength']) > self.trend_strength_threshold:
            if indicators['trend_direction'] > 0:
                return MarketRegime.TRENDING_UP
            else:
                return MarketRegime.TRENDING_DOWN

        # Priority 4: NORMAL - Default state
        return MarketRegime.NORMAL

    def get_regime_characteristics(self, regime: MarketRegime) -> Dict[str, any]:
        """Get characteristics and recommended actions for each regime."""

        characteristics = {
            MarketRegime.TRENDING_UP: {
                'description': 'Strong upward momentum with controlled volatility',
                'volatility': 'Low to Moderate',
                'risk_level': 'Low',
                'recommended_action': 'Increase equity exposure, momentum strategies',
                'position_sizing': 'Aggressive (60-80% equities)',
                'defensive_allocation': 'Low (0-20%)'
            },
            MarketRegime.TRENDING_DOWN: {
                'description': 'Strong downward momentum with controlled volatility',
                'volatility': 'Low to Moderate',
                'risk_level': 'High',
                'recommended_action': 'Reduce equity exposure, increase defensive positions',
                'position_sizing': 'Conservative (20-40% equities)',
                'defensive_allocation': 'High (60-80%)'
            },
            MarketRegime.HIGH_VOLATILITY: {
                'description': 'Elevated volatility regardless of trend direction',
                'volatility': 'High',
                'risk_level': 'Medium-High',
                'recommended_action': 'Reduce position sizes, use options for hedging',
                'position_sizing': 'Moderate (40-60% equities)',
                'defensive_allocation': 'Medium (30-50%)'
            },
            MarketRegime.CRASH: {
                'description': 'Severe market decline with high volatility',
                'volatility': 'Very High',
                'risk_level': 'Very High',
                'recommended_action': 'Heavy risk reduction, move to cash/defensive',
                'position_sizing': 'Very Conservative (0-20% equities)',
                'defensive_allocation': 'Very High (80-100%)'
            },
            MarketRegime.NORMAL: {
                'description': 'Typical market conditions, no strong trends',
                'volatility': 'Moderate',
                'risk_level': 'Medium',
                'recommended_action': 'Balanced approach, risk parity allocation',
                'position_sizing': 'Balanced (40-60% equities)',
                'defensive_allocation': 'Medium (30-50%)'
            }
        }

        return characteristics.get(regime, characteristics[MarketRegime.NORMAL])


def detect_regime_realtime_enhanced(prices: pd.DataFrame,
                                   features: pd.DataFrame,
                                   vol_threshold: float = 0.08) -> str:
    """Enhanced real-time regime detection for backtesting compatibility.

    Returns string regime name for backward compatibility with existing code.
    """

    detector = RegimeDetector(vol_threshold_high=vol_threshold)
    current_date = prices.index[-1] if not prices.empty else pd.Timestamp.now()

    try:
        regime, indicators = detector.detect_regime_comprehensive(prices, features, current_date)

        # Convert enum to string for compatibility
        regime_name = regime.value

        # Print regime detection details
        print(f"🎯 REGIME DETECTED: {regime_name}")
        print(f"   Volatility: {indicators['avg_volatility']:.3f}")
        print(f"   Trend Strength: {indicators['trend_strength']:.1%}")
        print(f"   Current Drawdown: {indicators['current_drawdown']:.1%}")
        print(f"   Momentum Score: {indicators['momentum_score']:.4f}")
        # Show recommended actions
        characteristics = detector.get_regime_characteristics(regime)
        print(f"   Recommended: {characteristics['recommended_action']}")

        return regime_name

    except Exception as e:
        print(f"⚠️  Regime detection error: {e}, defaulting to Normal")
        return "Normal"


# Backward compatibility function
def detect_regime_realtime(prices: pd.DataFrame, features: pd.DataFrame, vol_threshold: float = 0.05) -> str:
    """Legacy function for backward compatibility."""
    return detect_regime_realtime_enhanced(prices, features, vol_threshold)


def detect_regime(prices: pd.DataFrame, features: pd.DataFrame, vol_threshold: float = 0.08) -> pd.Series:
    """Enhanced batch regime detection for historical analysis.

    Returns a Series with regime classifications for each date.
    """
    dates = prices.index
    regimes = pd.Series(index=dates, dtype=object)

    detector = RegimeDetector(vol_threshold_high=vol_threshold)

    for i, date in enumerate(dates):
        try:
            # Use data up to current date for regime detection
            current_prices = prices.loc[:date]
            current_features = features.loc[:date] if not features.empty else pd.DataFrame()

            regime, _ = detector.detect_regime_comprehensive(current_prices, current_features, date)
            regimes.loc[date] = regime.value

        except Exception as e:
            regimes.loc[date] = "Normal"

    return regimes
