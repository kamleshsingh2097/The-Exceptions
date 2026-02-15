"""
FastAPI Server for Risk Management & Regime Detection Engine
Exposes endpoints for backtesting, stress testing, and regime analysis
"""

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

from data_loader import load_prices
from feature_engineering import rolling_features
from backtester import run_backtest
from stress_test import run_comprehensive_stress_test
from metrics import compute_performance
from regime_detection import RegimeDetector

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Risk Management & Regime Detection Engine",
    description="Advanced portfolio backtesting with regime detection and risk controls",
    version="1.0"
)

# In-memory store for background stress test tasks
stress_tasks: Dict[str, Dict[str, Any]] = {}


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

@app.post("/backtest", response_model=BacktestResponse)
async def run_portfolio_backtest(request: BacktestRequest):
    """
    Run portfolio backtest with risk management
    """
    try:
        logger.info("Starting backtest...")
        
        # Load market data
        prices = load_prices(
            tickers=['AAPL', 'MSFT', 'GOOGL'],
            start_date='2023-01-01',
            end_date='2024-12-31'
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
async def stress_test_portfolio(background_tasks: BackgroundTasks):
    """
    Run comprehensive stress test with crisis scenarios
    """
    try:
        logger.info("Scheduling background stress test task")

        # create a task id and register initial status
        task_id = uuid.uuid4().hex
        stress_tasks[task_id] = {"status": "running", "result": None}

        # Background worker that loads data, runs the stress test and stores sanitized result
        def run_and_store(tid: str, target_vol: float, drawdown_limit: float, defensive_asset: str):
            try:
                logger.info(f"Background task {tid} started")
                prices = load_prices(
                    tickers=['AAPL', 'MSFT', 'GOOGL'],
                    start_date='2023-01-01',
                    end_date='2024-12-31'
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

        # schedule background task
        background_tasks.add_task(run_and_store, task_id, 0.08, -0.15, 'DEFENSIVE')

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
    Analyze current market regime
    """
    try:
        logger.info("Analyzing market regime...")
        
        prices = load_prices(
            tickers=['AAPL', 'MSFT', 'GOOGL'],
            start_date='2023-01-01',
            end_date='2024-12-31'
        )
        features, _ = rolling_features(prices)
        
        detector = RegimeDetector()
        regime, indicators = detector.detect_regime_comprehensive(
            prices, features, prices.index[-1]
        )
        
        characteristics = detector.get_regime_characteristics(regime)
        
        logger.info(f"Regime detected: {regime.value}")
        
        return RegimeAnalysisResponse(
            current_regime=regime.value,
            volatility=float(indicators.get('avg_volatility', 0.0)),
            trend_strength=float(indicators.get('trend_direction', 0.0)),
            drawdown=float(indicators.get('drawdown', 0.0)),
            recommendations=characteristics
        )
    except Exception as e:
        logger.error(f"Regime analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def get_last_metrics():
    """Get last computed performance metrics"""
    try:
        prices = load_prices(
            tickers=['AAPL', 'MSFT', 'GOOGL'],
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
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
