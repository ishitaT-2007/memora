"""Reset and reseed the synthetic demo corpus."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db import Base, SessionLocal, engine
from app.services.seed import reset_and_seed

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        reset_and_seed(db)
        print("Demo dataset reset.")
    finally:
        db.close()
