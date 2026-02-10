from fastapi import WebSocket, WebSocketDisconnect
from typing import List
import asyncio
import json
from datetime import datetime
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)
        
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)

manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    await websocket.send_json({
        "type": "connected",
        "message": "Connected to sentiment stream",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    metrics_task = asyncio.create_task(broadcast_metrics_loop(websocket))
    
    try:
        while True:
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        metrics_task.cancel()
    except Exception:
        manager.disconnect(websocket)
        metrics_task.cancel()

async def broadcast_metrics_loop(websocket: WebSocket):
    while True:
        try:
            # Check if socket is still open in manager
            if websocket not in manager.active_connections:
                break
                
            async with AsyncSessionLocal() as session:
                # Last minute
                last_minute = (await session.execute(text("""
                    SELECT sentiment_label, COUNT(*) as count
                    FROM sentiment_analysis
                    WHERE analyzed_at >= NOW() - INTERVAL '1 minute'
                    GROUP BY sentiment_label
                """))).all()
                
                # Last hour
                last_hour = (await session.execute(text("""
                    SELECT sentiment_label, COUNT(*) as count
                    FROM sentiment_analysis
                    WHERE analyzed_at >= NOW() - INTERVAL '1 hour'
                    GROUP BY sentiment_label
                """))).all()
                
                # Last 24 hours
                last_24h = (await session.execute(text("""
                    SELECT sentiment_label, COUNT(*) as count
                    FROM sentiment_analysis
                    WHERE analyzed_at >= NOW() - INTERVAL '24 hours'
                    GROUP BY sentiment_label
                """))).all()
            
            def format_counts(rows):
                counts = {"positive": 0, "negative": 0, "neutral": 0, "total": 0}
                for row in rows:
                    counts[row.sentiment_label] = row.count
                    counts["total"] += row.count
                return counts
            
            metrics_message = {
                "type": "metrics_update",
                "data": {
                    "last_minute": format_counts(last_minute),
                    "last_hour": format_counts(last_hour),
                    "last_24_hours": format_counts(last_24h)
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send only if connection active
            if websocket in manager.active_connections:
                await websocket.send_json(metrics_message)
            else:
                break
            
        except Exception as e:
            print(f"Error broadcasting metrics: {e}")
        
        await asyncio.sleep(30)

# Hook for worker to call
async def broadcast_new_post(post_data: dict):
    message = {
        "type": "new_post",
        "data": {
            "post_id": post_data['post_id'],
            "content": post_data['content'][:100],
            "source": post_data['source'],
            "sentiment_label": post_data.get('sentiment_label', 'unknown'),
            "confidence_score": post_data.get('confidence_score', 0),
            "emotion": post_data.get('emotion', 'unknown'),
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    await manager.broadcast(message)
