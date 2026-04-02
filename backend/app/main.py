from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

from app.routers import router

app = FastAPI(title="Backtesting API")

app.include_router(router)