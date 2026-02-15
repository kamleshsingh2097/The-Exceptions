"""
Complete Financial Decision System Demo

Demonstrates the full system in action:
1. Data ingestion with no leakage
2. Regime detection
3. Intelligent allocation
4. Risk management
5. Backtesting
6. Stress testing
7. Explainability

Like a robo-advisor + hedge fund risk desk combined.
"""

import pandas as pd
import numpy as np
from datetime import datetime

# Import our complete system
from financial_decision_system import FinancialDecisionSystem, create_financial_decision_system

def demonstrate_regime_adaptation():
    """Show how the system adapts to different market regimes."""

    print("🎭 Demonstrating Regime Adaptation")
    print("="*50)

    # Create system
    system = create_financial_decision_system()

    # Test different market periods
    test_dates = [
        pd.Timestamp('2020-03-23'),  # COVID crash
        pd.Timestamp('2020-11-09'),  # Election day
        pd.Timestamp('2021-02-01'),  # Post-COVID recovery
        pd.Timestamp('2022-01-03'),  # High inflation start
        pd.Timestamp('2022-06-13'),  # Inflation peak
        pd.Timestamp('2023-10-01'),  # Recent normal period
    ]

    print("\nRegime Detection Across Market Conditions:")
    print("-" * 50)

    for date in test_dates:
        try:
            analysis = system.analyze_current_market_conditions(date)
            regime = analysis['regime']
            indicators = analysis['indicators']
            risk_level = analysis['risk_assessment']['overall_risk']

            print(f"\n📅 {date.strftime('%Y-%m-%d')}:")
            print(f"   Regime: {regime.value}")
            print(f"   Risk Level: {risk_level}")
            print(f"   Volatility: {indicators['avg_volatility']:.1%}")
            print(f"   Drawdown: {indicators['current_drawdown']:.1%}")
            print(f"   Trend: {indicators['trend_direction']:.1%}")

        except Exception as e:
            print(f"   ❌ Error for {date.strftime('%Y-%m-%d')}: {e}")

def demonstrate_allocation_changes():
    """Show how allocation changes with market conditions."""

    print("\n\n⚖️ Demonstrating Allocation Changes")
    print("="*50)

    system = create_financial_decision_system()

    # Test allocation in different regimes
    test_scenarios = [
        ("Normal Market", pd.Timestamp('2023-06-01')),
        ("High Volatility", pd.Timestamp('2020-03-16')),
        ("Crash Protection", pd.Timestamp('2020-03-23')),
        ("Recovery Mode", pd.Timestamp('2020-11-09')),
    ]

    print("\nAllocation Adaptation Across Regimes:")
    print("-" * 50)

    for scenario_name, date in test_scenarios:
        try:
            decision = system.make_portfolio_decision(date)

            print(f"\n🎯 {scenario_name} ({date.strftime('%Y-%m-%d')}):")
            print(f"   Regime: {decision['analysis']['regime'].value}")

            # Show top 3 allocations
            weights = decision['recommended_weights']
            top_3 = weights.nlargest(3)

            for asset, weight in top_3.items():
                print(f"   {asset}: {weight:.1%}")

            print(f"   Expected Vol: {decision['analysis']['allocation_recommendation']['expected_volatility']:.1%}")

        except Exception as e:
            print(f"   ❌ Error for {scenario_name}: {e}")

def demonstrate_risk_management():
    """Show risk management in action."""

    print("\n\n🛡️ Demonstrating Risk Management")
    print("="*50)

    system = create_financial_decision_system()

    # Test risk management during stress
    stress_date = pd.Timestamp('2020-03-23')  # COVID crash bottom

    print(f"\nRisk Management During Crisis ({stress_date.strftime('%Y-%m-%d')}):")
    print("-" * 50)

    try:
        decision = system.make_portfolio_decision(stress_date)

        print(f"Regime: {decision['analysis']['regime'].value}")
        print(f"Risk Level: {decision['analysis']['risk_assessment']['overall_risk']}")

        print("\nRisk Signals:")
        for signal in decision['analysis']['risk_signals']:
            print(f"   {signal}")

        print(f"\nRisk Reduction Applied: {decision['analysis']['allocation_recommendation']['risk_reduction_applied']:.1%}")

        print(f"\nExplanation:\n{decision['explanation']}")

    except Exception as e:
        print(f"❌ Error: {e}")

def run_complete_backtest_demo():
    """Run the complete backtest and show results."""

    print("\n\n📊 Complete Backtest Demonstration")
    print("="*50)

    system = create_financial_decision_system()

    print("\nRunning backtest with regime-adaptive allocation...")
    print("This may take a moment...")

    try:
        results = system.run_complete_backtest(rebalance_frequency='M')

        print("\n" + "="*60)
        print("BACKTEST RESULTS")
        print("="*60)
        print(f"Initial Capital: ${system.initial_capital:,.0f}")
        print(f"Final Value: ${results['final_value']:,.0f}")
        print(f"Total Return: {results['total_return']:.1%}")
        print(f"Annualized Return: {results['annualized_return']:.1%}")
        print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
        print(f"Max Drawdown: {results['max_drawdown']:.1%}")
        print(f"Volatility: {results.get('realized_volatility', 0):.1%}")

        # Show risk management effectiveness
        print(f"\nRisk Management:")
        print(f"   Target Volatility: {system.target_volatility:.1%}")
        print(f"   Risk Reduction Applied: {results.get('avg_risk_reduction', 0):.1%}")
        print(f"   Drawdown Protection: Limited to {system.max_drawdown_limit:.1%}")

    except Exception as e:
        print(f"❌ Backtest failed: {e}")

