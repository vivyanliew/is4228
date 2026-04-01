from pathlib import Path
import sys

import requests
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sidebar import render_market_intel_sidebar

st.set_page_config(page_title="Market Intelligence", layout="wide")

st.title("Market Intelligence Dashboard")
st.caption("Quick company snapshot with recent news, simple sentiment tagging, and an AI-generated summary.")

params = render_market_intel_sidebar()

if "market_intel_result" not in st.session_state:
    st.session_state.market_intel_result = None

if "market_intel_ticker" not in st.session_state:
    st.session_state.market_intel_ticker = None

if params["run"]:
    if not params["ticker"]:
        st.warning("Enter a ticker in the sidebar first.")
    else:
        with st.spinner(f"Fetching market intelligence for {params['ticker']}..."):
            try:
                response = requests.get(
                    f"http://127.0.0.1:8000/market-intel/{params['ticker']}",
                    timeout=30,
                )

                if response.status_code != 200:
                    st.session_state.market_intel_result = {
                        "request_error": f"API error {response.status_code}",
                        "response_body": response.text,
                    }
                else:
                    st.session_state.market_intel_result = response.json()
                    st.session_state.market_intel_ticker = params["ticker"]
            except Exception as exc:
                st.session_state.market_intel_result = {
                    "request_error": "Backend connection failed",
                    "response_body": str(exc),
                }

data = st.session_state.market_intel_result
ticker = st.session_state.market_intel_ticker or params["ticker"]

if not data:
    st.info("Use the sidebar to enter a ticker and fetch market intelligence.")
elif "request_error" in data:
    st.error(data["request_error"])
    st.code(data["response_body"])
elif "error" in data:
    st.error(f"Market intel failed for {ticker}: {data['error']}")
else:
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Ticker", data["ticker"])
    with col2:
        st.metric("Revenue", f"${data['revenue']:,.0f}")
    with col3:
        st.metric("EPS", f"{data['eps']:.2f}")

    sentiment = data.get("sentiment", "Neutral")
    if sentiment == "Positive":
        st.success(f"Sentiment: {sentiment}")
    elif sentiment == "Negative":
        st.error(f"Sentiment: {sentiment}")
    else:
        st.info(f"Sentiment: {sentiment}")

    st.subheader("AI Summary")
    st.write(data.get("llm_summary", "No AI summary available."))

    st.subheader("Recent News")
    for article in data.get("news", []):
        title = article.get("title", "Untitled article")
        url = article.get("url", "")

        with st.container(border=True):
            st.markdown(f"**{title}**")
            if url:
                st.markdown(f"[Open article]({url})")
            else:
                st.caption("No article link available.")

    if params["show_request"]:
        st.subheader("Raw API Response")
        st.json(data)
