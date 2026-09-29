import os
import tempfile
from pathlib import Path

TEST_DIR = Path(tempfile.mkdtemp(prefix="accrue-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(TEST_DIR / 'test.db').as_posix()}"
os.environ["HINDSIGHT_MODE"] = "mock"
os.environ["LLM_MODE"] = "mock"
os.environ["APP_SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["APP_ENV"] = "test"

from app.config import get_settings

get_settings.cache_clear()
