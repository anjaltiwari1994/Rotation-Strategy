import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Nifty 50 Momentum Dashboard Pro", layout="wide")

BENCHMARK = "NIFTYBEES.NS"
TOP_N = 5
STOP_LOSS = -10  # percent

NIFTY50 = [
    "ADANIENT.NS", "ADANIPORTS.NS", "APOLLOHOSP.NS", "ASIANPAINT.NS",
    "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS",
    "BEL.NS", "BHARTIARTL.NS", "CIPLA.NS", "COALINDIA.NS",
    "DRREDDY.NS", "EICHERMOT.NS", "ETERNAL.NS", "GRASIM.NS",
    "HCLTECH.NS", "HDFCBANK.NS", "HDFCLIFE.NS", "HEROMOTOCO.NS",
    "HINDALCO.NS", "HINDUNILVR.NS", "ICICIBANK.NS", "INDUSINDBK.NS",
    "INFY.NS", "ITC.NS", "JIOFIN.NS", "JSWSTEEL.NS",
    "KOTAKBANK.NS", "LT.NS", "M&M.NS", "MARUTI.NS",
    "NESTLEIND.NS", "NTPC.NS", "ONGC.NS", "POWERGRID.NS",
    "RELIANCE.NS", "SBILIFE.NS", "SBIN.NS", "SHRIRAMFIN.NS",
    "SUNPHARMA.NS", "TATACONSUM.NS", "TATAMOTORS.NS", "TATASTEEL.NS",
    "TCS.NS", "TECHM.NS", "TITAN.NS", "TRENT.NS",
    "ULTRACEMCO.NS", "WIPRO.NS"
]

# ---------- DATA ----------
@st.cache_data(ttl=3600)
def fetch_stock_data(symbol):
    try:
        df = yf.download(symbol, period="3mo", interval="1d", progress=False, threads=False)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[["Close"]].dropna()
        current_price = float(df["Close"].iloc[-1])
        monthly = df.resample("ME").last()
        if len(monthly) < 2:
            return None
        prev_month_close = float(monthly["Close"].iloc[-2])
        monthly_return = ((current_price / prev_month_close) - 1) * 100
        return {
            "Current Price": round(current_price, 2),
            "Prev Month Close": round(prev_month_close, 2),
            "Monthly Return %": round(monthly_return, 2)
        }
    except:
        return None

@st.cache_data(ttl=60)
def fetch_data(symbol):

    try:
        df = yf.download(
            symbol,
            period="3mo",
            interval="1d",
            progress=False,
            threads=False,
            auto_adjust=False
        )

        if df.empty:
            return None

        # Flatten columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if "Close" not in df.columns:
            return None

        df = df[["Close"]].dropna()

        if len(df) < 20:
            return None

        current_price = float(df["Close"].iloc[-1])

        monthly = df.resample("ME").last()

        if len(monthly) < 2:
            return None

        prev_month_close = float(monthly["Close"].iloc[-2])

        monthly_return = ((current_price / prev_month_close) - 1) * 100

        return {
            "Current Price": round(current_price, 2),
            "Prev Month Close": round(prev_month_close, 2),
            "Monthly Return %": round(monthly_return, 2)
        }

    except:
        return None

def build_dashboard():

    benchmark = fetch_data(BENCHMARK)

    if benchmark is None:
        st.error("Benchmark data could not be fetched.")
        st.stop()

    # Safety conversion
    benchmark_return = float(benchmark["Monthly Return %"])

    results = []

    for stock in NIFTY50:

        data = fetch_data(stock)

        if data is None:
            continue

        try:
            stock_return = float(data["Monthly Return %"])

            rs = stock_return - benchmark_return

            results.append({
                "Stock": stock.replace(".NS", ""),
                "Current Price": float(data["Current Price"]),
                "Prev Month Close": float(data["Prev Month Close"]),
                "Stock Return %": round(stock_return, 2),
                "Benchmark Return %": round(benchmark_return, 2),
                "RS Score": round(rs, 2)
            })

        except Exception:
            continue

    dashboard = pd.DataFrame(results)

    if dashboard.empty:
        st.error("No stock data available.")
        st.stop()

    dashboard.sort_values("RS Score", ascending=False, inplace=True)

    dashboard["Rank"] = range(1, len(dashboard) + 1)

    dashboard.reset_index(drop=True, inplace=True)

    return dashboard, benchmark

    df = pd.DataFrame(results)
    df.sort_values("RS Score", ascending=False, inplace=True)
    df["Rank"] = range(1, len(df) + 1)
    return df.reset_index(drop=True), benchmark

# ---------- PORTFOLIO TRACKER ----------
def initialize_portfolio():
    if "portfolio" not in st.session_state:
        st.session_state.portfolio = pd.DataFrame(columns=[
            "Stock", "Buy Price", "Quantity", "Current Price", "PnL %"
        ])


