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
async def websocket_client(websocket: WebSocket, session_id: str = Query(...)):
    logger.info(f"Client connected: session_id={session_id}")
    await websocket.accept()

    headers = Headers()
    headers["Authorization"] = f"Token {settings.deepgram_api_key}"
    logger.info(f"Connecting to Deepgram: {settings.deepgram_url}")

    try:
        async with connect(settings.deepgram_url, extra_headers=headers) as dg_ws:
            logger.info("Connected to Deepgram")

            async def send_to_deepgram():
                try:
                    while True:
                        data = await websocket.receive_bytes()
                        logger.info(f"Sending {len(data)} bytes to Deepgram")
                        await dg_ws.send(data)
                except WebSocketDisconnect:
                    logger.info("Client disconnected (send loop)")
                    await dg_ws.close()
                except Exception as exc:
                    logger.error(f"send_to_deepgram error: {exc}")
                    await dg_ws.close()

            async def receive_from_deepgram():
                try:
                    while True:
                        logger.info("Awaiting Deepgram response...")
                        response = await asyncio.wait_for(dg_ws.recv(), timeout=10)
                        logger.info(f"Deepgram response: {response}")

                        try:
                            response_json = json.loads(response)
                        except Exception as e:
                            logger.warning(f"Invalid JSON from Deepgram: {e}")
                            response_json = {"raw": response}

                        response_json["session_id"] = session_id
                        logger.info(
                            f"Sending with session_id: {json.dumps(response_json)}"
                        )
                        await websocket.send_text(json.dumps(response_json))

                except asyncio.TimeoutError:
                    logger.warning("No Deepgram response within 10s")
                except Exception as exc:
                    logger.error(f"receive_from_deepgram error: {exc}")
                    await websocket.close()

            await asyncio.gather(send_to_deepgram(), receive_from_deepgram())

    except Exception as exc:
        logger.error(f"Deepgram handshake/connect error: {exc}")
        await websocket.close(code=1008)
