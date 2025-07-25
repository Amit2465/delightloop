from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.audio import router as audio_router
from app.api.create_session import router as session_router
from app.api.email import router as email_router
from app.api.ocr import router as card_router
from app.api.summary import router as summary_router
from app.api.upload_s3 import router as upload_s3_router
from app.api.deepgram import router as deepgram_router
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include OCR route
app.include_router(card_router)
app.include_router(session_router)
app.include_router(audio_router)
app.include_router(summary_router)
app.include_router(email_router)
app.include_router(upload_s3_router)
app.include_router(deepgram_router)
