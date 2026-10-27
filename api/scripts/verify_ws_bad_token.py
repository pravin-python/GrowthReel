import asyncio
import websockets


async def main() -> None:
    uri = "ws://localhost:8001/api/v1/ws/notifications?token=garbage"
    try:
        async with websockets.connect(uri) as ws:
            msg = await ws.recv()
            print("unexpected message:", msg)
    except websockets.exceptions.InvalidStatusCode as exc:
        print("rejected at handshake with status:", exc)
    except websockets.exceptions.ConnectionClosedError as exc:
        print("closed with code:", exc.code, exc.reason)
    except Exception as exc:
        print("closed:", type(exc).__name__, exc)


asyncio.run(main())
