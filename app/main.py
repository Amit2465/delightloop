from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.create_session import router as session_router
from app.api.mock_seed import router as mockseed_router
from app.api.ocr import router as card_router
from app.api.audio import router as audio_router
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
app.include_router(mockseed_router)
app.include_router(audio_router)
