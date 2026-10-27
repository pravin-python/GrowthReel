"""Throwaway WS verification script (not part of the shipped app)."""
import asyncio
import json
import sys

import websockets

TOKEN = open("access.txt").read().strip()


async def main() -> None:
    uri = f"ws://localhost:8001/api/v1/ws/notifications?token={TOKEN}"
    async with websockets.connect(uri) as ws:
        print("response headers:", dict(ws.response_headers), file=sys.stderr)
        first = await ws.recv()
        print("first message:", first)
        data = json.loads(first)
        assert data["type"] == "session.init", data
        assert "session_id" in data, data
        print("OK: session.init received with session_id", data["session_id"])


asyncio.run(main())
