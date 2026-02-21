"""
Streamlit UI for Risk Management & Regime Detection Engine
Interactive dashboard for backtesting, analysis, and stress testing
CONNECTED TO BACKEND VIA REST API
"""

# when the UI lives in a subfolder we need the workspace root on PYTHONPATH
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from backend.tickers import tickers
from backend.utils import write_selected_ticker, read_selected_ticker
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import logging
import requests
from typing import Dict, Any

# API Configuration
API_BASE_URL = "https://the-exceptions.onrender.com"

def call_api(endpoint: str, method: str = "GET", data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Helper function to call API endpoints - always fetches fresh data"""
    url = f"{API_BASE_URL}/{endpoint}"

    try:
        if method == "POST":
            response = requests.post(url, json=data, timeout=120)
        else:
            response = requests.get(url, timeout=30)

        if response.status_code != 200:
            st.error(f"API Error (Status {response.status_code}): {response.text[:500]}")
            return None
        
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to API server. Is it running?")
        st.code("Start with: python api_server.py")
        return None
    except requests.exceptions.Timeout:
        st.error("❌ API request timed out. Check server performance.")
        return None
    except Exception as e:
        st.error(f"❌ API Error: {str(e)}")
        return None


def build_dates(result, start, end):
    """Return a pandas.DatetimeIndex for plotting from API result.

    Priority:
    1. Use `result['dates']` if present and parseable.
    2. Fall back to generating a date_range between `start` and `end` matching the equity length.
    Returns `None` on failure.
    """
    if not result:
        return None
    if "dates" in result and isinstance(result["dates"], list):
        try:
            return pd.to_datetime(result["dates"])
        except Exception:
            pass
    # fallback: create range between start and end matching length
    series = result.get('equity_curve') or []
    try:
        dates = pd.date_range(start=pd.to_datetime(start), end=pd.to_datetime(end), periods=len(series))
        return dates
    except Exception:
        return None

# Configure page
st.set_page_config(
    page_title="Trading Engine Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state for global date range
if 'global_start_date' not in st.session_state:
    st.session_state['global_start_date'] = pd.to_datetime("2023-01-01")
if 'global_end_date' not in st.session_state:
    st.session_state['global_end_date'] = pd.to_datetime("2024-12-31")

# --- UI Styling ---
_STYLE = '''
<style>
:root{
    --bg-grad: linear-gradient(180deg,#f7fbff 0%, #ffffff 100%);
    --card-bg: #ffffff;
    --muted: #6b7280;
    --accent: #2563eb;
}
body {background: var(--bg-grad);}
.stApp { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial; }

/* Header */
.header { padding: 18px 24px; border-radius: 10px; background: linear-gradient(90deg,#0f172a,#1e3a8a); color: white; box-shadow: 0 6px 20px rgba(2,6,23,0.08); }
.header h1 { margin: 0; font-weight: 700; font-size: 28px; }
.header p { margin: 6px 0 0 0; opacity: 0.95; }

/* Card style for metrics */
.metric-card { background: var(--card-bg); padding: 12px; border-radius: 12px; box-shadow: 0 6px 18px rgba(16,24,40,0.06); margin-bottom:8px }
.metric-label { color: var(--muted); font-size:12px; }
.metric-value { font-size:20px; font-weight:700; color:var(--accent); }

.panel { background: rgba(255,255,255,0.9); padding:14px; border-radius:10px; box-shadow: 0 4px 14px rgba(16,24,40,0.04); }

/* Footer muted */
.footer { color: var(--muted); font-size:12px; }

/* Sidebar tweaks */
.stSidebar { padding-top:10px }
.sidebar .stButton>button { width:100%; }

/* Responsive small tweaks */
@media (max-width: 600px){ .header h1 { font-size:20px } }
</style>
'''

st.markdown(_STYLE, unsafe_allow_html=True)

st.markdown(
    """
    <div class="header">
      <h1>🏦 Risk Management &amp; Regime Detection Engine</h1>
      <p>Advanced portfolio backtesting with adaptive risk controls and market regime analysis</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar navigation (grouped and compact)
st.sidebar.markdown("## 🔧 Controls")
st.sidebar.caption("Quickly navigate and run analyses")
page = st.sidebar.radio("Select Page", [
    "Dashboard",
    "Backtest",
    "Regime Analysis",
    "Stress Testing",
    "Outcome",
])

st.sidebar.markdown("---")
st.sidebar.markdown("## 📅 Global Date Range")
st.sidebar.caption("Set dates once - applies to all analyses")
st.session_state['global_start_date'] = st.sidebar.date_input(
    "Start Date",
    value=st.session_state['global_start_date'],
    key="global_start_input"
)
st.session_state['global_end_date'] = st.sidebar.date_input(
    "End Date",
    value=st.session_state['global_end_date'],
    key="global_end_input"
)

st.sidebar.markdown("---")
# Ticker selection (universal)
try:
    _prev_t = read_selected_ticker()
    _idx = tickers.index(_prev_t) if (_prev_t and _prev_t in tickers) else 0
except Exception:
    _idx = 0

selected_ticker = st.sidebar.selectbox("Select Ticker", options=tickers, index=_idx, key="selected_ticker")
try:
    write_selected_ticker(selected_ticker)
except Exception:
    st.sidebar.error("Failed to persist selected ticker")

st.sidebar.markdown("---")
st.sidebar.markdown("**Run Engines**")
if st.sidebar.button("Start Backtest", key="start_backtest_btn"):
    st.sidebar.info("Open Backtest page to configure and run a backtest.")

# Theme toggle
if 'dark_mode' not in st.session_state:
    st.session_state['dark_mode'] = False
dark = st.sidebar.checkbox("Dark mode (preview)", value=st.session_state['dark_mode'])
st.session_state['dark_mode'] = dark
if dark:
    st.markdown('<style> :root{ --bg-grad: linear-gradient(180deg,#0b1220 0%, #071028 100%); --card-bg:#071028; --muted:#9ca3af; --accent:#60a5fa; color: #e6eef8 } </style>', unsafe_allow_html=True)

# Note: ALL data is loaded on-demand via API calls
# No caching of metrics to ensure fresh data on each run

if page == "Dashboard":
    st.markdown("## 📊 System Overview")

    # Small helper to render metric cards with colors
    def render_card(label: str, value: str, delta: str = "", color: str = "#0f172a"):
        html = f"""
        <div class='metric-card'>
          <div class='metric-label'>{label}</div>
                    <div class='metric-value' style='color:{color}'>{value}</div>
                    <div class='metric-label'>{delta}</div>
                </div>
                """
        st.markdown(html, unsafe_allow_html=True)

    # Top summary cards
    cols = st.columns([1,1,1,1])
    with cols[0]:
        render_card("Regime Detector", "Active", "5 states", color="#0ea5a4")
    with cols[1]:
        render_card("Risk Engine", "Active", "4 components", color="#10b981")
    with cols[2]:
        render_card("Backtest Engine", "Ready", "Walk-forward", color="#60a5fa")
    with cols[3]:
        render_card("API Status", "Connected", "Backend ready", color="#34d399")

    # System components quick view
    st.markdown("### System Components")
    comp_col1, comp_col2 = st.columns(2)
    with comp_col1:
        st.markdown("**Risk Management Engine**")
        st.write("Volatility Targeting (8% target), Drawdown Protection (-15%), Position Sizing (Risk Parity), Stop-Loss (-3%)")
    with comp_col2:
        st.markdown("**Regime Detection**")
        st.write("Trending Up/Down, High Volatility, Crash, Normal Market")

    st.markdown("### Quick Stats & Performance")
    
    st.info(f"📅 Using dates: **{st.session_state['global_start_date'].strftime('%Y-%m-%d')}** → **{st.session_state['global_end_date'].strftime('%Y-%m-%d')}** (Set in sidebar)")

    # Call API for backtest (non-blocking summary)
    backtest_payload = {
        "start_date": st.session_state['global_start_date'].strftime('%Y-%m-%d'),
        "end_date": st.session_state['global_end_date'].strftime('%Y-%m-%d'),
        "target_vol": 0.08,
        "drawdown_limit": -0.15,
        "transaction_costs": 0.001
    }
    api_result = call_api("backtest", method="POST", data=backtest_payload)

    # helper: build_dates is defined at module level

    if api_result and api_result.get("status") == "success":
        metrics = api_result.get("metrics", {})
        
        # Show which dates these metrics are for
        st.caption(f"� Metrics for: {st.session_state['global_start_date'].strftime('%Y-%m-%d')} → {st.session_state['global_end_date'].strftime('%Y-%m-%d')} | Target Vol: 8.0%")
        
        # Validate metrics are present
        required_metrics = ['CAGR', 'Sharpe_Ratio', 'Annualized_Volatility', 'Sortino_Ratio']
        if not all(m in metrics for m in required_metrics):
            st.warning("⚠️ Some metrics missing from API response. Check API server.")
        
        # Display metrics only if valid data returned from API
        if metrics:
            mcols = st.columns(5)
            mvals = [
                f"{metrics.get('CAGR', 0):.2%}", 
                f"{metrics.get('Sharpe_Ratio', 0):.2f}", 
                f"{api_result.get('max_drawdown', 0):.2%}", 
                f"{metrics.get('Annualized_Volatility', 0):.2%}", 
                f"{metrics.get('Sortino_Ratio', 0):.2f}"
            ]
            mlabels = ["CAGR", "Sharpe", "Max DD", "Volatility", "Sortino"]
            colors = ["#10b981", "#0ea5a4", "#ef4444", "#f59e0b", "#0ea5a4"]
            for c, l, v, col in zip(mcols, mlabels, mvals, colors):
                with c:
                    render_card(l, v, "", color=col)

        # Tabs for performance, diagnostics and regime alerts
        tab1, tab2, tab3 = st.tabs(["Performance", "Diagnostics", "Regime Alerts"])
        with tab1:
            # Equity curve
            if "equity_curve" in api_result:
                st.subheader("Equity Curve")
                dates = build_dates(api_result, backtest_payload['start_date'], backtest_payload['end_date'])
                y = api_result['equity_curve']
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=dates if dates is not None else list(range(len(y))), y=y, mode='lines', name='Portfolio', line=dict(width=2, color='#2E86AB')))
                fig.update_layout(title="Portfolio Performance", xaxis_title="Date", yaxis_title="Value ($)", hovermode='x unified', height=420)
                st.plotly_chart(fig, use_container_width=True)

            # Returns distribution
            if "daily_returns" in api_result:
                st.subheader("Daily Returns")
                fig2 = px.histogram(api_result['daily_returns'], nbins=50, title="Daily Returns Distribution")
                st.plotly_chart(fig2, use_container_width=True)

        with tab2:
            st.subheader("Run Summary")
            st.json({k: api_result.get(k) for k in ['status','final_value','max_drawdown'] if k in api_result})

        with tab3:
            st.subheader("Regime Alerts")

            # Call regime-analysis endpoint to get current regime and recommendations
            regime_resp = call_api("regime-analysis", method="POST", data={})

            if not regime_resp:
                st.warning("Regime analysis unavailable — ensure API server is running.")
            else:
                current_regime = regime_resp.get('current_regime', 'Unknown')
                volatility = regime_resp.get('volatility', None)
                trend_strength = regime_resp.get('trend_strength', None)
                drawdown = regime_resp.get('drawdown', None)
                recommendations = regime_resp.get('recommendations', {}) or {}

                # Build dynamic messages (derived from API outputs, not hardcoded rules)
                msgs = []
                msgs.append(f"Market regime detected: {current_regime}.")

                if volatility is not None:
                    msgs.append(f"Portfolio volatility: {volatility:.1%}.")

                # Use textual recommendations when available
                pos = recommendations.get('position_sizing')
                def_alloc = recommendations.get('defensive_allocation') or recommendations.get('defensive_allocation', None)
                action = recommendations.get('recommended_action')

                if action:
                    msgs.append(action + ".")

                if pos:
                    msgs.append(f"Recommended equity allocation: {pos}.")

                if def_alloc:
                    msgs.append(f"Recommended defensive allocation: {def_alloc}.")

                # Display messages
                for m in msgs:
                    st.write("• " + m)
    else:
        st.warning("Quick stats unavailable — ensure API server is running or run a backtest from the Backtest page.")

