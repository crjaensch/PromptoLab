import pytest
from PySide6.QtWidgets import QApplication
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
