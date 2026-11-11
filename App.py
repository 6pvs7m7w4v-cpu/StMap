import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Mit Eget Stock-Map", layout="wide")

# --- WATCHLISTER ---
WATCHLISTS = {
    "Pension (Depot)": {
        "benchmark": "EXSA.DE",
        "tickers": ["EXV6.DE", "ESIF.DE", "EXV2.DE", "CBUF.DE", "ALAT.DE"]
    },
    "EU Sektorer": {
        "benchmark": "EXSA.DE",
        "tickers": ["EXV6.DE", "ESIF.DE", "EXV2.DE", "EXH1.DE", "EXH3.DE", "EXH4.DE", "EXH9.DE", "ESIS.DE"]
    },
    "Tema Watch": {
        "benchmark": "EXSA.DE",
        "tickers": ["4GLD.DE", "VZLC.DE", "NUCL.DE", "SMH.DE", "WCBR.DE", "RBOT.DE"]
    }
}

# --- SIDEPANEL ---
st.sidebar.title("⚙️ Indstillinger")
valgt_liste_navn = st.sidebar.selectbox("Vælg Watchlist", list(WATCHLISTS.keys()))
tail_length = st.sidebar.slider("Hale-længde (uger)", min_value=4, max_value=20, value=11)

valgt_liste = WATCHLISTS[valgt_liste_navn]
benchmark = valgt_liste["benchmark"]
tickers = valgt_liste["tickers"]

# --- DATA HENTNING & RRG BEREGNING ---
@st.cache_data(ttl=3600)
def hent_rrg_data(tickers, benchmark, tail):
    alle = list(set(tickers + [benchmark]))
    df = yf.download(alle, period="2y", interval="1wk", progress=False)["Adj Close"]
    
    rs_ratio = pd.DataFrame()
    rs_momentum = pd.DataFrame()
    
    for t in tickers:
        rs = (df[t] / df[benchmark]) * 100
        ma = rs.rolling(window=12).mean()
        rs_ratio[t] = 100 + ((rs - ma) / ma) * 100
        rs_momentum[t] = 100 + (rs_ratio[t].pct_change() * 100)
        
    return rs_ratio.tail(tail), rs_momentum.tail(tail)

st.title(f"📊 Stock-Map: {valgt_liste_navn}")

try:
    ratio, momentum = hent_rrg_data(tickers, benchmark, tail_length)

    # --- AUTOMATISK 270°-KROG DETEKTOR ---
    st.subheader("🔔 Krog-Alarmer")
    alarmer = []
    for t in tickers:
        r_nu, m_nu = ratio[t].iloc[-1], momentum[t].iloc[-1]
        r_forig, m_forig = ratio[t].iloc[-2], momentum[t].iloc[-2]
        
        if r_nu < 100 and m_nu > 100 and m_nu > m_forig:
            alarmer.append(f"🟢 **{t}** viser en potentiel **270°-krog** opad fra rød/gul zone!")
            
    if alarmer:
        for a in alarmer:
            st.success(a)
    else:
        st.info("Ingen nye 270°-kroge bekræftet i dag. Krudtet holdes tørt.")

    # --- PLOTLY GRAF ---
    fig = go.Figure()

    for t in tickers:
        x_vals = ratio[t].values
        y_vals = momentum[t].values
        
        fig.add_trace(go.Scatter(
            x=x_vals, y=y_vals, mode='lines+markers', name=t,
            line=dict(width=2),
            marker=dict(size=[5]*(len(x_vals)-1) + [11])
        ))

    fig.add_hline(y=100, line_dash="dash", line_color="gray")
    fig.add_vline(x=100, line_dash="dash", line_color="gray")

    fig.update_layout(
        xaxis_title="RS-Ratio (Relativ Styrke vs EXSA)",
        yaxis_title="RS-Momentum (Vinkel)",
        height=650,
        showlegend=True
    )

    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Kunne ikke hente data fra Xetra: {e}")
