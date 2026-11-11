import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

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

# SIDEBAR: Bedre udnyttelse af pladsen (ingen skjulte expanders)
st.sidebar.header("⚙️ Indstillinger")

# 1. Vælg eksisterende watchlist
selected_watchlist_name = st.sidebar.selectbox(
    "Vælg Watchlist", 
    options=list(st.session_state.watchlists.keys())
)

current_tickers = st.session_state.watchlists[selected_watchlist_name]

# 2. Opret ny watchlist direkte fremme i lyset
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
# Vælg benchmark til RRG / Momentum
benchmark = st.sidebar.selectbox("Benchmark til RRG", options=["ACWI", "SPY", "QQQ"], index=0)

# Hovedvisning: Hent data
if active_tickers:
    all_symbols = list(set(active_tickers + [benchmark]))
    
    with st.spinner("Henter kurser og beregner..."):
        raw_data = yf.download(all_symbols, period="1y", progress=False)
        
        # Håndtering af yfinance datastruktur (MultiIndex vs enkelt kolonne)
        if isinstance(raw_data.columns, pd.MultiIndex):
            data = raw_data["Close"]
        else:
            data = raw_data[["Close"]]
            if len(all_symbols) == 1:
                data.columns = all_symbols

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
            elif len(data.columns) == 1:
                fig_price.add_trace(go.Scatter(x=data.index, y=data.iloc[:, 0], mode='lines', name=active_tickers[0]))
        
        fig_price.update_layout(
            xaxis_title="Dato",
            yaxis_title="Pris",
            hovermode="x unified",
            margin=dict(l=20, r=20, t=30, b=20)
        )
        st.plotly_chart(fig_price, use_container_width=True)

    # TAB 2: RRG & MOMENTUM MAP
    with tab2:
        st.subheader("🧭 Momentum & Relativ Styrke (RRG)")
        st.markdown(f"Viser aktiernes relative styrke mod benchmark **{benchmark}**.")

        # Sikre at benchmark findes i data
        bm_col = None
        for col in data.columns:
            if benchmark in col:
                bm_col = col
                break

        if bm_col is None:
            st.error(f"Benchmark {benchmark} blev ikke fundet i de hentede data.")
        else:
            bm_prices = data[bm_col]
            rs_table = []

            for ticker in active_tickers:
                if ticker != benchmark:
                    t_col = None
                    for col in data.columns:
                        if ticker in col:
                            t_col = col
                            break
                    
                    if t_col is not None:
                        ticker_prices = data[t_col]
                        # Beregn ratio og sørg for at fjerne NaN-værdier
                        ratio = (ticker_prices / bm_prices).dropna()
                        
                        if len(ratio) > 60:
                            rs_level = (ratio.iloc[-1] / ratio.rolling(60).mean().iloc[-1]) * 100
                            rs_momentum = ((ratio.iloc[-1] / ratio.iloc[-20]) - 1) * 100
                            
                            rs_table.append({
                                "Ticker": ticker,
                                "Relativ Styrke (RS)": round(float(rs_level), 2),
                                "Momentum (RS-Mom)": round(float(rs_momentum), 2)
                            })

            if rs_table:
                df_rs = pd.DataFrame(rs_table)

                fig_rrg = go.Figure()
                fig_rrg.add_trace(go.Scatter(
                    x=df_rs["Relativ Styrke (RS)"],
                    y=df_rs["Momentum (RS-Mom)"],
                    mode='text+markers',
                    text=df_rs["Ticker"],
                    textposition="top center",
                    marker=dict(size=14, color=['#FF4B4B' if m < 0 else '#09AB3B' for m in df_rs["Momentum (RS-Mom)"]])
                ))

                fig_rrg.add_hline(y=0, line_dash="dash", line_color="gray")
                fig_rrg.add_vline(x=100, line_dash="dash", line_color="gray")

                fig_rrg.update_layout(
                    xaxis_title="Relativ Styrke (RS-Ratio vs Benchmark)",
                    yaxis_title="Momentum (RS-Momentum)",
                    hovermode="closest",
                    margin=dict(l=20, r=20, t=30, b=20)
                )

                st.plotly_chart(fig_rrg, use_container_width=True)
                st.dataframe(df_rs, use_container_width=True)
            else:
                st.info("Tilføj flere tickere ud over dit benchmark for at generere RRG-kortet.")
else:
    st.warning("Vælg eller tilføj mindst én ticker i menuen til venstre.")
