"""
Automated Trading Engine
Executes trades based on regime detection and risk management signals
"""

import logging
from typing import Dict, Optional
from datetime import datetime
import pandas as pd
from regime_detection import RegimeDetector, MarketRegime
from allocation import adjust_for_regime
from risk_engine import comprehensive_risk_management

logger = logging.getLogger(__name__)

class AutoTrader:
    """Automated trading system based on regime and risk signals"""
    
    def __init__(self, portfolio_value: float = 100000):
        self.portfolio_value = portfolio_value
        self.positions = {}
        self.regime_detector = RegimeDetector()
        self.trade_log = []
        
    def update_regime(self, prices: pd.DataFrame, features: pd.DataFrame) -> str:
        """Detect current market regime"""
        regime, indicators = self.regime_detector.detect_regime_comprehensive(
            prices, features, prices.index[-1]
        )
        
        logger.info(f"📊 Regime: {regime.value} | Vol: {indicators['avg_volatility']:.1%}")
        return regime.value
    
    def compute_allocation(self, regime: str, current_prices: pd.Series) -> Dict[str, float]:
        """Compute portfolio allocation based on regime"""
        allocation = adjust_for_regime(regime)
        
        logger.info(f"📍 Allocation - Equity: {allocation.get('EQUITY', 0):.0%}, Defensive: {allocation.get('DEFENSIVE', 0):.0%}, Cash: {allocation.get('CASH', 0):.0%}")
        return allocation
    
    def apply_risk_management(self, allocation: Dict[str, float], prices: pd.DataFrame) -> Dict[str, float]:
        """Apply risk management overlays"""
        # Apply comprehensive risk management
        adjusted = comprehensive_risk_management(
            allocation, 
            prices,
            target_vol=0.08,
            drawdown_limit=-0.15
        )
        return adjusted
    
    def execute_trades(self, target_allocation: Dict[str, float], prices: pd.Series):
        """Execute trades to reach target allocation"""
        for asset, target_weight in target_allocation.items():
            current_weight = self.positions.get(asset, 0)
            
            if abs(target_weight - current_weight) > 0.01:  # Trade if >1% difference
                trade_amount = (target_weight - current_weight) * self.portfolio_value
                side = "BUY" if trade_amount > 0 else "SELL"
                
                logger.info(f"  {side:4} {asset:10} @ ${prices.get(asset, 0):.2f} | Amount: ${abs(trade_amount):,.0f}")
                
                self.positions[asset] = target_weight
                self.trade_log.append({
                    'timestamp': datetime.now(),
                    'asset': asset,
                    'side': side,
                    'amount': abs(trade_amount),
                    'price': prices.get(asset, 0)
                })
    
    def run_daily_cycle(self, prices: pd.DataFrame, features: pd.DataFrame):
        """Run full daily trading cycle"""
        logger.info(f"\n{'='*60}")
        logger.info(f"🤖 AUTOMATED TRADING CYCLE - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        logger.info(f"{'='*60}\n")
        
        # 1. Detect regime
        regime = self.update_regime(prices, features)
        
        # 2. Compute base allocation
        allocation = self.compute_allocation(regime, prices.iloc[-1])
        
        # 3. Apply risk management
        final_allocation = self.apply_risk_management(allocation, prices)
        
        # 4. Execute trades
        self.execute_trades(final_allocation, prices.iloc[-1])
        
        logger.info(f"\n{'='*60}\n")

class AutoTradeConfig:
    """Configuration for automated trading"""
    def __init__(self):
        self.target_volatility = 0.08
        self.drawdown_limit = -0.15
        self.transaction_costs = 0.001
        self.rebalance_frequency = "daily"  # daily, weekly, monthly

# Global auto trader instance
auto_trader = None

def initialize_trader(portfolio_value: float = 100000) -> AutoTrader:
    """Initialize global auto trader"""
    global auto_trader
    auto_trader = AutoTrader(portfolio_value)
    logger.info(f"✅ AutoTrader initialized with ${portfolio_value:,.0f}")
    return auto_trader

def get_trader() -> Optional[AutoTrader]:
    """Get global auto trader instance"""
    return auto_trader
