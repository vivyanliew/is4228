import requests
import streamlit as st

st.set_page_config(page_title="Agent 6 Test", page_icon="📈")

st.title("Agent 6 — Market Context Test")

ticker = st.text_input("Ticker", value="BTC-USD")
start_date = st.text_input("Start Date", value="2022-01-01")
end_date = st.text_input("End Date", value="2024-12-31")

if st.button("Run Agent 6"):
    with st.spinner("Fetching market context..."):
        try:
            response = requests.post(
                "http://127.0.0.1:8000/agent/market-context",
                json={
                    "ticker": ticker,
                    "start_date": start_date,
                    "end_date": end_date,
                },
                timeout=30,
            )

            data = response.json()

            if response.status_code != 200:
                st.error(data.get("detail", "Request failed"))
            else:
                st.success("Market context fetched successfully")

                st.subheader("Summary")
                col1, col2 = st.columns(2)

                with col1:
                    st.metric("Market Regime", data["regime"])
                    st.metric("Trend Direction", data["trend_direction"])
                    st.metric("Strategy Bias", data["strategy_bias"])

                with col2:
                    st.metric("30D Realized Vol", data["realized_vol_30d"])
                    st.metric("SPY Correlation", data["correlation_to_spy"])
                    st.metric("SMA 200 Slope", data["sma_200_slope"])

                st.subheader("Reasoning")
                st.write(data["reasoning"])

                with st.expander("Raw JSON"):
                    st.json(data)

        except Exception as e:
            st.error(f"Error: {e}")