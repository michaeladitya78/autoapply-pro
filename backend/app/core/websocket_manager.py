"""WebSocket connection manager for real-time dashboard updates."""
from typing import Dict
from fastapi import WebSocket
import structlog

log = structlog.get_logger()


class WebSocketManager:
    def __init__(self):
        self.active: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active[user_id] = websocket
        log.info("WebSocket connected", user_id=user_id)

    def disconnect(self, user_id: str):
        self.active.pop(user_id, None)
        log.info("WebSocket disconnected", user_id=user_id)

    async def send_to_user(self, user_id: str, message: dict):
        """Send a JSON message to a specific user."""
        if user_id in self.active:
            try:
                await self.active[user_id].send_json(message)
            except Exception:
                self.disconnect(user_id)

    async def broadcast_agent_update(self, user_id: str, event_type: str, payload: dict):
        """Broadcast agent action to dashboard in real-time."""
        await self.send_to_user(user_id, {
            "type": event_type,
            "payload": payload,
        })


ws_manager = WebSocketManager()
