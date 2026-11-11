import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

# Opsætning af siden
st.set_page_config(page_title="Stock-Map / RRG", layout="wide")

st.title("📊 Stock-Map: Tema Watch")

# Standard-watchlists
DEFAULT_WATCHLISTS = {
    "Tema Watch": ["ACWI", "QQQ", "SMH", "SPY", "XLK"],
    "Sektor ETF'er": ["EXV6.DE", "EXV1.DE", "EXV2.DE", "EXV3.DE"],
}

# Gem watchlists i Session State, så tilføjede tickere huskes under kørsel
if "watchlists" not in st.session_state:
    st.session_state.watchlists = DEFAULT_WATCHLISTS

# SIDEBAR: Indstillinger
st.sidebar.header("Indstillinger")

# 1. Vælg watchlist
selected_watchlist_name = st.sidebar.selectbox(
    "Vælg Watchlist", 
    options=list(st.session_state.watchlists.keys())
)

current_tickers = st.session_state.watchlists[selected_watchlist_name]

# 2. Vælg / fjern tickere i den aktuelt valgte watchlist
active_tickers = st.sidebar.multiselect(
    "Aktive tickere i watchlist",
    options=current_tickers,
    default=current_tickers
)

# 3. Tilføj en helt ny ticker til den valgte watchlist
new_ticker = st.sidebar.text_input("Tilføj ny ticker (f.eks. AAPL eller EXV6.DE):").strip().upper()
if st.sidebar.button("Tilføj ticker"):
    if new_ticker and new_ticker not in current_tickers:
        st.session_state.watchlists[selected_watchlist_name].append(new_ticker)
        st.rerun()

# Hovedvisning: Hent og vis data
if active_tickers:
    st.info(f"Henter data for: {', '.join(active_tickers)}...")
    
    # Hent historiske data via yfinance (1 år)
    data = yf.download(active_tickers, period="1y")["Close"]
    
    st.success("Data hentet succesfuldt!")

    # Opret Plotly graf
    fig = go.Figure()

    # Hvis der kun er valgt 1 ticker, returnerer yfinance en Series i stedet for Dataframe
    if len(active_tickers) == 1:
        ticker = active_tickers[0]
        fig.add_trace(go.Scatter(x=data.index, y=data, mode='lines', name=ticker))
    else:
        for ticker in active_tickers:
            if ticker in data.columns:
                fig.add_trace(go.Scatter(x=data.index, y=data[ticker], mode='lines', name=ticker))

    fig.update_layout(
        xaxis_title="Dato",
        yaxis_title="Pris",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=30, b=20)
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Vælg eller tilføj mindst én ticker i menuen til venstre for at vise grafen.")
