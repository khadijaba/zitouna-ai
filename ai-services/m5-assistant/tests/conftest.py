import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    # "with" runs the lifespan: the models are loaded once for the whole test session.
    with TestClient(app) as c:
        yield c
