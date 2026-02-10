from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

import os
import json
import asyncio
import redis.asyncio as redis

from app.api.routes import router as api_router
from app.api.aggregate import router as aggregate_router
from app.core.database import init_db
from app.core.seed import seed_demo_data   # ✅ ADD THIS

app = FastAPI(title="Sentiment Analysis Platform")

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- ROUTERS ----------------
app.include_router(api_router)
app.include_router(aggregate_router)

# ---------------- REDIS CONFIG ----------------
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))


# ---------------- WEBSOCKET ----------------
from app.api.websocket import websocket_endpoint

app.add_api_websocket_route("/ws/sentiment", websocket_endpoint)

# ---------------- STARTUP ----------------
@app.on_event("startup")
async def startup():
    await init_db()          # create tables
    await seed_demo_data()   # seed demo rows IF tables empty
    
    # Start Alert Service
    from app.services.alerting import AlertService
    from app.core.database import AsyncSessionLocal
    
    alert_service = AlertService(AsyncSessionLocal)
    asyncio.create_task(alert_service.run_monitoring_loop())


# ---------------- ROOT ----------------
@app.get("/")
async def root():
    return {"status": "ok"}

