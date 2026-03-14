import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Page Configuration
st.set_page_config(page_title="Momentum Scanner", layout="wide")

st.title("📈 Momentum & Breakout Scanner")
st.markdown("Upload your CSV file with a **Symbol** column to analyze performance based on **Closing Prices**.")

def generate_unified_dashboard(ticker_list):
    end_date = datetime.now()
    # Buffer to ensure we have enough history for the 1Y calculation
    start_date = end_date - timedelta(days=450)

    try:
        # Download data
        raw_data = yf.download(ticker_list, start=start_date, end=end_date, auto_adjust=False, progress=False)
        
        if raw_data.empty:
            return None

        # Multi-index handling
        if len(ticker_list) > 1:
            prices_df = raw_data['Adj Close']
            volume_df = raw_data['Volume']
        else:
            prices_df = raw_data['Adj Close'].to_frame(name=ticker_list[0])
            volume_df = raw_data['Volume'].to_frame(name=ticker_list[0])

    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

    intervals = {
        '1D': 2, '1W': 7, '1M': 30, '3M': 90, '6M': 180, '1Y': 365
    }

    results = []
    for ticker in ticker_list:
        if ticker in prices_df.columns:
            prices = prices_df[ticker].dropna()
            volumes = volume_df[ticker].dropna()

            # Need history for volume and 1Y price
            if len(prices) < 250: continue

            curr_price = prices.iloc[-1]
            row = {'Stock': ticker.replace('.NS', '')}

            # RVOL (Current Volume / 20-Day Avg Volume)
            avg_vol_20d = volumes.iloc[-21:-1].mean()
            row['RVOL'] = round(volumes.iloc[-1] / avg_vol_20d, 2) if avg_vol_20d > 0 else 0

            all_rets = []
            for label, days in intervals.items():
                target_date = end_date - timedelta(days=days)
                
                # Fetch price at start of interval
                prev_price = prices.asof(target_date)
                
                # Special case for 1D (previous trading day)
                if label == '1D' and len(prices) >= 2:
                    prev_price = prices.iloc[-2]

                # Return calculation
                ret = round(((curr_price / prev_price) - 1) * 100, 2) if pd.notna(prev_price) and prev_price != 0 else 0
                row[f'{label} %'] = ret
                all_rets.append(ret)

                # --- NEW BREAKOUT LOGIC (CLOSE BASED) ---
                # Look at all closes from the target date up to the day BEFORE today
                period_history = prices[prices.index >= target_date]
                if len(period_history) > 1:
                    # Highest closing price in the lookback period
                    max_close_in_period = period_history.iloc[:-1].max() 
                    row[f'{label} BO'] = "★" if curr_price >= max_close_in_period else "-"
                else:
                    row[f'{label} BO'] = "-"

            row['Score'] = round(sum(all_rets) / len(all_rets), 2)
            results.append(row)

    return pd.DataFrame(results).sort_values(by='Score', ascending=False)

# File Uploader
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is not None:
    try:
        input_df = pd.read_csv(uploaded_file)
        input_df.columns = input_df.columns.str.strip()

        if 'Symbol' not in input_df.columns:
            st.error("CSV must contain a 'Symbol' column.")
        else:
            symbols = input_df['Symbol'].dropna().unique().tolist()
            symbols = [str(s).strip().upper() for s in symbols]
            symbols = [s if s.endswith('.NS') else f"{s}.NS" for s in symbols]

            with st.spinner(f'Analyzing {len(symbols)} stocks...'):
                final_df = generate_unified_dashboard(symbols)

            if final_df is not None and not final_df.empty:
                st.success("Analysis Complete!")
                
                # Styling
                styled_df = final_df.style.background_gradient(
                    subset=['Score', '1M %', '3M %', '6M %'], 
                    cmap='RdYlGn'
                )

                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    hide_index=True
                )

                # Download Button
                csv = final_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Results as CSV",
                    data=csv,
                    file_name=f"Analyzed_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime='text/csv',
                )
    except Exception as e:
        st.error(f"Error processing file: {e}")