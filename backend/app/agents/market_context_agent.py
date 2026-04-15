from app.market_intel import get_market_context


class MarketContextAgent:
    def run(self, ticker: str, start_date: str, end_date: str):
        return get_market_context(ticker, start_date, end_date)