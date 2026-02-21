"""
FastAPI Server for Risk Management & Regime Detection Engine
Exposes endpoints for backtesting, stress testing, and regime analysis
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "Backend Running"}
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uuid
import traceback
import pandas as pd
import numpy as np
import logging
import uvicorn
# imports refer to backend package when running via uvicorn from workspace root
from .utils import read_selected_ticker
from .tickers import tickers as TICKERS
from .data_loader import load_prices
from .feature_engineering import rolling_features
from .backtester import run_backtest
from .stress_test import run_comprehensive_stress_test
from .metrics import compute_performance
from .regime_detection import RegimeDetector
# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Risk Management & Regime Detection Engine",
    description="Advanced portfolio backtesting with regime detection and risk controls",
    version="1.0"
)

# In-memory store for background stress test tasks
# Auto-cleanup: keep only last 100 tasks
stress_tasks: Dict[str, Dict[str, Any]] = {}
MAX_STRESS_TASKS = 100

def get_effective_tickers(default_count: int = 3):
    """Return the user-selected ticker (as a single-item list) or a sensible default.

    Prefers the persisted selection written by the Streamlit app. Falls back
    to the first `default_count` tickers defined in `tickers.py`.
    """
    sel = read_selected_ticker()
    if sel:
        return [sel]
    try:
        return TICKERS[:default_count]
    except Exception:
        return ['AAPL', 'MSFT', 'GOOGL']

def sanitize(obj):
    # pandas DataFrame
    if isinstance(obj, pd.DataFrame):
        return {
            "columns": obj.columns.tolist(),
            "index": [str(i) for i in obj.index.tolist()],
            "data": obj.to_dict(orient="list")
        }
    # pandas Series
    if isinstance(obj, pd.Series):
        return obj.tolist()
    # numpy scalar
    if isinstance(obj, (np.generic,)):
        try:
            return obj.item()
        except Exception:
            return float(obj)
    # dict/list - recurse
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(v) for v in obj]
    return obj

# Request/Response Models
class BacktestRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    target_vol: float = 0.08
    drawdown_limit: float = -0.15
    transaction_costs: float = 0.001

class BacktestResponse(BaseModel):
    status: str
    metrics: Dict[str, float]
    max_drawdown: float
    sharpe_ratio: float
    cagr: float
    final_value: float
    equity_curve: Optional[List[float]] = None
    daily_returns: Optional[List[float]] = None
    dates: Optional[List[str]] = None

class RegimeAnalysisRequest(BaseModel):
    analysis_date: Optional[str] = None

class RegimeAnalysisResponse(BaseModel):
    current_regime: str
    volatility: float
    trend_strength: float
    drawdown: float
    recommendations: Dict[str, Any]

@app.on_event("startup")
async def startup_event():
    logger.info("Risk Management Engine API Started")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Risk Management & Regime Detection Engine",
        "version": "1.0"
    }

@app.get("/data-range")
async def get_data_range():
    """Get available date range for backtesting"""
    try:
        # Load sample data to determine available date range
        prices = load_prices(
            tickers=get_effective_tickers(),
            start_date='2020-01-01',
            end_date='2030-12-31'
        )
        
        if prices.empty:
            return {
                "status": "no_data",
                "message": "No price data available"
            }
        
        return {
            "status": "success",
            "start_date": prices.index[0].strftime('%Y-%m-%d'),
            "end_date": prices.index[-1].strftime('%Y-%m-%d'),
            "total_trading_days": len(prices),
            "message": f"Data available from {prices.index[0].strftime('%Y-%m-%d')} to {prices.index[-1].strftime('%Y-%m-%d')}"
        }
    except Exception as e:
        logger.error(f"Data range error: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

@app.post("/backtest", response_model=BacktestResponse)
async def run_portfolio_backtest(request: BacktestRequest):
    """
    Run portfolio backtest with risk management
    """
    try:
        logger.info("Starting backtest...")
        
        # Determine date range from request (fallback to sensible defaults)
        start_date = request.start_date or '2023-01-01'
        end_date = request.end_date or '2024-12-31'

        # Load market data
        prices = load_prices(
            tickers=get_effective_tickers(),
            start_date=start_date,
            end_date=end_date
        )
        features, _ = rolling_features(prices)
        
        # Run backtest
        results = run_backtest(
            prices, features,
            target_vol=request.target_vol,
            drawdown_limit=request.drawdown_limit,
            defensive_asset='DEFENSIVE',
            transaction_costs=request.transaction_costs
        )
        
        # Calculate metrics
        metrics = compute_performance(results['daily_returns'], results['equity_curve'])
        
        logger.info(f"Backtest complete - Sharpe: {metrics['Sharpe_Ratio']:.2f}")
        
        # Sanitize series to primitive lists for JSON transport
        equity_list = results['equity_curve'].tolist() if 'equity_curve' in results else None
        returns_list = results['daily_returns'].tolist() if 'daily_returns' in results else None
        dates_list = [str(d) for d in results['equity_curve'].index.tolist()] if 'equity_curve' in results else None

        return BacktestResponse(
            status="success",
            metrics={k: float(v) for k, v in metrics.items()},
            max_drawdown=float(metrics['Max_Drawdown']),
            sharpe_ratio=float(metrics['Sharpe_Ratio']),
            cagr=float(metrics['CAGR']),
            final_value=float(results['equity_curve'].iloc[-1]),
            equity_curve=equity_list,
            daily_returns=returns_list,
            dates=dates_list
        )
    except Exception as e:
        logger.error(f"Backtest error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stress-test")
async def stress_test_portfolio(background_tasks: BackgroundTasks, 
                                 start_date: Optional[str] = None,
                                 end_date: Optional[str] = None):
    """
    Run comprehensive stress test with crisis scenarios
    Accepts optional date range, defaults to wide historical range
    """
    try:
        logger.info("Scheduling background stress test task")
        
        # Use provided dates or defaults
        test_start = start_date or '2020-01-01'
        test_end = end_date or '2024-12-31'
        
        logger.info(f"Stress test parameters: dates={test_start} to {test_end}")

        # create a task id and register initial status
        task_id = uuid.uuid4().hex
        stress_tasks[task_id] = {"status": "running", "result": None, "created_at": str(pd.Timestamp.now())}
        
        # Cleanup old tasks if too many
        if len(stress_tasks) > MAX_STRESS_TASKS:
            oldest_key = min(stress_tasks.keys(), key=lambda k: stress_tasks[k].get('created_at', ''))
            del stress_tasks[oldest_key]
            logger.info(f"Cleaned up old stress test task: {oldest_key}")

        # Background worker that loads data, runs the stress test and stores sanitized result
        def run_and_store(tid: str, target_vol: float, drawdown_limit: float, defensive_asset: str, dt_start: str, dt_end: str):
            try:
                logger.info(f"Background task {tid} started with dates {dt_start} to {dt_end}")
                # Use provided date range for stress tests
                prices = load_prices(
                    tickers=get_effective_tickers(),
                    start_date=dt_start,
                    end_date=dt_end
                )
                features, _ = rolling_features(prices)

                results = run_comprehensive_stress_test(
                    prices, features,
                    target_vol=target_vol,
                    drawdown_limit=drawdown_limit,
                    defensive_asset=defensive_asset
                )

                payload = {
                    "status": "success",
                    "base": results.get('base'),
                    "crisis": results.get('crisis'),
                    "volatility": results.get('volatility'),
                    "correlation": results.get('correlation'),
                    "risk_engine_analysis": results.get('risk_engine_analysis')
                }

                stress_tasks[tid]["status"] = "completed"
                stress_tasks[tid]["result"] = sanitize(payload)
                logger.info(f"Background task {tid} completed")
            except Exception:
                tb = traceback.format_exc()
                logger.exception(f"Background task {tid} failed: {tb}")
                stress_tasks[tid]["status"] = "failed"
                stress_tasks[tid]["result"] = {"error": str(tb)}

        # schedule background task with provided dates
        background_tasks.add_task(run_and_store, task_id, 0.08, -0.15, 'DEFENSIVE', test_start, test_end)

        return JSONResponse(content=jsonable_encoder({"status": "started", "task_id": task_id}))
    except Exception as e:
        logger.exception("Stress test error")
        tb = traceback.format_exc()
        return JSONResponse(status_code=500, content=jsonable_encoder({
            "status": "error",
            "error": str(e),
            "traceback": tb
        }))

@app.post("/regime-analysis", response_model=RegimeAnalysisResponse)
async def analyze_regime(request: RegimeAnalysisRequest):
    """
    Analyze current market regime for a given date.
    Uses available historical data up to the analysis date.
    """
    try:
        logger.info("Analyzing market regime...")
        
        # Parse analysis date
        analysis_date = request.analysis_date or '2024-12-31'
        try:
            analysis_dt = pd.to_datetime(analysis_date)
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid date format: {analysis_date}. Use YYYY-MM-DD")
        
        # Try to load data - start with a wide range to find what's available
        # Go back 2 years to have plenty of historical data
        from datetime import timedelta
        start_dt = analysis_dt - timedelta(days=730)
        start_date = start_dt.strftime('%Y-%m-%d')
        end_date = analysis_dt.strftime('%Y-%m-%d')
        
        logger.info(f"Attempting to load regime data from {start_date} to {end_date}")
        
        # Load data - this will get whatever data is available
        prices = load_prices(
            tickers=get_effective_tickers(),
            start_date=start_date,
            end_date=end_date
        )
        
        # Validate we have sufficient data
        if prices.empty:
            raise HTTPException(
                status_code=400, 
                detail=f"No price data available for {end_date}. Try dates between 2023-01-01 and available market dates."
            )
        
        if len(prices) < 30:  # Need minimum 30 trading days
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient data for regime analysis. Got {len(prices)} trading days, need at least 30. Try dates closer to available data."
            )
        
        logger.info(f"Loaded {len(prices)} trading days. Analysis date {end_date}, data range: {prices.index[0].strftime('%Y-%m-%d')} to {prices.index[-1].strftime('%Y-%m-%d')}")
        
        features, _ = rolling_features(prices)
        
        detector = RegimeDetector()
        regime, indicators = detector.detect_regime_comprehensive(
            prices, features, prices.index[-1]
        )
        
        characteristics = detector.get_regime_characteristics(regime)
        
        logger.info(f"Regime detected: {regime.value}, strength {indicators.get('trend_strength', 0.0):.3f}")
        
        return RegimeAnalysisResponse(
            current_regime=regime.value,
            volatility=float(indicators.get('avg_volatility', 0.0)),
            # previously returned trend_direction by mistake; clients expect trend_strength
            trend_strength=float(indicators.get('trend_strength', 0.0)),
            drawdown=float(indicators.get('drawdown', 0.0)),
            recommendations=characteristics
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Regime analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/metrics")
async def get_last_metrics():
    """Get last computed performance metrics"""
    try:
        prices = load_prices(
            tickers=get_effective_tickers(),
            start_date='2023-01-01',
            end_date='2024-12-31'
        )
        features, _ = rolling_features(prices)
        results = run_backtest(prices, features)
        metrics = compute_performance(results['daily_returns'], results['equity_curve'])
        
        return {
            "status": "success",
            "metrics": {k: float(v) for k, v in metrics.items()}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stress-test/{task_id}")
async def get_stress_test_status(task_id: str):
    """Retrieve status/result for background stress test task"""
    task = stress_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return JSONResponse(content=jsonable_encoder(task))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")