elif page == "Backtest":
    st.markdown("## 🎯 Portfolio Backtest")

    # Input controls in a panel
    with st.expander("Backtest Configuration", expanded=True):
        st.info(f"📅 Using global dates: **{st.session_state['global_start_date'].strftime('%Y-%m-%d')}** → **{st.session_state['global_end_date'].strftime('%Y-%m-%d')}** (Set in sidebar)")
        
        cfg_col1, cfg_col2 = st.columns([1, 1])
        with cfg_col1:
            target_vol = st.slider("Target Volatility", 0.01, 0.30, 0.08, 0.01)
        with cfg_col2:
            dd_limit = st.slider("Drawdown Limit", -0.50, -0.01, -0.15, 0.01)

    run = st.button("Run Backtest", key="backtest_btn")
    result_container = st.empty()
    if run:
        with st.spinner("Running backtest via API..."):
            backtest_payload = {
                "start_date": st.session_state['global_start_date'].strftime('%Y-%m-%d'),
                "end_date": st.session_state['global_end_date'].strftime('%Y-%m-%d'),
                "target_vol": target_vol,
                "drawdown_limit": dd_limit,
                "transaction_costs": 0.001
            }
            api_result = call_api("backtest", method="POST", data=backtest_payload)

            if not api_result:
                st.error("Backtest API call failed — check logs and ensure API server is running.")
            else:
                if api_result.get("status") == "success":
                    metrics = api_result.get("metrics", {})
                    
                    # Validate metrics from API
                    if not metrics:
                        st.error("❌ API returned no metrics. Check API server logs.")
                    else:
                        # show compact metrics row - only display if data exists
                        row = st.columns(5)
                        vals = [
                            f"{metrics.get('CAGR', 0):.2%}", 
                            f"{metrics.get('Sharpe_Ratio', 0):.2f}", 
                            f"{api_result.get('max_drawdown', 0):.2%}", 
                            f"{metrics.get('Annualized_Volatility', 0):.2%}", 
                            f"${api_result.get('final_value', 0):.2f}"
                        ]
                        labs = ["CAGR","Sharpe","Max DD","Vol","Final"]
                        for c,l,v in zip(row,labs,vals):
                            c.markdown(f"<div class='metric-card'><div class='metric-label'>{l}</div><div class='metric-value'>{v}</div></div>", unsafe_allow_html=True)

                        st.success("✅ Backtest completed via API!")
                else:
                    st.error("❌ Backtest failed — see API response for details")
                    st.code(str(api_result))

                # Visuals
                if "equity_curve" in api_result:
                    with st.expander("Equity Curve", expanded=True):
                        dates = build_dates(api_result, backtest_payload['start_date'], backtest_payload['end_date'])
                        y = api_result['equity_curve']
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=dates if dates is not None else list(range(len(y))), y=y, mode='lines', line=dict(width=2, color='#2E86AB')))
                        fig.update_layout(height=420, hovermode='x unified')
                        st.plotly_chart(fig, use_container_width=True)

                if "daily_returns" in api_result:
                    with st.expander("Returns Distribution", expanded=False):
                        fig2 = px.histogram(api_result['daily_returns'], nbins=50)
                        st.plotly_chart(fig2, use_container_width=True)

