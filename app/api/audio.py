import asyncio
import json
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from websockets.client import connect
from websockets.http import Headers

from app.core.config import settings

router = APIRouter(tags=["/v1/audio"])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("audio")

@router.websocket("/ws/client")
async def websocket_client(websocket: WebSocket, session_id: str = Query(None)):
    logger.info("[AUDIO] WebSocket client connected")
    await websocket.accept()
    try:
        logger.info(f"[AUDIO] Connecting to Deepgram at {settings.deepgram_url}")
        headers = Headers()
        headers["Authorization"] = f"Token {settings.deepgram_api_key}"
        async with connect(settings.deepgram_url, extra_headers=headers) as dg_ws:

            async def send_to_deepgram():
                try:
                    while True:
                        data = await websocket.receive_bytes()
                        logger.info(f"[AUDIO] Received {len(data)} bytes from client, sending to Deepgram...")
                        await dg_ws.send(data)
                except WebSocketDisconnect:
                    logger.info("[AUDIO] Client disconnected (send loop)")
                except Exception as e:
                    logger.error(f"[AUDIO] Error in send_to_deepgram: {e}")

            async def receive_from_deepgram():
                try:
                    while True:
                        response = await dg_ws.recv()
                        logger.info(f"[AUDIO] Deepgram response: {response}")
                        # Optionally, add session_id to response if needed
                        if session_id:
                            try:
                                response_json = json.loads(response)
                                response_json["session_id"] = session_id
                                response = json.dumps(response_json)
                            except Exception:
                                pass
                        await websocket.send_text(response)
                except Exception as e:
                    logger.error(f"[AUDIO] Error in receive_from_deepgram: {e}")

            await asyncio.gather(
                send_to_deepgram(),
                receive_from_deepgram()
            )

    except WebSocketDisconnect:
        logger.info("[AUDIO] Client disconnected (main)")
    except Exception as e:
        logger.error(f"[AUDIO] Error: {e}")