import yfinance as yf
import requests
from datetime import datetime, timedelta
import cohere
import os
from pathlib import Path
import pandas as pd
import numpy as np

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

COHERE_API_KEY = os.getenv("COHERE_API_KEY")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

co = cohere.Client(COHERE_API_KEY) if COHERE_API_KEY else None

def get_market_context(ticker: str, start_date: str, end_date: str) -> dict:
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    warmup_start = (start_dt - timedelta(days=300)).strftime("%Y-%m-%d")

    asset_df = yf.download(ticker, start=warmup_start, end=end_date, auto_adjust=True, progress=False)
    spy_df = yf.download("SPY", start=warmup_start, end=end_date, auto_adjust=True, progress=False)

    if asset_df.empty:
        raise ValueError(f"No data for {ticker}")

    asset_close = asset_df["Close"]
    spy_close = spy_df["Close"]

    if isinstance(asset_close, pd.DataFrame):
        asset_close = asset_close.iloc[:, 0]
    if isinstance(spy_close, pd.DataFrame):
        spy_close = spy_close.iloc[:, 0]

    asset_close = asset_close.dropna()
    spy_close = spy_close.dropna()

    if len(asset_close) < 220:
        raise ValueError("Not enough data for SMA200")

    sma_200 = asset_close.rolling(200).mean()
    latest_price = float(asset_close.iloc[-1])
    latest_sma = float(sma_200.iloc[-1])

    sma_valid = sma_200.dropna()
    slope = float((sma_valid.iloc[-1] - sma_valid.iloc[-21]) / 20)

    asset_returns = asset_close.pct_change().dropna()
    spy_returns = spy_close.pct_change().dropna()

    realized_vol = float(asset_returns.tail(30).std() * np.sqrt(252))

    aligned = pd.concat(
        [asset_returns.rename("a"), spy_returns.rename("s")],
        axis=1
    ).dropna()

    corr = float(aligned["a"].corr(aligned["s"])) if not aligned.empty else 0.0

    if latest_price > latest_sma and slope > 0:
        regime = "trending"
        trend_direction = "up"
    elif latest_price < latest_sma and slope < 0:
        regime = "trending"
        trend_direction = "down"
    else:
        regime = "ranging"
        trend_direction = "sideways"

    if regime == "trending" and realized_vol < 0.6:
        strategy_bias = "momentum"
    elif regime == "ranging":
        strategy_bias = "mean_reversion"
    else:
        strategy_bias = "neutral"

    reasoning = (
        f"Price is {'above' if latest_price > latest_sma else 'below'} SMA200, "
        f"slope={slope:.4f}, vol={realized_vol:.2f}, corr_to_spy={corr:.2f}. "
        f"Bias={strategy_bias}."
    )

    return {
        "ticker": ticker,
        "start_date": start_date,
        "end_date": end_date,
        "regime": regime,
        "trend_direction": trend_direction,
        "sma_200_slope": round(slope, 6),
        "realized_vol_30d": round(realized_vol, 4),
        "correlation_to_spy": round(corr, 4),
        "strategy_bias": strategy_bias,
        "reasoning": reasoning,
    }

#llm summarisation
def summarise_with_cohere(news_articles, ticker, revenue, eps):
    if co is None:
        return "AI summary unavailable because COHERE_API_KEY is not configured."

    news_text = "\n".join([f"- {a['title']}" for a in news_articles])

    if not news_text.strip():
        news_text = "No recent news available."

    prompt = (
        f"{ticker} has revenue ${revenue:,.2f} and EPS ${eps:.2f}.\n"
        f"Recent news:\n{news_text}\n\n"
        "Summarise this in 2-3 sentences."
    )

    try:
        response = co.chat(
            model="command-a-03-2025",
            message=prompt,
        )
        return response.text.strip()
    except Exception as exc:
        return f"AI summary unavailable: {exc}"

def get_market_intel(ticker: str):
    try:
        # Stock data
        stock = yf.Ticker(ticker)
        info = stock.info
        revenue = info.get("totalRevenue", 0)
        eps = info.get("trailingEps", 0)

        # News
        end = datetime.now()
        start = end - timedelta(days=7)
        url = "https://finnhub.io/api/v1/company-news"
        params = {
            "symbol": ticker,
            "from": start.strftime("%Y-%m-%d"),
            "to": end.strftime("%Y-%m-%d"),
            "token": FINNHUB_API_KEY
        }
        articles = []
        if FINNHUB_API_KEY:
            res = requests.get(url, params=params, timeout=20)
            parsed = res.json()
            if isinstance(parsed, list):
                articles = parsed
            else:
                articles = []

        news = []
        for article in articles[:5]:
            title = article.get("headline") or article.get("summary") or "No Title"
            url = article.get("url")
            news.append({"title": title, "url": url})

        if not news:
            news = [{"title": "No news available", "url": ""}]

        # Sentiment
        positive_keywords = ["gain", "growth", "surge", "positive", "expansion", "record"]
        negative_keywords = ["loss", "decline", "drop", "negative", "reduction", "miss"]

        sentiment = "Neutral"
        for item in news:
            title_lower = item['title'].lower()
            if any(word in title_lower for word in positive_keywords):
                sentiment = "Positive"
                break
            elif any(word in title_lower for word in negative_keywords):
                sentiment = "Negative"
                break

        # LLM summary
        llm_summary = summarise_with_cohere(news, ticker, revenue, eps)

        return {
            "ticker": ticker,
            "revenue": revenue,
            "eps": eps,
            "news": news,
            "sentiment": sentiment,
            "llm_summary": llm_summary
        }

    except Exception as e:
        return {"error": str(e)}
