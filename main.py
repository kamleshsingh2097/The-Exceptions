"""
Main entry point for the Risk Management & Regime Detection Engine
Options:
- Run the complete system demo
- Start the API server 
- Launch the Streamlit dashboard
"""

import sys
import subprocess
import argparse
from pathlib import Path

def print_banner():
    print("\n" + "="*80)
    print("🏦 RISK MANAGEMENT & REGIME DETECTION ENGINE")
    print("="*80)
    print("\nOptions:\n")
    print("1. python main.py --demo       → Run complete system demo")
    print("2. python main.py --api        → Start FastAPI server (port 8000)")
    print("3. python main.py --dashboard  → Launch Streamlit dashboard")
    print("4. python main.py --backtest   → Run backtester only")
    print("\n" + "="*80 + "\n")

def run_demo():
    """Run the complete system demonstration"""
    print("🚀 Running Complete System Demo...\n")
    subprocess.run([sys.executable, "complete_system_demo.py"], check=True)

def run_api():
    """Start the FastAPI server"""
    print("🌐 Starting FastAPI Server...\n")
    print("Server will be available at: http://localhost:8000")
    print("API Docs at: http://localhost:8000/docs\n")
    subprocess.run(
        [sys.executable, "-m", "uvicorn", "api_server:app", "--reload", "--port", "8000"],
        check=True
    )

def run_dashboard():
    """Launch the Streamlit dashboard"""
    print("📊 Launching Streamlit Dashboard...\n")
    print("Dashboard will open at: http://localhost:8501\n")
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", "app.py"],
        check=True
    )

def run_backtest():
    """Run backtest and show results"""
    print("🎯 Running Backtest...\n")
    from data_loader import load_prices
    from feature_engineering import rolling_features
    from backtester import run_backtest
    from metrics import compute_performance
    
    prices = load_prices(
        tickers=['AAPL', 'MSFT', 'GOOGL'],
        start_date='2023-01-01',
        end_date='2024-12-31'
    )
    features, _ = rolling_features(prices)
    results = run_backtest(prices, features)
    metrics = compute_performance(results['daily_returns'], results['equity_curve'])
    
    print("\n" + "="*60)
    print("BACKTEST RESULTS")
    print("="*60)
    print(f"CAGR:               {metrics['CAGR']:.2%}")
    print(f"Sharpe Ratio:       {metrics['Sharpe_Ratio']:.2f}")
    print(f"Max Drawdown:       {metrics['Max_Drawdown']:.2%}")
    print(f"Volatility:         {metrics['Annualized_Volatility']:.2%}")
    print(f"Sortino Ratio:      {metrics['Sortino_Ratio']:.2f}")
    print(f"Final Value:        ${results['equity_curve'].iloc[-1]:.2f}")
    print("="*60 + "\n")

def main():
    parser = argparse.ArgumentParser(
        description="Risk Management & Regime Detection Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --demo          Run complete system demonstration
  python main.py --api           Start FastAPI server
  python main.py --dashboard     Launch Streamlit dashboard
  python main.py --backtest      Run backtest and print results
        """
    )
    
    parser.add_argument(
        "--demo", 
        action="store_true",
        help="Run complete system demonstration"
    )
    parser.add_argument(
        "--api",
        action="store_true", 
        help="Start FastAPI server"
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Launch Streamlit dashboard"
    )
    parser.add_argument(
        "--backtest",
        action="store_true",
        help="Run backtest only and print results"
    )
    
    args = parser.parse_args()
    
    if not any([args.demo, args.api, args.dashboard, args.backtest]):
        print_banner()
        parser.print_help()
        return
    
    try:
        if args.demo:
            run_demo()
        elif args.api:
            run_api()
        elif args.dashboard:
            run_dashboard()
        elif args.backtest:
            run_backtest()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
