"""Integration tests for application factory and configuration behavior."""
from app import create_app


def test_app_factory_testing_config():
    """Test that application factory initializes properly under testing config."""
    test_app = create_app("testing")
    assert test_app is not None
    assert test_app.config["TESTING"] is True


def test_app_factory_development_config():
    """Test that application factory initializes properly under development config."""
    dev_app = create_app("development")
    assert dev_app is not None
    assert dev_app.config["DEBUG"] is True
