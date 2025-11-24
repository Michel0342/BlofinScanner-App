import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime

# --- Configuratie & Styling ---
st.set_page_config(
    page_title="Blofin USDT Futures Scanner",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Basis URL van de Blofin API
BASE_URL = "https://openapi.blofin.com"

# Functie om de achtergrondkleur van de cel aan te passen (Heatmap)
def highlight_change(val):
    """Kleur cellen met een lichte achtergrond op basis van positieve/negatieve waarde."""
    if isinstance(val, (int, float)):
        if val > 0:
            # Groene achtergrond voor stijgers
            return 'background-color: #e6ffe6; color: #006600' 
        elif val < 0:
            # Rode achtergrond voor dalers
            return 'background-color: #ffe6e6; color: #cc0000'
        else:
            return 'background-color: white; color: black'
    return None

# --- Data Functies ---

@st.cache_data(ttl=300)
def get_futures_symbols():
    """Haalt alle beschikbare USDT futures paren op."""
    url = f"{BASE_URL}/api/v1/market/instruments"
    try:
        response = requests.get(url)
        data = response.json()
        
        # AANPASSING: Filter op SWAP EN '-USDT'
        symbols = [
            item['instId'] 
            for item in data['data'] 
            if item['instType'] == 'SWAP' and item['instId'].endswith('-USDT')
        ]
        
        return symbols
    except Exception:
        return []

def get_candle_stats(symbol, bar_interval):
    url = f"{BASE_URL}/api/v1/market/candles"
    params = {
        'instId': symbol,
        'bar': bar_interval,
        'limit': 1 
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

st.title("📊 Blofin USDT Futures Scanner (Heatmap Stijl)")
st.markdown("---") 

# Instellingen in de zijbalk
st.sidebar.header("Instellingen")
# AANPASSING: Limiet verhoogd naar 150
limit_coins = st.sidebar.slider("Aantal munten scannen", 10, 150, 50) 

st.sidebar.info(f"Laatste data check: {datetime.now().strftime('%H:%M:%S')} UTC")

status_text = st.empty()

if st.sidebar.button("Start Scan", use_container_width=True):
    progress_bar = st.progress(0)
    
    all_symbols = get_futures_symbols()
    symbols_to_scan = all_symbols[:limit_coins]
    
    if not symbols_to_scan:
        status_text.warning("Geen USDT Futures paren gevonden.")
        progress_bar.empty()
    else:
        results = []
        status_text.write(f"Data ophalen voor {len(symbols_to_scan)} USDT paren... even geduld.")
        start_time = time.time()
        
        for i, symbol in enumerate(symbols_to_scan):
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
            
            progress_bar.progress((i + 1) / len(symbols_to_scan))
            time.sleep(0.05)
            
        end_time = time.time()
        
        df = pd.DataFrame(results)
        df = df.sort_values(by="15m %", ascending=False)
        
        scan_time = round(end_time - start_time, 2)
        status_text.success(f"Scan voltooid! {len(symbols_to_scan)} munten gecheckt in {scan_time} seconden.")
        
        st.dataframe(
            df.style.applymap(highlight_change, subset=["5m %", "15m %", "1u %"]),
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
    status_text.info("Druk op 'Start Scan' om de live data op te halen.")
