import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import wrds
import numpy as np
import atexit
from datetime import datetime

# ------------------- Page Configuration -------------------
st.set_page_config(
    page_title="Financial Analytics Terminal",
    page_icon="📊",
    layout="wide"
)

plt.rcParams['font.sans-serif'] = ['Arial', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

# ------------------- Sidebar -------------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3059/3059978.png", width=100)
    st.title("📊 Decision Support")
    st.markdown("---")
    
    data_source = st.radio("Select Data Source", ["WRDS Cloud", "Local CSV Upload"])
    
    if data_source == "WRDS Cloud":
        st.subheader("🔧 WRDS Credentials")
        wrds_user = st.text_input("Username"，value="")
        wrds_pass = st.text_input("Password", type="password")
    
    st.markdown("---")
    st.caption("© 2026 ACC102 Professional Project")

# ------------------- Main Header -------------------
st.title("📊 Corporate Financial Intelligence System")
st.info("Integrated DuPont Analysis & Solvency Monitoring Module (CSMAR Database)")

# ------------------- Data Connection -------------------
if data_source == "WRDS Cloud":
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Connect to WRDS", use_container_width=True):
            with st.spinner("Authenticating with financial database..."):
                try:
                    conn = wrds.Connection(wrds_username=wrds_user, wrds_password=wrds_pass)
                    st.session_state["conn"] = conn
                    st.success("✅ Connection Established")
                except Exception as e:
                    st.error(f"Connection Failed: {e}")
    with col2:
        if st.button("❌ Disconnect", use_container_width=True):
            if "conn" in st.session_state:
                st.session_state["conn"].close()
                del st.session_state["conn"]
                st.success("✅ Session Terminated")
else:
    uploaded_file = st.file_uploader("Upload CSV (CSMAR Format)", type="csv")
    if uploaded_file is not None:
        df_local = pd.read_csv(uploaded_file)
        required = ["total_assets","total_liabilities","equity","net_profit","revenue","accper"]
        missing = [x for x in required if x not in df_local.columns]
        if missing:
            st.error(f"Missing fields: {', '.join(missing)}")
        else:
            st.session_state["df"] = df_local
            st.success("✅ Local Data Synchronized")

# ------------------- Query Panel -------------------
if data_source == "WRDS Cloud" and "conn" in st.session_state:
    st.subheader("📥 Data Acquisition")
    with st.expander("Query Parameters", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            stkcd = st.text_input("Stock Code", "600900")
        with col2:
            start_year = st.number_input("Start Year", 2015, 2026, 2020)
        with col3:
            end_year = st.number_input("End Year", 2015, 2026, 2025)
            
        if st.button("🚀 Execute Data Retrieval", use_container_width=True):
            with st.spinner("Extracting Financial Data..."):
                sql = f"""
                    SELECT a.stkcd, a.accper, 
                           a.a001000000 AS total_assets, 
                           a.a002000000 AS total_liabilities, 
                           a.a003000000 AS equity,
                           b.b001100000 AS net_profit,
                           b.b001000000 AS revenue
                    FROM csmar.fs_combas a
                    LEFT JOIN csmar.fs_comins b 
                      ON a.stkcd = b.stkcd AND a.accper = b.accper
                    WHERE a.stkcd = '{stkcd}'
                      AND a.accper BETWEEN '{start_year}-01-01' AND '{end_year}-12-31'
                    ORDER BY a.accper
                """
                try:
                    df = st.session_state["conn"].raw_sql(sql)
                    df = df.drop_duplicates(subset=["accper"], keep="last")
                    st.session_state["df"] = df
                    st.success(f"✅ Retrieved {len(df)} Valid Reports")
                except Exception as e:
                    st.error(f"SQL Execution Error: {e}")

# ------------------- Analytics Engine -------------------
if "df" in st.session_state and not st.session_state["df"].empty:
    df = st.session_state["df"].copy()

    # Ratio Calculation with zero-division protection
    df_calc = df.copy()
    df_calc["Debt_Ratio"] = (df_calc["total_liabilities"] / df_calc["total_assets"].replace(0, np.nan) * 100).round(2)
    df_calc["ROE"] = (df_calc["net_profit"] / df_calc["equity"].replace(0, np.nan) * 100).round(2)
    df_calc["Net_Margin"] = (df_calc["net_profit"] / df_calc["revenue"].replace(0, np.nan) * 100).round(2)
    df_calc["Asset_Turnover"] = (df_calc["revenue"] / df_calc["total_assets"].replace(0, np.nan)).round(3)

    st.markdown("---")
    st.subheader("🎯 Key Performance Indicators (KPIs)")

    if len(df_calc) >= 1:
        latest = df_calc.iloc[-1]
        prev = df_calc.iloc[-2] if len(df_calc) >= 2 else latest

        m1, m2, m3, m4 = st.columns(4)
        
        def format_kpi(value, change):
            if pd.isna(value):
                return "—", "—"
            return f"{value}%", f"{round(change,2)}%" if not pd.isna(change) else "—"

        debt_val, debt_change = format_kpi(latest['Debt_Ratio'], latest['Debt_Ratio']-prev['Debt_Ratio'])
        roe_val, roe_change = format_kpi(latest['ROE'], latest['ROE']-prev['ROE'])
        nm_val = f"{latest['Net_Margin']}%" if not pd.isna(latest['Net_Margin']) else "—"
        at_val = f"{latest['Asset_Turnover']}x" if not pd.isna(latest['Asset_Turnover']) else "—"
        
        m1.metric("Debt-to-Asset Ratio", debt_val, debt_change)
        m2.metric("Return on Equity (ROE)", roe_val, roe_change)
        m3.metric("Net Profit Margin", nm_val, "Latest Report")
        m4.metric("Asset Turnover", at_val, "Operational")

    # Visualization Module
    st.markdown("---")
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("📈 DuPont Analysis Trends")
        dupont_option = st.selectbox("Select Dimension", ["ROE", "Net Margin", "Debt Ratio"])

        fig, ax = plt.subplots(figsize=(10, 6))
        color_map = {"ROE": "#e74c3c", "Net Margin": "#2ecc71", "Debt Ratio": "#3498db"}
        mapping = {"ROE": "ROE", "Net Margin": "Net_Margin", "Debt Ratio": "Debt_Ratio"}
        target_col = mapping[dupont_option]

        plot_df = df_calc.dropna(subset=[target_col]).copy()
        plot_df["accper"] = pd.to_datetime(plot_df["accper"])
        
        ax.plot(plot_df["accper"], plot_df[target_col], marker='o', color=color_map[dupont_option], linewidth=2)
        ax.set_title(f"{dupont_option} Time Series Analysis", fontsize=14)
        ax.set_ylabel("Value (%)")
        ax.grid(True, linestyle='--', alpha=0.6)
        st.pyplot(fig)

    with col_right:
        st.subheader("🔍 Financial Diagnosis")
        if not pd.isna(latest["Debt_Ratio"]):
            dr = float(latest["Debt_Ratio"])
            if dr > 70:
                st.warning("⚠️ High Leverage: Debt ratio exceeds 70%. Monitor solvency risks closely.")
            elif dr < 30:
                st.success("✅ Strong Solvency: Conservative capital structure with low leverage.")
            else:
                st.info("ℹ️ Moderate Leverage: Capital structure aligns with industry standards.")

        if not pd.isna(latest["ROE"]):
            roe = float(latest["ROE"])
            if roe > 15:
                st.success("💎 Premium Performer: ROE consistently > 15% indicates high shareholder value.")
            elif roe < 0:
                st.warning("⚠️ Negative ROE: The company is currently loss-making for shareholders.")

        st.caption("Note: Calculations are based on CSMAR raw data via WRDS. For academic research only.")

    # ------------------- Fixed Export Module -------------------
    with st.expander("View Raw Analytics Table"):
        # We fillna("N/A") ONLY for the UI table so it looks clean
        st.dataframe(df_calc.fillna("N/A"), use_container_width=True)
        
        # We export the ORIGINAL df_calc to maintain numeric integrity in CSV
        csv_buffer = df_calc.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        
        st.download_button(
            label="📥 Export Analysis (.csv)", 
            data=csv_buffer,
            file_name=f"Financial_Report_{datetime.now().strftime('%Y%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )

# ------------------- Auto-Cleanup -------------------
def close_conn():
    if "conn" in st.session_state:
        try:
            st.session_state["conn"].close()
        except:
            pass

atexit.register(close_conn)
