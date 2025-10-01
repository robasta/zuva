import asyncio
import websockets

async def test_ws():
    uri = "ws://localhost:8000/ws/dashboard"
    print(f"Connecting to {uri}...")
    async with websockets.connect(uri) as websocket:
        print("Connected! Sending ping...")
        await websocket.send('{"type": "ping"}')
        response = await websocket.recv()
        print(f"Received: {response}")
        print("WebSocket test successful.")

if __name__ == "__main__":
    asyncio.run(test_ws())
