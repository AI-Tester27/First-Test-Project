"""Sparsa Homeoclinic — FastAPI entry point. Routers are split by domain."""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import asyncio
import logging

from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware

from core import mongo_client, now_utc, db
from storage import init_storage
from messaging import provider_status, refresh_messaging_cache
from seed import seed_all
from routers import auth, patients, cases, pharmacy, payments, reminders, attachments, ai, exports, admin, dashboards
from routers.reminders import reminder_scheduler

app = FastAPI(title="Sparsa Homeoclinic API")
api = APIRouter(prefix="/api")


@api.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "sparsa-homeoclinic",
        "time": now_utc().isoformat(),
        "providers": provider_status(),
    }


# Mount all domain routers under /api
for r in (auth, patients, cases, pharmacy, payments, reminders, attachments, ai, exports, admin, dashboards):
    api.include_router(r.router)

app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origin_regex=".*",
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


@app.on_event("startup")
async def on_startup():
    await seed_all()
    try:
        await refresh_messaging_cache(db)
    except Exception as e:
        logging.warning(f"Messaging cache refresh at startup failed: {e}")
    try:
        init_storage()
    except Exception as e:
        logging.warning(f"Storage init at startup failed: {e}")
    asyncio.create_task(reminder_scheduler())


@app.on_event("shutdown")
async def shutdown_db():
    mongo_client.close()
