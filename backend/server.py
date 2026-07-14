"""Sparsa Homeoclinic — FastAPI entry point. Routers are split by domain."""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import asyncio
import logging
import time
import uuid

from fastapi import FastAPI, APIRouter, Request
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

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


# ── CORS ────────────────────────────────────────────────────────────────────
# Set CORS_ALLOWED_ORIGINS in production to a comma-separated allow-list
# (e.g. "https://clinic.sparsa.com,https://admin.sparsa.com"). When unset, we
# fall back to a permissive regex so dev/preview environments continue to work.
_allowed_origins_env = os.environ.get("CORS_ALLOWED_ORIGINS", "").strip()
if _allowed_origins_env:
    _origins = [o.strip() for o in _allowed_origins_env.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    logging.info(f"CORS locked down to: {_origins}")
else:
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origin_regex=".*",
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )


# ── Structured request logging with X-Request-ID ────────────────────────────
class RequestContextMiddleware(BaseHTTPMiddleware):
    """Adds a request id, logs request/response with latency, and propagates the
    id back via the X-Request-ID response header so the frontend can surface it
    when reporting bugs."""

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.state.request_id = rid
        started = time.perf_counter()
        try:
            response = await call_next(request)
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            response.headers["X-Request-ID"] = rid
            # Skip noisy health-check logs
            if request.url.path != "/api/health":
                logging.info(
                    f'rid={rid} {request.method} {request.url.path} '
                    f'-> {response.status_code} ({elapsed_ms}ms)'
                )
            return response
        except Exception:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            logging.exception(
                f'rid={rid} {request.method} {request.url.path} -> 500 ({elapsed_ms}ms)'
            )
            raise


app.add_middleware(RequestContextMiddleware)

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