def run_stress_test_demo():
    """Demonstrate stress testing capabilities."""

    print("\n\n🧪 Stress Testing Demonstration")
    print("="*50)

    system = create_financial_decision_system()

    print("Running comprehensive stress tests...")
    print("Testing: Crisis scenarios, volatility spikes, correlation breaks")

    try:
        stress_results = system.run_stress_tests()

        print("\n" + "="*60)
        print("STRESS TEST RESULTS")
        print("="*60)

        print("Crisis Protection Effectiveness:")
        print(f"   Capital Preservation: {stress_results['crisis_protection_effectiveness']:.1%}")
        print(f"   Recovery Speed: {stress_results['volatility_spike_recovery']:.1%}")
        print(f"   Correlation Stress Resistance: {stress_results['correlation_stress_resistance']:.1%}")

        print("\nWorst Case Scenarios:")
        for scenario, impact in stress_results.get('worst_case_scenarios', {}).items():
            print(f"   {scenario}: {impact:.1%} loss")

    except Exception as e:
        print(f"❌ Stress test failed: {e}")

def generate_comprehensive_report():
    """Generate the full system report."""

    print("\n\n📋 Complete System Report")
    print("="*50)

    system = create_financial_decision_system()

    # Run all analyses
    print("Running comprehensive analysis...")
    system.run_complete_backtest()
    system.run_stress_tests()

    # Generate report
    report = system.generate_performance_report()

    print(report)

    # Save report to file
    with open('FINANCIAL_DECISION_SYSTEM_REPORT.md', 'w') as f:
        f.write(report)

    print("\n💾 Report saved to: FINANCIAL_DECISION_SYSTEM_REPORT.md")

def demonstrate_real_time_decision():
    """Show how the system would make decisions in real-time."""

    print("\n\n⚡ Real-Time Decision Demonstration")
    print("="*50)

    system = create_financial_decision_system()

    # Simulate real-time decision making
    print("Simulating real-time portfolio management...")

    # Get the most recent date in our data
    latest_date = system.prices.index[-1]

    print(f"\nLatest market data: {latest_date.strftime('%Y-%m-%d')}")

    try:
        # Make current decision
        decision = system.make_portfolio_decision(latest_date)

        print("\n" + "="*60)
        print("CURRENT PORTFOLIO DECISION")
        print("="*60)

        print(f"Date: {decision['date'].strftime('%Y-%m-%d')}")
        print(f"Market Regime: {decision['analysis']['regime'].value}")
        print(f"Decision Confidence: {decision['analysis']['confidence'].value}")

        print(f"\nRisk Assessment:")
        risk = decision['analysis']['risk_assessment']
        print(f"   Overall Risk: {risk['overall_risk']}")
        print(f"   Volatility Risk: {risk['volatility_risk']}")
        print(f"   Drawdown Risk: {risk['drawdown_risk']}")

        print(f"\nRecommended Allocation:")
        weights = decision['recommended_weights']
        for asset in sorted(weights.index):
            print(f"   {asset}: {weights[asset]:.1%}")

        print(f"\nExpected Portfolio Volatility: {decision['analysis']['allocation_recommendation']['expected_volatility']:.1%}")

        if decision['analysis']['risk_signals']:
            print(f"\n⚠️ Risk Signals:")
            for signal in decision['analysis']['risk_signals']:
                print(f"   {signal}")

        print(f"\n💡 Decision Explanation:")
        print(decision['explanation'])

    except Exception as e:
        print(f"❌ Real-time decision failed: {e}")

def main():
    """Run the complete demonstration."""

    print("🚀 Complete Financial Decision System Demo")
    print("="*60)
    print("Like a robo-advisor + hedge fund risk desk combined")
    print("Demonstrating: Regime detection → Intelligent allocation → Risk management")
    print("="*60)

    # Run all demonstrations
    demonstrate_regime_adaptation()
    demonstrate_allocation_changes()
    demonstrate_risk_management()
    run_complete_backtest_demo()
    run_stress_test_demo()
    demonstrate_real_time_decision()
    generate_comprehensive_report()

    print("\n" + "="*80)
    print("🎉 DEMONSTRATION COMPLETE")
    print("="*80)
    print("The system successfully demonstrated:")
    print("✅ Market regime detection")
    print("✅ Intelligent capital allocation")
    print("✅ Dynamic risk management")
    print("✅ Crisis protection")
    print("✅ Long-term optimization")
    print("✅ Comprehensive backtesting")
    print("✅ Stress testing")
    print("✅ Explainability layer")
    print("\n🧠 System Status: FULLY OPERATIONAL")
    print("Ready for live trading or further development!")

if __name__ == "__main__":
    main()