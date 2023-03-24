import pytest
from plots import create_app

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "focus: single out a test for development"
    )

@pytest.fixture
def app():
    app = create_app()
    return app