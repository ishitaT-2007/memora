from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.services.hindsight_adapter import hindsight
from app.services.llm_adapter import llm

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/api/health")
def health(db: Session = Depends(get_db)) -> dict:
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    hs = hindsight.health()
    lm = llm.health()
    ready = db_ok and (hs.get("ok") or settings.hindsight_mode == "mock")
    return {
        "status": "ok" if ready else "degraded",
        "database": {"ok": db_ok},
        "hindsight": hs,
        "llm": lm,
        "env": settings.app_env,
    }
