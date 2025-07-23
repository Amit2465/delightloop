from contextlib import asynccontextmanager
import asyncio
import subprocess
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

    # 🔥 Start mock audio script in background
    asyncio.create_task(run_mock_audio())
    yield


async def run_mock_audio():
    # 🟡 This will run once on app startup
    proc = await asyncio.create_subprocess_exec(
        "python", "app/scripts.py",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    print("[Mock Audio Script] STDOUT:", stdout.decode())
    print("[Mock Audio Script] STDERR:", stderr.decode())


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Register routes
app.include_router(card_router)
app.include_router(session_router)
app.include_router(mockseed_router)
app.include_router(audio_router)
