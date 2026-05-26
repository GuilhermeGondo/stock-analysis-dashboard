import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# =========================================
# CONFIG
# =========================================

st.set_page_config(
    page_title="Stock Analysis Dashboard",
    layout="wide"
)

st.title("📈 Stock Analysis Dashboard")

# =========================================
# INPUTS
# =========================================

tickers = [
    "VIVA3.SA",
    "BRBI11.SA",
    "PSSA3.SA",
    "ITUB4.SA",
    "VALE3.SA"
]

targets = {
    "VIVA3": 28,
    "BRBI11": 17,
    "PSSA3": 45,
    "ITUB4": 42,
    "VALE3": 78
}

manual_market_caps = {
    "BRBI11": 314987000 * 16.11
}

# =========================================
# DATA COLLECTION
# =========================================

results = []

for ticker_full in tickers:

    try:

        ticker = ticker_full.replace(".SA", "")

        stock = yf.Ticker(ticker_full)

        info = stock.info

        hist = stock.history(period="2y")

        if hist.empty:
            continue

        current_price = hist["Close"].iloc[-1]

        market_cap = info.get("marketCap")

        pe_ratio = info.get("trailingPE")

        pb_ratio = info.get("priceToBook")

        # =========================================
        # DIVIDEND YIELD MANUAL
        # =========================================

        dividends = stock.dividends

        last_12m_dividends = dividends.last("365D").sum()

        dividend_yield = (
            last_12m_dividends / current_price
        ) * 100

        # =========================================
        # HISTORICAL METRICS
        # =========================================

        high_1y = hist["Close"].max()

        low_1y = hist["Close"].min()

        moving_avg_200 = (
            hist["Close"]
            .rolling(200)
            .mean()
            .iloc[-1]
        )

        distance_ma200 = (
            ((current_price / moving_avg_200) - 1) * 100
            if pd.notnull(moving_avg_200)
            else None
        )

        price_position = (
            (
                (current_price - low_1y)
                / (high_1y - low_1y)
            ) * 100
            if high_1y != low_1y
            else None
        )

        # =========================================
        # TARGET / UPSIDE
        # =========================================

        target_price = targets.get(ticker)

        upside = (
            (
                (target_price / current_price) - 1
            ) * 100
            if target_price is not None
            else None
        )

        # =========================================
        # VOLATILITY
        # =========================================

        daily_returns = hist["Close"].pct_change()

        volatility = (
            daily_returns.std()
            * np.sqrt(252)
            * 100
        )

        # =========================================
        # FALLBACK MARKET CAP
        # =========================================

        if market_cap is None:
            market_cap = manual_market_caps.get(ticker)

        # =========================================
        # APPEND
        # =========================================

        results.append({

            "date": datetime.today().date(),

            "ticker": ticker,

            "current_price": round(current_price, 2),

            "target_price": target_price,

            "upside_pct": round(upside, 2)
            if upside is not None else None,

            "market_cap": market_cap,

            "pe_ratio": round(pe_ratio, 2)
            if pe_ratio else None,

            "pb_ratio": round(pb_ratio, 2)
            if pb_ratio else None,

            "high_1y": round(high_1y, 2),

            "low_1y": round(low_1y, 2),

            "price_position_pct": round(price_position, 2)
            if price_position else None,

            "moving_avg_200": round(moving_avg_200, 2)
            if pd.notnull(moving_avg_200)
            else None,

            "distance_ma200_pct": round(distance_ma200, 2)
            if distance_ma200 is not None
            else None,

            "dividend_yield_pct": round(dividend_yield, 2),

            "volatility_annualized_pct": round(volatility, 2)

        })

    except Exception as e:

        print(f"Erro em {ticker_full}: {e}")

# =========================================
# DATAFRAME
# =========================================

df = pd.DataFrame(results)

df["date"] = pd.to_datetime(df["date"])

# =========================================
# SIDEBAR
# =========================================

st.sidebar.header("Filters")

selected_tickers = st.sidebar.multiselect(
    "Select Stocks",
    options=df["ticker"].unique(),
    default=df["ticker"].unique()
)

filtered_df = df[
    df["ticker"].isin(selected_tickers)
]

# =========================================
# METRICS
# =========================================

st.subheader("Portfolio Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Stocks",
    len(filtered_df)
)

col2.metric(
    "Average Upside",
    f"{filtered_df['upside_pct'].mean():.2f}%"
)

col3.metric(
    "Average Dividend Yield",
    f"{filtered_df['dividend_yield_pct'].mean():.2f}%"
)

col4.metric(
    "Highest Upside",
    filtered_df.loc[
        filtered_df["upside_pct"].idxmax(),
        "ticker"
    ]
)

# =========================================
# TABLE
# =========================================

st.subheader("Stock Table")

display_df = filtered_df.sort_values(
    "upside_pct",
    ascending=False
)

st.dataframe(
    display_df,
    use_container_width=True
)

# =========================================
# UPSIDE CHART
# =========================================

st.subheader("Upside by Stock")

fig_upside = px.bar(
    display_df,
    x="ticker",
    y="upside_pct",
    text="upside_pct"
)

st.plotly_chart(
    fig_upside,
    use_container_width=True
)

# =========================================
# DIVIDEND VS UPSIDE
# =========================================

st.subheader("Dividend Yield vs Upside")

fig_scatter = px.scatter(
    display_df,
    x="dividend_yield_pct",
    y="upside_pct",
    text="ticker",
    size="market_cap",
    hover_data=[
        "pe_ratio",
        "pb_ratio",
        "current_price"
    ]
)

st.plotly_chart(
    fig_scatter,
    use_container_width=True
)

# =========================================
# STOCK DETAIL
# =========================================

st.subheader("Individual Stock Analysis")

selected_stock = st.selectbox(
    "Choose a stock",
    display_df["ticker"]
)

# =========================================
# HISTORICAL DATA
# =========================================

stock_data = yf.download(
    f"{selected_stock}.SA",
    period="5y"
)

stock_data["MA200"] = (
    stock_data["Close"]
    .rolling(200)
    .mean()
)

# =========================================
# PRICE CHART
# =========================================

fig_price = go.Figure()

fig_price.add_trace(
    go.Scatter(
        x=stock_data.index,
        y=stock_data["Close"],
        name="Close"
    )
)

fig_price.add_trace(
    go.Scatter(
        x=stock_data.index,
        y=stock_data["MA200"],
        name="MA200"
    )
)

st.plotly_chart(
    fig_price,
    use_container_width=True
)