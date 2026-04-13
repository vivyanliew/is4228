import yfinance as yf
import requests
from datetime import datetime, timedelta
import cohere
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

COHERE_API_KEY = os.getenv("COHERE_API_KEY")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

co = cohere.Client(COHERE_API_KEY) if COHERE_API_KEY else None

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
