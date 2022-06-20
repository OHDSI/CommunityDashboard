import pytest
from community_dashboard import app


@pytest.fixture
def run_app():
    return app
