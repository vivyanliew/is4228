from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

from app.routers import router
from app.agent_router import agent_router

app = FastAPI(title="Backtesting API")

app.include_router(router)
app.include_router(agent_router)
