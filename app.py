import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime, timedelta

# Page Configuration
st.set_page_config(page_title="Momentum Quadrant Scanner", layout="wide")

st.title("📈 Momentum vs. Valuation Dashboard")

# --- SIDEBAR: DATA SOURCE ---
st.sidebar.header("Settings")
source_option = st.sidebar.radio("Select Input Method:", ("Project CSVs", "Upload New CSV"))

DATA_FOLDER = "data"
selected_file = None

if source_option == "Project CSVs":
    if os.path.exists(DATA_FOLDER):
        files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.csv')]
        if files:
            selected_file_name = st.sidebar.selectbox("Choose a preset file:", files)
            selected_file = os.path.join(DATA_FOLDER, selected_file_name)
else:
    uploaded_file = st.sidebar.file_uploader("Upload your Symbol CSV", type="csv")
    if uploaded_file:
        selected_file = uploaded_file

# --- PLOTTING FUNCTION ---
def plot_quadrant_st(df):
    if df.empty: return
    plot_df = df[df['T_PE'] > 0].copy()
    if plot_df.empty: return

    fig, ax = plt.subplots(figsize=(10, 6))
    pe_threshold = plot_df['T_PE'].median()
    momentum_threshold = 0

    ax.scatter(plot_df['T_PE'], plot_df['Score'], s=plot_df['RVOL']*50, alpha=0.6, edgecolors='black')

    for i, row in plot_df.iterrows():
        ax.annotate(row['Stock'], (row['T_PE'], row['Score']), fontsize=8)

    ax.axvline(x=pe_threshold, color='red', linestyle='--', alpha=0.3)
    ax.axhline(y=momentum_threshold, color='red', linestyle='--', alpha=0.3)

    # Quadrant Labels
    ax.text(pe_threshold*0.5, plot_df['Score'].max(), 'THE LEADER', color='green', fontweight='bold')
    ax.text(pe_threshold*1.5, plot_df['Score'].max(), 'THE BUBBLE', color='orange', fontweight='bold')
    ax.text(pe_threshold*0.5, plot_df['Score'].min(), 'TURNAROUND', color='blue', fontweight='bold')
    ax.text(pe_threshold*1.5, plot_df['Score'].min(), 'VALUE TRAP', color='red', fontweight='bold')

    ax.set_xscale('log')
    ax.set_xlabel('Trailing P/E (Log Scale)')
    ax.set_ylabel('Momentum Score')
    st.pyplot(fig)

# --- CORE PROCESSING ENGINE ---
def generate_unified_dashboard(ticker_list):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=450)
    
    try:
        raw_data = yf.download(ticker_list, start=start_date, end=end_date, auto_adjust=False, progress=False)
        prices_df = raw_data['Adj Close'] if len(ticker_list) > 1 else raw_data['Adj Close'].to_frame(name=ticker_list[0])
        volume_df = raw_data['Volume'] if len(ticker_list) > 1 else raw_data['Volume'].to_frame(name=ticker_list[0])
    except Exception as e:
        st.error(f"Fetch Error: {e}")
        return None

    intervals = {'1D': 2, '1W': 7, '1M': 30, '3M': 90, '6M': 180, '1Y': 365}
    results = []

    for ticker in ticker_list:
        if ticker in prices_df.columns:
            prices = prices_df[ticker].dropna()
            volumes = volume_df[ticker].dropna()
            if len(prices) < 22: continue

            curr_price = prices.iloc[-1]
            row = {'Stock': ticker.replace('.NS', '')}

            # Fundamentals & PEG Fallback
            try:
                info = yf.Ticker(ticker).info
                t_pe = info.get('trailingPE', 0)
                f_pe = info.get('forwardPE', 0)
                t_eps = info.get('trailingEps', 0)
                f_eps = info.get('forwardEps', 0)

                row['T_PE'] = t_pe if t_pe else 0
                row['F_PE'] = f_pe if f_pe else 0
                row['T_EPS'] = t_eps
                row['F_EPS'] = f_eps

                growth = ((f_eps / t_eps) - 1) * 100 if t_eps and f_eps and t_eps > 0 else 0
                yf_peg = info.get('pegRatio')
                row['PEG'] = yf_peg if yf_peg and yf_peg != 0 else (t_pe / growth if t_pe and growth > 0 else 0)
                row['E_Growth (Forward < Trailing)'] = "YES" if (f_pe and t_pe and 0 < f_pe < t_pe) else "NO"
            except:
                row.update({'T_PE':0, 'F_PE':0, 'PEG':0, 'T_EPS':0, 'F_EPS':0, 'E_Growth (Forward < Trailing)':"N/A"})

            # RVOL & Momentum
            row['RVOL'] = round(volumes.iloc[-1] / volumes.iloc[-21:-1].mean(), 2) if len(volumes) > 21 else 0
            
            all_rets = []
            for label, days in intervals.items():
                ref_date = end_date - timedelta(days=days)
                prev_price = prices.asof(ref_date)
                if label == '1D' and len(prices) >= 2: prev_price = prices.iloc[-2]
                
                ret = round(((curr_price / prev_price) - 1) * 100, 2) if pd.notna(prev_price) and prev_price != 0 else 0
                row[f'{label}%'] = ret
                all_rets.append(ret)
                row[f'{label}BO'] = "★" if curr_price >= prices[prices.index >= ref_date].max() else "-"

            row['Score'] = round(sum(all_rets) / len(all_rets), 2)
            results.append(row)

    return pd.DataFrame(results).sort_values(by='Score', ascending=False)

# --- EXECUTION ---
if selected_file:
    input_df = pd.read_csv(selected_file)
    if st.button("🚀 Run Analysis"):
        symbols = [s if str(s).endswith('.NS') else f"{s}.NS" for s in input_df['Symbol'].dropna()]
        
        with st.spinner("Analyzing Market Data..."):
            res_df = generate_unified_dashboard(symbols)

        if res_df is not None:
            # 1. Plotting
            st.subheader("Momentum vs. Valuation Quadrant")
            plot_quadrant_st(res_df)

            # 2. High Conviction Filter
            st.subheader("🔥 High Conviction Picks")
            high_conv = res_df[(res_df['Score'] > 0) & (res_df['E_Growth (Forward < Trailing)'] == "YES") & (res_df['PEG'] > 0) & (res_df['PEG'] < 1.5)]
            st.dataframe(high_conv, use_container_width=True, hide_index=True)

            # 3. Full Table
            st.subheader("All Results")
            st.dataframe(res_df.style.background_gradient(subset=['Score', '1M%', '3M%'], cmap='RdYlGn'), use_container_width=True, hide_index=True)