def generate_signals(dashboard):
    current_top5 = dashboard.head(TOP_N)["Stock"].tolist()
    held_stocks = st.session_state.portfolio["Stock"].tolist()

    buy_alerts = [s for s in current_top5 if s not in held_stocks]
    sell_alerts = [s for s in held_stocks if s not in current_top5]

    return buy_alerts, sell_alerts, current_top5


def update_portfolio_prices(dashboard):
    if st.session_state.portfolio.empty:
        return

    for idx, row in st.session_state.portfolio.iterrows():
        stock_data = dashboard[dashboard["Stock"] == row["Stock"]]
        if not stock_data.empty:
            current_price = stock_data.iloc[0]["Current Price"]
            buy_price = row["Buy Price"]
            pnl = ((current_price / buy_price) - 1) * 100

            st.session_state.portfolio.at[idx, "Current Price"] = current_price
            st.session_state.portfolio.at[idx, "PnL %"] = round(pnl, 2)


def execute_rebalance(dashboard, capital=30000):
    top5 = dashboard.head(TOP_N)
    allocation = capital / TOP_N

    new_portfolio = []

    for _, row in top5.iterrows():
        qty = allocation / row["Current Price"]
        new_portfolio.append({
            "Stock": row["Stock"],
            "Buy Price": row["Current Price"],
            "Quantity": round(qty, 2),
            "Current Price": row["Current Price"],
            "PnL %": 0.0
        })

    st.session_state.portfolio = pd.DataFrame(new_portfolio)

# ---------- UI ----------
st.title("📈 Nifty 50 Momentum Dashboard Pro")
initialize_portfolio()

dashboard, benchmark = build_dashboard()
update_portfolio_prices(dashboard)

# Benchmark
st.subheader("Benchmark")
c1, c2, c3 = st.columns(3)
c1.metric("Current Price", f"₹{benchmark['Current Price']}")
c2.metric("Prev Month Close", f"₹{benchmark['Prev Month Close']}")
c3.metric("Monthly Return", f"{benchmark['Monthly Return %']}%")

# Signals
buy_alerts, sell_alerts, top5 = generate_signals(dashboard)

st.subheader("🚨 Buy/Sell Alerts")
col1, col2 = st.columns(2)

with col1:
    st.success(f"BUY: {', '.join(buy_alerts) if buy_alerts else 'No new buys'}")

with col2:
    st.error(f"SELL: {', '.join(sell_alerts) if sell_alerts else 'No sells'}")

# Rebalance button
if st.button("🔄 Execute Monthly Rebalance"):
    execute_rebalance(dashboard)
    st.success("Portfolio updated to latest Top 5 momentum stocks.")

# Top 5
st.subheader("🏆 Current Top 5")
st.dataframe(dashboard.head(5), use_container_width=True)

# Portfolio Tracker
st.subheader("💼 Live Portfolio Tracker")

if not st.session_state.portfolio.empty:
    st.dataframe(st.session_state.portfolio, use_container_width=True)

    total_value = (st.session_state.portfolio["Quantity"] * st.session_state.portfolio["Current Price"]).sum()
    total_cost = (st.session_state.portfolio["Quantity"] * st.session_state.portfolio["Buy Price"]).sum()
    portfolio_return = ((total_value / total_cost) - 1) * 100

    p1, p2, p3 = st.columns(3)
    p1.metric("Portfolio Value", f"₹{total_value:,.2f}")
    p2.metric("Total Return", f"{portfolio_return:.2f}%")
    p3.metric("Holdings", len(st.session_state.portfolio))

    # Stop loss alerts
    stop_loss_hits = st.session_state.portfolio[
        st.session_state.portfolio["PnL %"] <= STOP_LOSS
    ]

    if not stop_loss_hits.empty:
        st.warning(
            "⚠ Stop Loss Triggered: " + ", ".join(stop_loss_hits["Stock"].tolist())
        )
else:
    st.info("No active portfolio yet. Click monthly rebalance to start.")

# Full dashboard
st.subheader("📊 Full RS Ranking")
st.dataframe(dashboard, use_container_width=True, height=700)

# Chart
st.subheader("📉 Relative Strength Chart")
fig = px.bar(
    dashboard,
    x="Stock",
    y="RS Score",
    color="RS Score"
)
fig.update_layout(height=650, xaxis_tickangle=-45)
st.plotly_chart(fig, use_container_width=True)

# Download
csv = dashboard.to_csv(index=False).encode("utf-8")
st.download_button(
    "📥 Download Dashboard CSV",
    csv,
    file_name=f"nifty50_dashboard_{datetime.today().date()}.csv",
    mime="text/csv"
)

st.markdown("---")
st.caption("Monthly rotation strategy | Buy top 5 | Sell rank dropouts | Portfolio tracker + alerts")
