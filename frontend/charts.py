import streamlit as st
import matplotlib.pyplot as plt

def render_charts(results):
    df = results["data"]
    equity = results["equity_curve"]

    st.subheader("📈 Price Chart")

    fig, ax = plt.subplots()
    ax.plot(df["Close"])
    ax.set_title("Price")

    # st.pyplot(fig, use_container_width=True)

    st.subheader("💰 Equity Curve")

    fig2, ax2 = plt.subplots()
    ax2.plot(equity)
    ax2.set_title("Equity Curve")

    # st.pyplot(fig2, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        st.pyplot(fig, use_container_width=True)

    with col2:
        st.pyplot(fig2, use_container_width=True)