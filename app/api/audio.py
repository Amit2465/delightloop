import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from websockets.client import connect
from websockets.http import Headers
from redis.asyncio import Redis
from app.core.config import settings

router = APIRouter(tags=["/v1/audio"])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("audio")

redis = Redis.from_url(settings.redis_url, decode_responses=True)

@router.websocket("/ws/client")
async def websocket_client(websocket: WebSocket, session_id: str = Query(...)):
    logger.info(f"Client connected: session_id={session_id}")
    await websocket.accept()
    
    headers = Headers()
    headers["Authorization"] = f"Token {settings.deepgram_api_key}"
    logger.info(f"Connecting to Deepgram: {settings.deepgram_url}")

    try:
        async with connect(settings.deepgram_url, extra_headers=headers) as dg_ws:
            logger.info("✅ Connected to Deepgram")

            # Ping Redis for connectivity
            try:
                pong = await redis.ping()
                logger.info(f"Redis ping response: {pong}")
            except Exception as e:
                logger.error(f"Redis ping failed: {e}")

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
                            logger.warning(f"Invalid JSON: {e}")
                            response_json = None

                        if response_json:
                            redis_key = f"session:{session_id}:transcripts"
                            serialized = json.dumps(response_json)

                            logger.info(f"Pushing to Redis: key={redis_key}, value={serialized}")
                            try:
                                await redis.rpush(redis_key, serialized)
                                logger.info("Push OK")
                                length = await redis.llen(redis_key)
                                logger.info(f"Redis list length now: {length}")
                            except Exception as e:
                                logger.error(f"Redis push failed: {e}")

                        await websocket.send_text(response)

                except asyncio.TimeoutError:
                    logger.warning("No Deepgram response within 10s")
                    # optionally continue, or break
                except Exception as exc:
                    logger.error(f"receive_from_deepgram error: {exc}")
                    await websocket.close()

            await asyncio.gather(send_to_deepgram(), receive_from_deepgram())

    except Exception as exc:
        logger.error(f"Deepgram handshake/connect error: {exc}")
        await websocket.close(code=1008)
    finally:
        logger.info("Finalizing: closing Redis")
        try:
            await redis.close()
        except Exception as e:
            logger.error(f"Redis close failed: {e}")
        logger.info("Cleanup complete")
