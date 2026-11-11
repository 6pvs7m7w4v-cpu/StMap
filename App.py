import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="Stock-Map / RRG", layout="wide")

st.title("📊 Stock-Map: Tema Watch")

st.sidebar.header("Indstillinger")
watchlist_valgt = st.sidebar.selectbox("Vælg Watchlist", ["Tema Watch"])
hale_længde = st.sidebar.slider("Hale-længde (uger)", 1, 30, 11)

# Brug standard-tickere uden .DE for at sikre stabile data fra start
tickers = ["SPY", "QQQ", "SMH", "ACWI", "XLK"]

st.write("Henter data for tickere...")

data_list = []
for t in tickers:
    try:
        df = yf.download(t, period="1y", interval="1wk", progress=False)
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df = df.xs(t, axis=1, level=1)
            close_col = 'Close' if 'Close' in df.columns else df.columns[0]
            s = df[close_col].dropna()
            if not s.empty:
                temp_df = pd.DataFrame({t: s})
                data_list.append(temp_df)
    except Exception as e:
        st.sidebar.warning(f"Kunne ikke hente {t}: {e}")

if data_list:
    df_all = pd.concat(data_list, axis=1).dropna(how="all")
    st.success("Data hentet succesfuldt!")
    st.line_chart(df_all)
else:
    st.error("Kunne ikke hente data for nogen af tickerne.")
