"""
dashboard.py
Streamlit dashboard over your local whoop.db.

Run:
    streamlit run dashboard.py
"""
import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="WHOOP Dashboard", layout="wide")

conn = sqlite3.connect("whoop.db")

recovery_df = pd.read_sql(
    """
    SELECT r.recovery_score, r.resting_heart_rate, r.hrv_rmssd_milli,
           c.strain, c.start AS cycle_start
    FROM recovery r
    JOIN cycles c ON r.cycle_id = c.id
    ORDER BY c.start
    """, conn
)
sleep_df = pd.read_sql(
    "SELECT * FROM sleep ORDER BY start", conn
)
workouts_df = pd.read_sql(
    "SELECT * FROM workouts ORDER BY start", conn
)

st.title("My WHOOP Data")
st.caption("Personal biometric pipeline — WHOOP API → SQLite → Streamlit")

if recovery_df.empty:
    st.warning("No data yet. Run `python3 pull_data.py` first.")
else:
    col1, col2, col3 = st.columns(3)
    col1.metric("Avg Recovery", f"{recovery_df['recovery_score'].mean():.0f}%")
    col2.metric("Avg Resting HR", f"{recovery_df['resting_heart_rate'].mean():.0f} bpm")
    col3.metric("Avg Strain", f"{recovery_df['strain'].mean():.1f}")

    st.subheader("Recovery over time")
    fig = px.line(recovery_df, x="cycle_start", y="recovery_score", markers=True)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Strain vs. Recovery")
    fig2 = px.scatter(recovery_df, x="strain", y="recovery_score",
                       trendline="ols", hover_data=["cycle_start"])
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("HRV over time")
    fig3 = px.line(recovery_df, x="cycle_start", y="hrv_rmssd_milli", markers=True)
    st.plotly_chart(fig3, use_container_width=True)

    if not sleep_df.empty:
        st.subheader("Sleep performance over time")
        fig4 = px.bar(sleep_df, x="start", y="sleep_performance_percentage")
        st.plotly_chart(fig4, use_container_width=True)

    if not workouts_df.empty:
        st.subheader("Workouts logged")
        st.dataframe(workouts_df[["start", "sport_name", "strain", "average_heart_rate"]])

st.caption("Note: with only a few days of data, trend lines are illustrative, not statistically robust yet.")