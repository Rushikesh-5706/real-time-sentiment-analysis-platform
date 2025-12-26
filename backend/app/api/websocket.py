import asyncio
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

async def websocket_handler(websocket: WebSocket):
    await websocket.accept()

    # Connection confirmation
    await websocket.send_json({
        "type": "connected",
        "message": "Connected to sentiment stream",
        "timestamp": datetime.utcnow().isoformat()
    })

    try:
        # Keep connection alive and stream metrics
        while True:
            await asyncio.sleep(30)

            await websocket.send_json({
                "type": "metrics_update",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "last_minute": {"positive": 0, "negative": 0, "neutral": 0, "total": 0},
                    "last_hour": {"positive": 0, "negative": 0, "neutral": 0, "total": 0},
                    "last_24_hours": {"positive": 0, "negative": 0, "neutral": 0, "total": 0}
                }
            })

    except WebSocketDisconnect:
        pass
