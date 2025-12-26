from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

import os
import json
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

# ---------------- STARTUP ----------------
@app.on_event("startup")
async def startup():
    await init_db()          # create tables
    await seed_demo_data()   # ✅ seed demo rows IF tables empty

# ---------------- WEBSOCKET ----------------
@app.websocket("/ws/sentiment")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True
    )
    pubsub = client.pubsub()

    try:
        await pubsub.subscribe("sentiment_updates")

        async for message in pubsub.listen():
            if message["type"] == "subscribe":
                await websocket.send_json({
                    "type": "connected",
                    "message": "Connected to sentiment stream"
                })

            elif message["type"] == "message":
                await websocket.send_text(message["data"])

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WS Error: {e}")
    finally:
        await pubsub.unsubscribe("sentiment_updates")
        await client.close()

# ---------------- ROOT ----------------
@app.get("/")
async def root():
    return {"status": "ok"}

