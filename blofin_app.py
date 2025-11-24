import streamlit as st
import requests
import pandas as pd
import time

# --- Configuratie ---
st.set_page_config(page_title="Blofin Multi-Timeframe Scanner", layout="wide")
BASE_URL = "https://openapi.blofin.com"

# --- Functies ---

@st.cache_data(ttl=300)
def get_futures_symbols():
    """Haalt alle beschikbare futures paren op."""
    url = f"{BASE_URL}/api/v1/market/instruments"
    try:
        response = requests.get(url)
        data = response.json()
        symbols = [item['instId'] for item in data['data'] if item['instType'] == 'SWAP']
        return symbols
    except Exception:
        return []

def get_candle_stats(symbol, bar_interval):
    """
    Haalt data op voor een specifieke tijdlijn (bijv '5m').
    Geeft terug: Huidige Prijs, Percentage Verschil
    """
    url = f"{BASE_URL}/api/v1/market/candles"
    
    params = {
        'instId': symbol,
        'bar': bar_interval,
        'limit': 1 # We hebben alleen de allerlaatste/huidige candle nodig
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if 'data' in data and len(data['data']) > 0:
            latest = data['data'][0]
            open_price = float(latest[1])
            current_price = float(latest[4])
            
            if open_price == 0: return 0.0, 0.0
            
            change_pct = ((current_price - open_price) / open_price) * 100
            return current_price, change_pct
            
        return 0.0, 0.0
    except Exception:
        return 0.0, 0.0

# --- De App Interface ---

st.title("📊 Blofin Multi-Scanner")
st.write("Live overzicht van 5m, 15m en 1u prestaties.")

# Instellingen in de zijbalk
st.sidebar.header("Instellingen")
limit_coins = st.sidebar.slider("Aantal munten scannen", 10, 50, 20)

if st.sidebar.button("Start Scan"):
    status_text = st.empty()
    progress_bar = st.progress(0)
    
    all_symbols = get_futures_symbols()
    symbols_to_scan = all_symbols[:limit_coins]
    
    results = []
    
    status_text.write("Data ophalen... even geduld.")
    
    for i, symbol in enumerate(symbols_to_scan):
        # We halen 3 keer data op per munt
        price, change_5m = get_candle_stats(symbol, "5m")
        _, change_15m = get_candle_stats(symbol, "15m")
        _, change_1h = get_candle_stats(symbol, "1H")
        
        results.append({
            "Munt": symbol,
            "Prijs ($)": price,
            "5m %": change_5m,
            "15m %": change_15m,
            "1u %": change_1h
        })
        
        # Update balk
        progress_bar.progress((i + 1) / len(symbols_to_scan))
        time.sleep(0.05) # Korte pauze
        
    # Maak de tabel
    df = pd.DataFrame(results)
    
    # Sorteer
    df = df.sort_values(by="15m %", ascending=False)
    
    status_text.write(f"Scan voltooid! {limit_coins} munten gecheckt.")
    
    # Interactieve tabel tonen
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "Prijs ($)": st.column_config.NumberColumn(format="$ %.4f"),
            "5m %": st.column_config.NumberColumn(format="%.2f %%"),
            "15m %": st.column_config.NumberColumn(format="%.2f %%"),
            "1u %": st.column_config.NumberColumn(format="%.2f %%"),
        },
        hide_index=True
    )

else:

    st.info("Druk op 'Start Scan' in de zijbalk om te beginnen.")
