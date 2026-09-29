from app.db import Base, SessionLocal, engine
from app.models import User
from app.services.seed import reset_and_seed


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            reset_and_seed(db)
    finally:
        db.close()
