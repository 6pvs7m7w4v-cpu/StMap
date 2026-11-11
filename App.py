import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# Opsætning af siden
st.set_page_config(page_title="Stock-Map / RRG", layout="wide")

st.title("📊 Stock-Map: Watchlist & RRG Momentum")

# Standard-watchlists med dine primære lister
DEFAULT_WATCHLISTS = {
    "Tema Watch": ["ACWI", "QQQ", "SMH", "SPY", "XLK"],
    "Sektor ETF'er": ["EXV6.DE", "EXV1.DE", "EXV2.DE", "EXV3.DE"],
    "Kombineret Alle": ["ACWI", "QQQ", "SMH", "SPY", "XLK", "EXV6.DE", "EXV1.DE", "EXV2.DE", "EXV3.DE"],
}

# Gem watchlists i Session State
if "watchlists" not in st.session_state:
    st.session_state.watchlists = DEFAULT_WATCHLISTS

# SIDEBAR: Indstillinger
st.sidebar.header("⚙️ Indstillinger")

# 1. Vælg eksisterende watchlist
selected_watchlist_name = st.sidebar.selectbox(
    "Vælg Watchlist", 
    options=list(st.session_state.watchlists.keys())
)

current_tickers = st.session_state.watchlists[selected_watchlist_name]

# 2. Opret ny watchlist
st.sidebar.markdown("---")
st.sidebar.subheader("➕ Opret ny watchlist")
new_wl_name = st.sidebar.text_input("Navn på ny liste:")
if st.sidebar.button("Gem ny liste"):
    if new_wl_name and new_wl_name not in st.session_state.watchlists:
        st.session_state.watchlists[new_wl_name] = ["SPY"]
        st.rerun()

st.sidebar.markdown("---")

# 3. Vælg / fjern tickere i den aktuelt valgte watchlist
active_tickers = st.sidebar.multiselect(
    "Aktive tickere i listen",
    options=current_tickers,
    default=current_tickers
)

# 4. Tilføj ny ticker til aktiv watchlist
new_ticker = st.sidebar.text_input("Tilføj ticker (f.eks. AAPL, EXV6.DE):").strip().upper()
if st.sidebar.button("Tilføj til liste"):
    if new_ticker and new_ticker not in current_tickers:
        st.session_state.watchlists[selected_watchlist_name].append(new_ticker)
        st.rerun()

st.sidebar.markdown("---")
# Benchmark og historik-længde
benchmark = st.sidebar.selectbox("Benchmark til RRG", options=["ACWI", "SPY", "QQQ"], index=0)
history_weeks = st.sidebar.slider("Hale-historik (uger på RRG)", min_value=1, max_value=12, value=4)

# Hovedvisning: Hent data
if active_tickers:
    all_symbols = list(set(active_tickers + [benchmark]))
    
    with st.spinner("Henter kurser og beregner..."):
        raw_data = yf.download(all_symbols, period="2y", progress=False)
        
        if isinstance(raw_data.columns, pd.MultiIndex):
            data = raw_data["Close"]
        else:
            data = raw_data[["Close"]]
            if len(all_symbols) == 1:
                data.columns = all_symbols

    st.success("Data hentet succesfuldt!")

    # Opret faner
    tab1, tab2 = st.tabs(["📈 Prisudvikling", "🧭 RRG & Momentum Map"])

    # TAB 1: PRISGRAF
    with tab1:
        st.subheader(f"Prisudvikling for: {selected_watchlist_name}")
        fig_price = go.Figure()
        for ticker in active_tickers:
            # Sikre robust opslag uanset yfinance kolonnestruktur
            t_col = next((c for c in data.columns if ticker in c), None)
            if t_col is not None:
                fig_price.add_trace(go.Scatter(x=data.index, y=data[t_col], mode='lines', name=ticker))
            elif len(data.columns) == 1:
                fig_price.add_trace(go.Scatter(x=data.index, y=data.iloc[:, 0], mode='lines', name=ticker))
        
        fig_price.update_layout(
            xaxis_title="Dato",
            yaxis_title="Pris",
            hovermode="x unified",
            margin=dict(l=20, r=20, t=30, b=20)
        )
        st.plotly_chart(fig_price, use_container_width=True)

    # TAB 2: RRG & MOMENTUM MAP MED HISTORIK-HALER
    with tab2:
        st.subheader("🧭 RRG Momentum & Rotations-kort")
        st.markdown(f"Viser udviklingen over de seneste **{history_weeks} uger** i forhold til **{benchmark}**.")

        bm_col = next((c for c in data.columns if benchmark in c), None)

        if bm_col is None:
            st.error(f"Benchmark {benchmark} blev ikke fundet i de hentede data.")
        else:
            bm_prices = data[bm_col]
            
            # Resample til ugentlige data for renere RRG-beregning
            weekly_data = data.resample('W').last()
            weekly_bm = bm_prices.resample('W').last()

            fig_rrg = go.Figure()
            latest_table = []

            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

            for idx, ticker in enumerate(active_tickers):
                if ticker != benchmark:
                    t_col = next((c for c in weekly_data.columns if ticker in c), None)
                    
                    if t_col is not None:
                        t_prices = weekly_data[t_col]
                        ratio = (t_prices / weekly_bm).dropna()

                        if len(ratio) > 52:
                            rs_ratio = (ratio / ratio.rolling(52).mean()) * 100
                            rs_mom = (ratio / ratio.shift(4)) * 100

                            df_history = pd.DataFrame({
                                "RS": rs_ratio.iloc[-(history_weeks + 1):],
                                "Mom": rs_mom.iloc[-(history_weeks + 1):]
                            }).dropna()

                            if not df_history.empty:
                                color = colors[idx % len(colors)]

                                # Hale / historik-linje
                                fig_rrg.add_trace(go.Scatter(
                                    x=df_history["RS"],
                                    y=df_history["Mom"],
                                    mode='lines+markers',
                                    name=ticker,
                                    line=dict(color=color, width=2, dash='dot'),
                                    marker=dict(size=5, color=color),
                                    showlegend=True
                                ))

                                # Seneste punkt
                                latest_rs = df_history["RS"].iloc[-1]
                                latest_mom = df_history["Mom"].iloc[-1]

                                fig_rrg.add_trace(go.Scatter(
                                    x=[latest_rs],
                                    y=[latest_mom],
                                    mode='markers+text',
                                    text=[ticker],
                                    textposition="top center",
                                    marker=dict(size=14, color=color, symbol='circle'),
                                    showlegend=False
                                ))

                                latest_table.append({
                                    "Ticker": ticker,
                                    "Relativ Styrke (RS)": round(float(latest_rs), 2),
                                    "Momentum (RS-Mom)": round(float(latest_mom), 2)
                                })

            if latest_table:
                fig_rrg.add_hline(y=100, line_dash="solid", line_color="rgba(150,150,150,0.5)")
                fig_rrg.add_vline(x=100, line_dash="solid", line_color="rgba(150,150,150,0.5)")

                fig_rrg.update_layout(
                    xaxis_title="Relativ Styrke (RS-Ratio vs Benchmark)",
                    yaxis_title="Momentum (RS-Momentum)",
                    hovermode="closest",
                    margin=dict(l=20, r=20, t=30, b=20),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )

                st.plotly_chart(fig_rrg, use_container_width=True)
                st.dataframe(pd.DataFrame(latest_table), use_container_width=True)
            else:
                st.info("Tilføj flere tickere ud over dit benchmark for at generere RRG-kortet.")
else:
    st.warning("Vælg eller tilføj mindst én ticker i menuen til venstre.")
