"""
Streamlit UI for Risk Management & Regime Detection Engine
Interactive dashboard for backtesting, analysis, and stress testing
CONNECTED TO BACKEND VIA REST API
"""

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
API_BASE_URL = "http://localhost:8000"

def call_api(endpoint: str, method: str = "GET", data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Helper function to call API endpoints"""
    url = f"{API_BASE_URL}/{endpoint}"

    try:
        if method == "POST":
            response = requests.post(url, json=data, timeout=60)  # Increased timeout for backtests
        else:
            response = requests.get(url, timeout=10)

        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        st.error("Make sure the API server is running: `python main.py --api`")
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
    "Documentation",
])

st.sidebar.markdown("---")
st.sidebar.markdown("**Run Engines**")
if st.sidebar.button("Start Backtest"):
    st.sidebar.info("Open Backtest page to configure and run a backtest.")

# Theme toggle
if 'dark_mode' not in st.session_state:
    st.session_state['dark_mode'] = False
dark = st.sidebar.checkbox("Dark mode (preview)", value=st.session_state['dark_mode'])
st.session_state['dark_mode'] = dark
if dark:
    st.markdown('<style> :root{ --bg-grad: linear-gradient(180deg,#0b1220 0%, #071028 100%); --card-bg:#071028; --muted:#9ca3af; --accent:#60a5fa; color: #e6eef8 } </style>', unsafe_allow_html=True)

# Load data once
@st.cache_data
def load_system_data():
    """Load system data via API (placeholder - actual data comes from API calls)"""
    # Data is now loaded on-demand via API calls
    return None, None

# Data is now loaded on-demand via API calls
# No need to preload data since API handles it

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

    # Call API for backtest (non-blocking summary)
    backtest_payload = {
        "start_date": "2023-01-01",
        "end_date": "2024-12-31",
        "target_vol": 0.08,
        "drawdown_limit": -0.15,
        "transaction_costs": 0.001
    }
    api_result = call_api("backtest", method="POST", data=backtest_payload)

    # helper: build_dates is defined at module level

    if api_result and api_result.get("status") == "success":
        metrics = api_result.get("metrics", {})

        # Summary metrics row
        mcols = st.columns(5)
        mvals = [f"{metrics.get('CAGR', 0):.2%}", f"{metrics.get('Sharpe_Ratio', 0):.2f}", f"{api_result.get('max_drawdown', 0):.2%}", f"{metrics.get('Annualized_Volatility', 0):.2%}", f"{metrics.get('Sortino_Ratio', 0):.2f}"]
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
        cfg_col1, cfg_col2, cfg_col3 = st.columns([1,1,1])
        with cfg_col1:
            start_date = st.date_input("Start Date", value=pd.to_datetime("2023-01-01"))
            end_date = st.date_input("End Date", value=pd.to_datetime("2024-12-31"))
        with cfg_col2:
            target_vol = st.slider("Target Volatility", 0.01, 0.30, 0.08, 0.01)
        with cfg_col3:
            dd_limit = st.slider("Drawdown Limit", -0.50, -0.01, -0.15, 0.01)

    run = st.button("Run Backtest", key="backtest_btn")
    result_container = st.empty()
    if run:
        with st.spinner("Running backtest via API..."):
            backtest_payload = {
                "start_date": str(start_date),
                "end_date": str(end_date),
                "target_vol": target_vol,
                "drawdown_limit": dd_limit,
                "transaction_costs": 0.001
            }
            api_result = call_api("backtest", method="POST", data=backtest_payload)

            if not api_result:
                st.error("Backtest API call failed — check logs and API server.")
            else:
                if api_result.get("status") == "success":
                    metrics = api_result.get("metrics", {})
                    # show compact metrics row
                    row = st.columns(5)
                    vals = [f"{metrics.get('CAGR', 0):.2%}", f"{metrics.get('Sharpe_Ratio', 0):.2f}", f"{api_result.get('max_drawdown', 0):.2%}", f"{metrics.get('Annualized_Volatility', 0):.2%}", f"${api_result.get('final_value', 0):.2f}"]
                    labs = ["CAGR","Sharpe","Max DD","Vol","Final"]
                    for c,l,v in zip(row,labs,vals):
                        c.markdown(f"<div class='metric-card'><div class='metric-label'>{l}</div><div class='metric-value'>{v}</div></div>", unsafe_allow_html=True)

                    st.success("✅ Backtest completed via API!")
                else:
                    st.error("❌ Backtest failed — see API response for details")

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

    left, right = st.columns([2,1])
    with left:
        st.markdown("Use the analyze button to get the current regime and recommendations.")
        if st.button("Analyze Current Regime", key="regime_btn"):
            with st.spinner("Analyzing regime via API..."):
                api_result = call_api("regime-analysis", method="POST", data={})
                if not api_result:
                    st.error("Regime analysis API failed")
                else:
                    current_regime = api_result.get("current_regime", "Unknown")
                    recommendations = api_result.get("recommendations", {})
                    volatility = api_result.get("volatility", 0)
                    trend_strength = api_result.get("trend_strength", 0)
                    drawdown = api_result.get("drawdown", 0)

                    st.markdown(f"### Market regime detected: **{current_regime}**")
                    description = recommendations.get("description", "Market analysis in progress")
                    st.info(description)

                    # narrative
                    narrative = []
                    if volatility > 0.15:
                        narrative.append(f"Volatility at {volatility:.1%} — critical range.")
                    elif volatility > 0.08:
                        narrative.append(f"Volatility at {volatility:.1%} — elevated.")
                    if trend_strength > 0.5:
                        narrative.append("Strong trend — consider momentum exposure.")
                    if drawdown < -0.10:
                        narrative.append(f"Drawdown {drawdown:.1%} — tighten risk controls.")

                    with st.expander("Narrative & Actions", expanded=True):
                        for line in narrative:
                            st.write(f"• {line}")

                    # Metrics cards
                    c1, c2, c3 = st.columns(3)
                    c1.markdown(f"<div class='metric-card'><div class='metric-label'>Volatility</div><div class='metric-value'>{volatility:.2%}</div></div>", unsafe_allow_html=True)
                    c2.markdown(f"<div class='metric-card'><div class='metric-label'>Trend Strength</div><div class='metric-value'>{trend_strength:.2%}</div></div>", unsafe_allow_html=True)
                    c3.markdown(f"<div class='metric-card'><div class='metric-label'>Drawdown</div><div class='metric-value'>{drawdown:.2%}</div></div>", unsafe_allow_html=True)

                    st.success("✅ Regime analysis completed via API!")

    with right:
        st.markdown("**Regime Definitions**")
        with st.expander("View definitions", expanded=True):
            st.markdown("""
            - **Normal**: Volatility < 5% — Stable returns, full exposure
            - **Moderate**: Vol 5-8% — Reduced exposure
            - **High Vol**: Vol 8-15% — Defensive positioning
            - **Trending Up/Down**: Momentum-based actions
            - **Crash**: Vol > 15% — Extreme caution
            """)

elif page == "Stress Testing":
    st.markdown("## 🔴 Stress Testing & Crisis Scenarios")

    st.write("Run stress scenarios to evaluate portfolio resilience under crisis conditions.")
    if st.button("Run Crisis Scenarios", key="stress_btn"):
        with st.spinner("Starting stress test..."):
            api_result = call_api("stress-test", method="POST", data={})
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

                        c1, c2, c3 = st.columns(3)
                        c1.markdown(f"<div class='metric-card'><div class='metric-label'>Base Return</div><div class='metric-value'>{base.get('total_return',0):.2%}</div></div>", unsafe_allow_html=True)
                        c2.markdown(f"<div class='metric-card'><div class='metric-label'>Crisis Return</div><div class='metric-value'>{crisis.get('total_return',0):.2%}</div></div>", unsafe_allow_html=True)
                        c3.markdown(f"<div class='metric-card'><div class='metric-label'>Protection</div><div class='metric-value'>{analysis.get('capital_preservation_ratio',0):.1%}</div></div>", unsafe_allow_html=True)

                        with st.expander("Detailed Analysis", expanded=False):
                            st.json(result)
                        st.success("✅ Stress testing completed via API!")
                    else:
                        st.error("Stress testing did not complete within timeout or failed on server")

elif page == "Documentation":
    st.markdown("## 📚 System Documentation")

    with st.expander("Risk Management Engine", expanded=False):
        st.markdown("""
        The risk engine automatically adjusts portfolio exposure based on market conditions:

        1. **Volatility Targeting**: Scales positions to maintain target portfolio volatility
        2. **Drawdown Protection**: Reduces equity exposure when drawdown exceeds threshold
        3. **Position Sizing**: Uses risk parity (inverse volatility weighting)
        4. **Stop-Loss Logic**: Exits individual positions at loss thresholds
        """)

    with st.expander("Regime Detection", expanded=False):
        st.markdown("""
        Detects distinct market regimes using technical indicators:
        - **Volatility Threshold**
        - **Trend Strength & Direction**
        - **Drawdown Detection**n
        Use outputs to adapt allocation and risk management dynamically.
        """)

    with st.expander("Backtesting Framework", expanded=False):
        st.markdown("""
        - Walk-forward validation (no lookahead bias)
        - Real-time regime detection
        - Transaction costs included
        - Adaptive allocation based on regime
        """)

    with st.expander("Performance Metrics", expanded=False):
        st.markdown("""
        - **CAGR** — Compound Annual Growth Rate
        - **Sharpe Ratio** — Risk-adjusted returns
        - **Sortino Ratio** — Downside deviation
        - **Max Drawdown** — Largest peak-to-trough decline
        - **Win Rate** — % of profitable days
        """)

    st.markdown("---")
    st.info("Run the engine with: python complete_system_demo.py")

# Footer
st.markdown("---")
st.markdown("**Risk Management & Regime Detection Engine v1.0** | Built with Streamlit + FastAPI")
