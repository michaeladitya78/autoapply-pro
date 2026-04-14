"""WebSocket connection manager with Redis Pub/Sub backplane for real-time dashboard updates.

In a cloud deployment (Railway), FastAPI instances scale horizontally.
When a Celery worker emits an event, it publishes it to Redis. Every FastAPI
instance subscribes to this Redis channel, receives the event, and forwards it
local WebSockets connected to that specific instance.
"""
from typing import Dict
import asyncio
import json
import structlog
from fastapi import WebSocket

from app.core.config import settings
import redis.asyncio as redis

log = structlog.get_logger()


class WebSocketManager:
    def __init__(self):
        self.active: Dict[str, WebSocket] = {}
        self.redis_client = None
        self.pubsub_task = None

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active[user_id] = websocket
        log.info("WebSocket connected", user_id=user_id)

    def disconnect(self, user_id: str):
        self.active.pop(user_id, None)
        log.info("WebSocket disconnected", user_id=user_id)

    async def send_to_user_local(self, user_id: str, message: dict):
        """Send a message to a locally connected WebSocket."""
        if user_id in self.active:
            try:
                await self.active[user_id].send_json(message)
            except Exception:
                self.disconnect(user_id)

    async def broadcast_agent_update(self, user_id: str, event_type: str, payload: dict):
        """
        Publish agent action to Redis.
        Called by Celery workers or API endpoints.
        """
        if not self.redis_client:
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

        message = {
            "user_id": user_id,
            "data": {
                "type": event_type,
                "payload": payload,
            }
        }
        await self.redis_client.publish("autoapply_events", json.dumps(message))

    async def start_redis_listener(self):
        """Start listening to Redis for events and broadcast to local WebSockets."""
        if not self.redis_client:
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe("autoapply_events")
        log.info("Started Redis WebSocket pub/sub listener")

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    payload = json.loads(message["data"])
                    user_id = payload.get("user_id")
                    if user_id in self.active:
                        await self.send_to_user_local(user_id, payload["data"])
        except Exception as e:
            log.error("Redis pub/sub listener failed", error=str(e))


ws_manager = WebSocketManager()
