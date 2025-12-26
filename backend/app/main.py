from app.api.aggregate import router as aggregate_router
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.api.routes import router as api_router
from app.core.database import init_db
import asyncio
import redis.asyncio as redis
import os
import json

app = FastAPI(title="Sentiment Analysis Platform")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(api_router)
app.include_router(aggregate_router)

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

@app.on_event("startup")
async def startup():
    await init_db()

@app.websocket("/ws/sentiment")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Use the specific async Redis client
    client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    pubsub = client.pubsub()
    
    try:
        await pubsub.subscribe("sentiment_updates")
        
        # This generator keeps the connection alive and waits for messages
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
            elif message["type"] == "subscribe":
                # Send confirmation to browser that Redis is ready
                await websocket.send_json({"status": "subscribed", "channel": "sentiment_updates"})
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WS Error: {e}")
    finally:
        await pubsub.unsubscribe("sentiment_updates")
        await client.close()

@app.get("/")
async def root():
    return {"status": "ok"}
