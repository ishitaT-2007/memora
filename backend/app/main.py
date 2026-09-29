from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.bootstrap import init_db
from app.config import get_settings
from app.errors import AccrueError, accrue_error_handler
from app.routers import accounts, auth, escalations, health, memories, sources

settings = get_settings()
logger = logging.getLogger("accrue")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


init_db()

app = FastAPI(
    title="Accrue",
    description="Hindsight-powered Customer Success copilot for live account escalations.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AccrueError, accrue_error_handler)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    try:
        response = await call_next(request)
    except AccrueError:
        raise
    except Exception:
        logger.exception("Unhandled error on %s", request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL_ERROR",
                "message": "Something went wrong. Try again or use the scripted demo fallback.",
                "request_id": request.state.request_id,
            },
        )
    response.headers["X-Request-ID"] = request.state.request_id
    return response


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(escalations.router)
app.include_router(memories.router)
app.include_router(sources.router)


@app.get("/")
def root() -> dict:
    return {"name": "Accrue", "docs": "/docs", "health": "/api/health"}