elif page == "Regime Analysis":
    st.markdown("## 📈 Market Regime Analysis")

    # Show available data range
    try:
        range_info = call_api("data-range", method="GET")
        if range_info and range_info.get("status") == "success":
            st.info(f"📊 {range_info.get('message')} ({range_info.get('total_trading_days')} trading days)")
    except:
        pass

    left, right = st.columns([2, 1])

    with left:
        st.markdown("**Configure Analysis Date:**")
        st.caption(
            f"Using global date range: "
            f"**{st.session_state['global_start_date'].strftime('%Y-%m-%d')}** → "
            f"**{st.session_state['global_end_date'].strftime('%Y-%m-%d')}**"
        )

        analysis_col1, analysis_col2 = st.columns(2)

        with analysis_col1:
            analysis_date = st.date_input(
                "Analysis Date",
                value=st.session_state['global_end_date'],
                key="analysis_date_input"
            )

        with analysis_col2:
            st.write("")
            analyze_btn = st.button("Analyze Current Regime", key="regime_btn")

        if analyze_btn:
            with st.spinner("Analyzing regime via API..."):
                api_result = call_api(
                    "regime-analysis",
                    method="POST",
                    data={"analysis_date": str(analysis_date)}
                )

                if not api_result:
                    st.error("Regime analysis API failed - check backend.")
                else:
                    volatility = api_result.get("volatility", 0.0)
                    trend_strength = api_result.get("trend_strength", 0.0)
                    drawdown = api_result.get("drawdown", 0.0)

                    # -------------------------------
                    # VOLATILITY CLASSIFICATION
                    # -------------------------------
                    if volatility < 0.12:
                        vol_state = "Low Volatility"
                        vol_msg = "Low risk environment — stable conditions."
                    elif volatility < 0.20:
                        vol_state = "Normal Volatility"
                        vol_msg = "Typical equity regime."
                    elif volatility < 0.30:
                        vol_state = "High Volatility"
                        vol_msg = "Elevated risk — reduce exposure."
                    else:
                        vol_state = "Crisis Volatility"
                        vol_msg = "Extreme risk — defensive posture required."

                    # -------------------------------
                    # TREND CLASSIFICATION
                    # -------------------------------
                    if trend_strength > 0.05:
                        trend_state = "Strong Trend"
                        trend_msg = "Momentum strategies favored."
                    elif trend_strength > 0.02:
                        trend_state = "Moderate Trend"
                        trend_msg = "Partial directional exposure."
                    else:
                        trend_state = "Weak / Sideways"
                        trend_msg = "Neutral positioning advised."

                    # -------------------------------
                    # CRASH DETECTION (STRUCTURAL)
                    # -------------------------------
                    if volatility > 0.30 and drawdown < -0.20:
                        final_regime = "Crash Regime"
                    else:
                        final_regime = f"{vol_state} + {trend_state}"

                    # -------------------------------
                    # DISPLAY RESULTS
                    # -------------------------------
                    st.markdown(f"### 🧠 Detected Regime: **{final_regime}**")
                    st.caption(f"📅 As of: {analysis_date.strftime('%Y-%m-%d')}")

                    # Narrative Explanation
                    with st.expander("Narrative & Risk Interpretation", expanded=True):
                        st.write(f"• Volatility: {volatility:.2%} → {vol_msg}")
                        st.write(f"• Trend Strength: {trend_strength:.2%} → {trend_msg}")

                        if drawdown < -0.20:
                            st.write(f"• Drawdown {drawdown:.2%} — capital preservation mode.")
                        elif drawdown < -0.10:
                            st.write(f"• Drawdown {drawdown:.2%} — tighten risk controls.")
                        else:
                            st.write(f"• Drawdown {drawdown:.2%} — within acceptable limits.")

                    # Metric Cards
                    c1, c2, c3 = st.columns(3)
                    c1.markdown(
                        f"<div class='metric-card'><div class='metric-label'>Volatility (Annualized)</div>"
                        f"<div class='metric-value'>{volatility:.2%}</div></div>",
                        unsafe_allow_html=True
                    )
                    c2.markdown(
                        f"<div class='metric-card'><div class='metric-label'>Trend Strength</div>"
                        f"<div class='metric-value'>{trend_strength:.2%}</div></div>",
                        unsafe_allow_html=True
                    )
                    c3.markdown(
                        f"<div class='metric-card'><div class='metric-label'>Drawdown</div>"
                        f"<div class='metric-value'>{drawdown:.2%}</div></div>",
                        unsafe_allow_html=True
                    )

                    st.success("✅ Institutional-grade regime classification completed!")

    # -------------------------------
    # RIGHT PANEL – DEFINITIONS
    # -------------------------------
    with right:
        st.markdown("**Regime Definitions**")
        with st.expander("View definitions", expanded=True):
            st.markdown("""
            ### Volatility States (Annualized)
            - **Low Vol**: < 12% — Stable market conditions  
            - **Normal Vol**: 12–20% — Typical equity regime  
            - **High Vol**: 20–30% — Defensive positioning  
            - **Crisis**: > 30% — Extreme stress environment  

            ### Trend State
            - Based on momentum / moving average structure  
            - Strong trend → momentum allocation  
            - Weak trend → neutral positioning  

            ### Crash Regime
            - Volatility > 30%  
            - Drawdown worse than -20%  
            - Capital preservation mode activated
            """)


