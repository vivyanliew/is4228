from fastapi import FastAPI

from app.routers import router

app = FastAPI(title="Backtesting API")

app.include_router(router)