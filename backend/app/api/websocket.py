import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect
from app.services.market_service import get_stock_quote
from app.core.redis import cache_delete


class ConnectionManager:
    def __init__(self):
        self.active: dict[str, list[WebSocket]] = {}

    async def connect(self, symbol: str, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(symbol, []).append(ws)

    def disconnect(self, symbol: str, ws: WebSocket):
        if symbol in self.active:
            try:
                self.active[symbol].remove(ws)
            except ValueError:
                pass

    async def broadcast(self, symbol: str, data: dict):
        for ws in list(self.active.get(symbol, [])):
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(symbol, ws)


manager = ConnectionManager()


async def stock_ws_handler(websocket: WebSocket, symbol: str):
    sym = symbol.upper()
    await manager.connect(sym, websocket)
    try:
        while True:
            # Bust cache so we always get fresh price
            await cache_delete(f"quote:{sym}")
            quote = await get_stock_quote(sym)
            await websocket.send_json({"type": "quote", **quote})
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        manager.disconnect(sym, websocket)
    except Exception:
        manager.disconnect(sym, websocket)
