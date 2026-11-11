import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# Opsætning af siden
st.set_page_config(page_title="Stock-Map / RRG", layout="wide")

st.title("📊 Stock-Map: Watchlist & RRG Momentum")

# Standard-watchlists
DEFAULT_WATCHLISTS = {
    "Tema Watch": ["ACWI", "QQQ", "SMH", "SPY", "XLK"],
    "Sektor ETF'er": ["EXV6.DE", "EXV1.DE", "EXV2.DE", "EXV3.DE"],
}

# Gem watchlists i Session State
if "watchlists" not in st.session_state:
    st.session_state.watchlists = DEFAULT_WATCHLISTS

# SIDEBAR: Indstillinger og administration af watchlists
st.sidebar.header("⚙️ Watchlist Indstillinger")

# 1. Vælg eksisterende watchlist
selected_watchlist_name = st.sidebar.selectbox(
    "Vælg Watchlist", 
    options=list(st.session_state.watchlists.keys())
)

current_tickers = st.session_state.watchlists[selected_watchlist_name]

# 2. Opret ny watchlist
with st.sidebar.expander("➕ Opret ny watchlist"):
    new_wl_name = st.text_input("Navn på ny watchlist:")
    if st.button("Gem ny watchlist"):
        if new_wl_name and new_wl_name not in st.session_state.watchlists:
            st.session_state.watchlists[new_wl_name] = ["SPY"]
            st.rerun()

# 3. Vælg / fjern tickere i den aktuelt valgte watchlist
active_tickers = st.sidebar.multiselect(
    "Aktive tickere i listen",
    options=current_tickers,
    default=current_tickers
)

# 4. Tilføj ny ticker til aktiv watchlist
new_ticker = st.sidebar.text_input("Tilføj ticker (f.eks. AAPL):").strip().upper()
if st.sidebar.button("Tilføj til liste"):
    if new_ticker and new_ticker not in current_tickers:
        st.session_state.watchlists[selected_watchlist_name].append(new_ticker)
        st.rerun()

# Vælg benchmark til RRG / Momentum (f.eks. ACWI eller SPY)
benchmark = st.sidebar.selectbox("Benchmark til Relative Styrke", options=["ACWI", "SPY", "QQQ"], index=0)

# Hovedvisning: Hent data
if active_tickers:
    all_symbols = list(set(active_tickers + [benchmark]))
    
    with st.spinner("Henter kurser og beregner momentum..."):
        # Hent 1 års historisk data
        raw_data = yf.download(all_symbols, period="1y", progress=False)
        if isinstance(raw_data.columns, pd.MultiIndex):
            data = raw_data["Close"]
        else:
            data = raw_data[["Close"]].rename(columns={"Close": all_symbols[0]})

    st.success("Data hentet succesfuldt!")

    # Opret faner til hhv. Prisgraf og RRG/Momentum Map
    tab1, tab2 = st.tabs(["📈 Prisudvikling", "🧭 RRG & Momentum Map"])

    # TAB 1: PRISGRAF
    with tab1:
        st.subheader(f"Prisudvikling for: {selected_watchlist_name}")
        fig_price = go.Figure()
        for ticker in active_tickers:
            if ticker in data.columns:
                fig_price.add_trace(go.Scatter(x=data.index, y=data[ticker], mode='lines', name=ticker))
        
        fig_price.update_layout(
            xaxis_title="Dato",
            yaxis_title="Pris",
            hovermode="x unified",
            margin=dict(l=20, r=20, t=30, b=20)
        )
        st.plotly_chart(fig_price, use_container_width=True)

    # TAB 2: RRG & MOMENTUM MAP
    with tab2:
        st.subheader("🧭 Momentum & Relativ Styrke (RRG-inspireret)")
        st.markdown(f"Viser aktiernes relative styrke og momentum mod benchmark **{benchmark}** over de seneste 14 uger.")

        if benchmark not in data.columns:
            st.error(f"Benchmark {benchmark} mangler i data. Vælg et andet benchmark.")
        else:
            # Beregn simpel relativ styrke (Ratio = Ticker / Benchmark) og momentum (ROC af ratio)
            rs_table = []
            bm_prices = data[benchmark]

            for ticker in active_tickers:
                if ticker != benchmark and ticker in data.columns:
                    ticker_prices = data[ticker]
                    # Relativ styrke ratio
                    ratio = ticker_prices / bm_prices
                    # Relativ Styrke (niveau over 14 uger) og Momentum (ROC på 4 uger af ratioen)
                    rs_level = (ratio.iloc[-1] / ratio.rolling(60).mean().iloc[-1]) * 100
                    rs_momentum = ((ratio.iloc[-1] / ratio.iloc[-20]) - 1) * 100
                    
                    rs_table.append({
                        "Ticker": ticker,
                        "Relativ Styrke (RS)": round(rs_level, 2),
                        "Momentum (RS-Mom)": round(rs_momentum, 2)
                    })

            if rs_table:
                df_rs = pd.DataFrame(rs_table)

                # Scatter plot (RRG Kvadrant-lignende visning)
                fig_rrg = go.Figure()
                fig_rrg.add_trace(go.Scatter(
                    x=df_rs["Relativ Styrke (RS)"],
                    y=df_rs["Momentum (RS-Mom)"],
                    mode='text+markers+text',
                    text=df_rs["Ticker"],
                    textposition="top center",
                    marker=dict(size=12, color=['red' if m < 0 else 'green' for m in df_rs["Momentum (RS-Mom)"]])
                ))

                # Tilføj akser og kvadranter (skæring ved 100 for RS og 0 for Momentum)
                fig_rrg.add_hline(y=0, line_dash="dash", line_color="gray")
                fig_rrg.add_vline(x=100, line_dash="dash", line_color="gray")

                fig_rrg.update_layout(
                    xaxis_title="Relativ Styrke (RS-Ratio vs Benchmark)",
                    yaxis_title="Momentum (RS-Momentum)",
                    hovermode="closest",
                    margin=dict(l=20, r=20, t=30, b=20)
                )

                st.plotly_chart(fig_rrg, use_container_width=True)

                # Vis også datatabel med tal
                st.dataframe(df_rs, use_container_width=True)
            else:
                st.info("Tilføj flere tickere ud over dit benchmark for at se RRG-kortet.")
else:
    st.warning("Vælg eller tilføj mindst én ticker i menuen til venstre.")
