import pytest
from PySide6.QtWidgets import QApplication
from src.llm.llm_utils_adapter import LLMWorker
from PySide6.QtCore import QSettings

@pytest.fixture(scope='session')
def qapp():
    """Create a QApplication instance for the entire test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.quit()

@pytest.fixture
def settings():
    """Create a QSettings instance for testing."""
    settings = QSettings('PromptoLab', 'Test')
    settings.clear()  # Start with clean settings
    yield settings
    settings.clear()  # Clean up after test

@pytest.fixture(autouse=True)
def available_models(monkeypatch):
    """Keep test model defaults independent of the provider catalog."""
    monkeypatch.setattr(
        LLMWorker, "get_models",
        staticmethod(lambda: ["gpt-6-luna", "gpt-5.4-mini"]),
    )
