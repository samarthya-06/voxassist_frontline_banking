from fastapi import WebSocket


class SessionManager:
    def __init__(self) -> None:
        # Changed from single WebSocket to a list of WebSockets per session
        # so that multiple clients (staff + kiosk) can observe the same session.
        self.active: dict[str, list[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if session_id not in self.active:
            self.active[session_id] = []
        self.active[session_id].append(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        connections = self.active.get(session_id, [])
        if websocket in connections:
            connections.remove(websocket)
        if not connections:
            self.active.pop(session_id, None)

    async def send_json(self, session_id: str, payload: dict) -> None:
        connections = self.active.get(session_id, [])
        # Broadcast to all connected clients for this session
        dead: list[WebSocket] = []
        for ws in connections:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        # Clean up any dead connections
        for ws in dead:
            if ws in connections:
                connections.remove(ws)


manager = SessionManager()
