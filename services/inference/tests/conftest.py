import os
from collections.abc import Generator
from pathlib import Path

import pytest

TEST_DATABASE = Path(__file__).resolve().parent / ".slatesignal-test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE}"
os.environ["ADMIN_EMAIL"] = "admin@slatesignal.dev"
os.environ["ADMIN_BOOTSTRAP_TOKEN"] = "test-admin-bootstrap-token"  # noqa: S105
os.environ["BOOTSTRAP_HISTORICAL_EVALUATIONS"] = "false"

from slatesignal.core.database import Base, engine  # noqa: E402


@pytest.fixture(autouse=True)
def clean_database() -> Generator[None, None, None]:
    engine.dispose()
    TEST_DATABASE.unlink(missing_ok=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    TEST_DATABASE.unlink(missing_ok=True)
