import asyncio
import websockets
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mock")

async def send_mock_audio():
    session_id = "test123"
    uri = f"ws://localhost:8080/ws/client?session_id={session_id}"

    try:
        async with websockets.connect(uri) as websocket:
            logger.info(f"Connected to WebSocket at {uri}")

            i = 0
            while True:
                dummy_audio = b"\x00" * 1024  # 1KB of fake bytes
                await websocket.send(dummy_audio)
                logger.info(f"Sent dummy audio chunk {i + 1}")
                
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    logger.info(f"Received response: {response}")
                except asyncio.TimeoutError:
                    logger.warning("No response received within timeout")

                i += 1
                await asyncio.sleep(2)  # send every 2 seconds

    except Exception as e:
        logger.error(f"WebSocket connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(send_mock_audio())