elif page == "Stress Testing":
    st.markdown("## 🔴 Stress Testing & Crisis Scenarios")

    st.write("Run stress scenarios to evaluate portfolio resilience under crisis conditions.")
    st.info(f"📅 Using global dates: **{st.session_state['global_start_date'].strftime('%Y-%m-%d')}** → **{st.session_state['global_end_date'].strftime('%Y-%m-%d')}** (Set in sidebar)")
    
    st.markdown("### How Stress Tests Work:")
    st.write("""
    - **Base Return**: Your portfolio's return in normal market conditions for the selected date range
    - **Crisis Return**: Simulated return if a major crash occurred during that period  
    - **Protection**: How well the risk engine protected capital in the crisis scenario
    
    **Why same dates = same results:** Identical market data produces identical backtests (this is correct).  
    **To see different values:** Change the date range in the sidebar and run again.
    """)
    
    if st.button("Run Crisis Scenarios", key="stress_btn"):
        with st.spinner("Starting stress test..."):
            # Pass dates to ensure fresh calculation
            api_result = call_api("stress-test", method="POST", data={
                "start_date": st.session_state['global_start_date'].strftime('%Y-%m-%d'),
                "end_date": st.session_state['global_end_date'].strftime('%Y-%m-%d')
            })
            if not api_result:
                st.error("Failed to start stress test via API")
            else:
                task_id = api_result.get('task_id')
                if not task_id:
                    st.error("API did not return a task id")
                else:
                    st.info(f"Stress test started (task id: {task_id}). Polling for result...")
                    import time
                    timeout = 300
                    poll_interval = 2
                    elapsed = 0
                    result = None
                    placeholder = st.empty()
                    while elapsed < timeout:
                        time.sleep(poll_interval)
                        elapsed += poll_interval
                        status_resp = call_api(f"stress-test/{task_id}", method="GET")
                        if not status_resp:
                            placeholder.text(f"Waiting for server... {elapsed}s")
                            continue
                        status = status_resp.get("status")
                        placeholder.text(f"Status: {status} — elapsed {elapsed}s")
                        if status == "completed":
                            result = status_resp.get("result")
                            break
                        if status == "failed":
                            st.error("Stress test failed on server")
                            st.code(status_resp.get("result", {}).get("error", "No error info"))
                            result = None
                            break

                    if result:
                        base = result.get('base', {})
                        crisis = result.get('crisis', {})
                        analysis = result.get('risk_engine_analysis', {}) or {}

                        st.success(f"✅ Stress test completed! Task ID: {task_id[:8]}")
                        st.caption(f"Calculated fresh scenarios for {st.session_state['global_start_date'].strftime('%Y-%m-%d')} → {st.session_state['global_end_date'].strftime('%Y-%m-%d')}")

                        c1, c2, c3 = st.columns(3)
                        c1.markdown(f"<div class='metric-card'><div class='metric-label'>Base Return</div><div class='metric-value'>{base.get('total_return',0):.2%}</div></div>", unsafe_allow_html=True)
                        c2.markdown(f"<div class='metric-card'><div class='metric-label'>Crisis Return</div><div class='metric-value'>{crisis.get('total_return',0):.2%}</div></div>", unsafe_allow_html=True)
                        c3.markdown(f"<div class='metric-card'><div class='metric-label'>Protection</div><div class='metric-value'>{analysis.get('capital_preservation_ratio',0):.1%}</div></div>", unsafe_allow_html=True)

                        with st.expander("Detailed Analysis", expanded=False):
                            st.write("**Base Scenario** (normal market conditions):")
                            st.write(f"- Total Return: {base.get('total_return', 0):.2%}")
                            st.write(f"- Max Drawdown: {base.get('max_drawdown', 0):.2%}")
                            
                            st.write("**Crisis Scenario** (market crash):")
                            st.write(f"- Total Return: {crisis.get('total_return', 0):.2%}")
                            st.write(f"- Max Drawdown: {crisis.get('max_drawdown', 0):.2%}")
                            st.write(f"- Capital Preservation: {analysis.get('capital_preservation_ratio', 0):.1%}")
                            
                            st.json(result)
                    else:
                        st.error("Stress testing did not complete within timeout or failed on server")

