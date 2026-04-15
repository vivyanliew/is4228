# frontend/streamlit_app.py
import streamlit as st
import requests

st.title("Market Intelligence Dashboard")

ticker = st.text_input("Enter Stock Ticker (e.g., AAPL, TSLA):").upper()

if ticker:
    st.write(f"Fetching data for: {ticker} ...")
    
    try:
        # Call your FastAPI backend
        response = requests.get(f"http://127.0.0.1:8000/market-intel/{ticker}")
        data = response.json()
        
        if "error" in data:
            st.error(f"Error fetching market intel: {data['error']}")
        else:
            st.subheader("Stock Info")
            st.write(f"**Ticker:** {data['ticker']}")
            st.write(f"**Revenue:** ${data['revenue']:,.2f}")
            st.write(f"**EPS:** ${data['eps']:.2f}")
            st.write(f"**Sentiment:** {data['sentiment']}")
            st.write(f"**Summary:** {data['summary']}")
            
            st.subheader("News")
            for article in data['news']:
                if article['url']:
                    st.markdown(f"- [{article['title']}]({article['url']})")
                else:
                    st.markdown(f"- {article['title']}")
            
            st.subheader("LLM Summary")
            st.write(data['llm_summary'])
    
    except Exception as e:
        st.error(f"Error connecting to backend: {str(e)}")