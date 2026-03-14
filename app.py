import streamlit as st
import yfinance as yf
import pandas as pd
import os
from datetime import datetime, timedelta

# Page Configuration
st.set_page_config(page_title="Momentum & Fundamentals Scanner", layout="wide")

st.title("📈 Momentum & Fundamentals Scanner")

# --- SIDEBAR SETTINGS ---
st.sidebar.header("Data Source")
source_option = st.sidebar.radio(
    "Select Input Method:",
    ("Use Existing Project CSVs", "Upload New CSV")
)

DATA_FOLDER = "data"
selected_file = None

if source_option == "Use Existing Project CSVs":
    if os.path.exists(DATA_FOLDER):
        files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.csv')]
        if files:
            selected_file_name = st.sidebar.selectbox("Choose a preset file:", files)
            selected_file = os.path.join(DATA_FOLDER, selected_file_name)
        else:
            st.sidebar.warning("No CSV files found in 'data' folder.")
    else:
        st.sidebar.error("Folder 'data' not found in project.")
else:
    uploaded_file = st.sidebar.file_uploader("Upload your Symbol CSV", type="csv")
    if uploaded_file:
        selected_file = uploaded_file

def get_fundamentals(ticker_list):
    """Fetches P/E, EPS, and PEG for a list of tickers."""
    data = {}
    for ticker in ticker_list:
        try:
            info = yf.Ticker(ticker).info
            data[ticker] = {
                'EPS': info.get('trailingEps', 0),
                'P/E': info.get('trailingPE', 0),
                'PEG': info.get('pegRatio', 0)
            }
        except:
            data[ticker] = {'EPS': 0, 'P/E': 0, 'PEG': 0}
    return data

def generate_unified_dashboard(ticker_list):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=450)

    try:
        # 1. Fetch Price Data
        raw_data = yf.download(ticker_list, start=start_date, end=end_date, auto_adjust=False, progress=False)
        if raw_data.empty: return None

        if len(ticker_list) > 1:
            prices_df = raw_data['Adj Close']
            volume_df = raw_data['Volume']
        else:
            prices_df = raw_data['Adj Close'].to_frame(name=ticker_list[0])
            volume_df = raw_data['Volume'].to_frame(name=ticker_list[0])
        
        # 2. Fetch Fundamental Data
        fundamental_data = get_fundamentals(ticker_list)

    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

    intervals = {'1D': 2, '1W': 7, '1M': 30, '3M': 90, '6M': 180, '1Y': 365}
    results = []

    for ticker in ticker_list:
        if ticker in prices_df.columns:
            prices = prices_df[ticker].dropna()
            volumes = volume_df[ticker].dropna()
            if len(prices) < 250: continue

            curr_price = prices.iloc[-1]
            f = fundamental_data.get(ticker, {'EPS': 0, 'P/E': 0, 'PEG': 0})
            
            row = {
                'Stock': ticker.replace('.NS', ''),
                'EPS': f['EPS'],
                'P/E': round(f['P/E'], 2) if f['P/E'] else 0,
                'PEG': f['PEG']
            }

            # RVOL
            avg_vol_20d = volumes.iloc[-21:-1].mean()
            row['RVOL'] = round(volumes.iloc[-1] / avg_vol_20d, 2) if avg_vol_20d > 0 else 0

            all_rets = []
            for label, days in intervals.items():
                target_date = end_date - timedelta(days=days)
                prev_price = prices.asof(target_date)
                if label == '1D' and len(prices) >= 2: prev_price = prices.iloc[-2]

                ret = round(((curr_price / prev_price) - 1) * 100, 2) if pd.notna(prev_price) and prev_price != 0 else 0
                row[f'{label} %'] = ret
                all_rets.append(ret)

                # Close-based Breakout
                period_history = prices[prices.index >= target_date]
                if len(period_history) > 1:
                    max_close = period_history.iloc[:-1].max() 
                    row[f'{label} BO'] = "★" if curr_price >= max_close else "-"
                else:
                    row[f'{label} BO'] = "-"

            row['Score'] = round(sum(all_rets) / len(all_rets), 2)
            results.append(row)

    return pd.DataFrame(results).sort_values(by='Score', ascending=False)

# --- MAIN EXECUTION ---
if selected_file:
    try:
        input_df = pd.read_csv(selected_file)
        input_df.columns = input_df.columns.str.strip()
        if 'Symbol' not in input_df.columns:
            st.error("CSV must contain a 'Symbol' column.")
        else:
            symbols = [str(s).strip().upper() for s in input_df['Symbol'].dropna().unique()]
            symbols = [s if s.endswith('.NS') else f"{s}.NS" for s in symbols]

            if st.button("Run Analysis"):
                with st.spinner(f'Fetching momentum and fundamentals for {len(symbols)} stocks...'):
                    final_df = generate_unified_dashboard(symbols)

                if final_df is not None and not final_df.empty:
                    st.success("Analysis Complete!")
                    
                    # Reorder columns to put fundamentals near the name
                    cols = ['Stock', 'Score', 'P/E', 'EPS', 'PEG', 'RVOL'] + [c for c in final_df.columns if '%' in c or 'BO' in c]
                    final_df = final_df[cols]

                    st.dataframe(
                        final_df.style.background_gradient(subset=['Score', '1M %', '3M %'], cmap='RdYlGn'),
                        use_container_width=True, hide_index=True
                    )
                    
                    csv = final_df.to_csv(index=False).encode('utf-8')
                    st.download_button("Download Results", data=csv, file_name="momentum_fundamentals.csv", mime='text/csv')
    except Exception as e:
        st.error(f"Error: {e}")