elif page == "Outcome":
    st.markdown("## 🎯 Crisis Simulation & System Outcome")

    st.info(
        f"📅 Using global dates: "
        f"**{st.session_state['global_start_date'].strftime('%Y-%m-%d')}** → "
        f"**{st.session_state['global_end_date'].strftime('%Y-%m-%d')}** "
        f"(Set in sidebar)"
    )

    st.markdown("### Crisis Injection Parameters")
    st.write("""
    The system simulates a severe market crisis by injecting:
    - **Geometric Crash (-25%)** distributed across shock window
    - **High Volatility Regime**
    - **Correlation Spike (diversification breakdown)**
    """)

    if st.button("Simulate Crisis & Analyze Outcome", key="outcome_btn"):
        with st.spinner("Simulating crisis scenario..."):

            api_result = call_api(
                "stress-test",
                method="POST",
                data={
                    "start_date": st.session_state['global_start_date'].strftime('%Y-%m-%d'),
                    "end_date": st.session_state['global_end_date'].strftime('%Y-%m-%d')
                }
            )

            if not api_result:
                st.error("Failed to start crisis simulation via API")
                st.stop()

            task_id = api_result.get("task_id")
            if not task_id:
                st.error("API did not return a task id")
                st.stop()

            import time
            timeout = 300
            poll_interval = 2
            elapsed = 0
            result = None
            placeholder = st.empty()

            while elapsed < timeout:
                time.sleep(poll_interval)
                elapsed += poll_interval

                status_resp = call_api(f"stress-test/{task_id}", method="GET")
                if not status_resp:
                    placeholder.text(f"Waiting for server... {elapsed}s")
                    continue

                status = status_resp.get("status")
                placeholder.text(f"Status: {status} — elapsed {elapsed}s")

                if status == "completed":
                    result = status_resp.get("result")
                    break

                if status == "failed":
                    st.error("Crisis simulation failed on server")
                    st.code(status_resp.get("result", {}).get("error", "No error info"))
                    st.stop()

            if not result:
                st.error("Crisis simulation did not complete within timeout")
                st.stop()

            placeholder.empty()

            base = result.get("base", {})
            crisis = result.get("crisis", {})
            analysis = result.get("risk_engine_analysis", {}) or {}

            st.success("✅ Crisis simulation completed!")

            # -----------------------------
            # Capital Protection Assessment
            # -----------------------------
            st.markdown("### 🛡️ Capital Protection Assessment")

            base_return = base.get("total_return", 0)
            crisis_return = crisis.get("total_return", 0)

            preservation_ratio = analysis.get("capital_preservation_ratio", 0)
            drawdown_protection = analysis.get("drawdown_protection", 0)

            # Health logic based on drawdown protection (more professional)
            if drawdown_protection > 0.60:
                health_status = "✅ STRONG"
                health_color = "#10b981"
                assessment = "System significantly reduced downside risk."
            elif drawdown_protection > 0.30:
                health_status = "⚠️ MODERATE"
                health_color = "#f59e0b"
                assessment = "System partially reduced crisis damage."
            elif drawdown_protection > 0:
                health_status = "❌ WEAK"
                health_color = "#ef4444"
                assessment = "Limited crisis protection observed."
            else:
                health_status = "🔴 CRITICAL"
                health_color = "#991b1b"
                assessment = "System amplified downside risk."

            c1, c2, c3, c4 = st.columns(4)

            c1.metric("Base Return", f"{base_return:.2%}")
            c2.metric("Crisis Return", f"{crisis_return:.2%}")
            c3.metric("Capital Preserved", f"{preservation_ratio:.1%}")
            c4.markdown(
                f"<div style='font-size:18px;font-weight:600;color:{health_color}'>{health_status}</div>",
                unsafe_allow_html=True
            )

            st.markdown(f"### System Assessment: {assessment}")

            # -----------------------------
            # Explainability Layer
            # -----------------------------
            st.markdown("### Explainability Layer")

            explanation_text = f"""
**Market Regime Detected:** High Volatility + Crash Environment  

**Risk Engine Behavior:**
- Target volatility constraint enforced
- Dynamic allocation adjustments triggered
- Drawdown control rules activated

**Performance Impact:**
- Base Return: {base_return:.2%}
- Crisis Return: {crisis_return:.2%}
- Capital Preservation Ratio: {preservation_ratio:.1%}
- Drawdown Protection: {drawdown_protection:.1%}

**Conclusion:** {'Portfolio remained structurally resilient.' if drawdown_protection > 0.30 else 'System requires improved downside controls.'}
"""

            st.markdown(explanation_text)

            # -----------------------------
            # Detailed Results
            # -----------------------------
            with st.expander("View Full Simulation Results", expanded=False):

                st.write("**Base Scenario (Normal Conditions):**")
                st.write(f"- Return: {base.get('total_return', 0):.2%}")
                st.write(f"- Max Drawdown: {base.get('max_drawdown', 0):.2%}")

                st.write("\n**Crisis Scenario (Crash + Volatility Spike):**")
                st.write(f"- Return: {crisis.get('total_return', 0):.2%}")
                st.write(f"- Max Drawdown: {crisis.get('max_drawdown', 0):.2%}")

                st.write("\n**Risk Engine Analysis:**")
                st.json(analysis)

st.markdown("---")
st.markdown("**Risk Management & Regime Detection Engine v1.0** | Built with Streamlit + FastAPI")

