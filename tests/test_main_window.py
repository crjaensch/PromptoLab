import pytest
from PySide6.QtWidgets import QApplication, QTreeWidgetItem
from PySide6.QtCore import QSettings
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
from datetime import datetime

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from main_window import MainWindow
from models import Prompt, PromptType

@pytest.fixture
def main_window(qtbot, qapp):
    """Create a MainWindow instance for testing."""
    with patch('PySide6.QtCore.QSettings'):
        window = MainWindow()
        window.show()
        qtbot.addWidget(window)
        return window

def test_initial_state(main_window):
    """Test the initial state of the MainWindow."""
    # Check that all tabs are created
    assert main_window.tabs.count() == 4
    assert main_window.tabs.tabText(0) == "📚 Prompt Catalog"
    assert main_window.tabs.tabText(1) == "🧪 LLM Playground"
    assert main_window.tabs.tabText(2) == "📋 Test Sets"
    assert main_window.tabs.tabText(3) == "📊 Test Evaluation"
    
    # Check status bar initial state
    assert main_window.statusBar().currentMessage() == "Ready"

def test_show_status(main_window):
    """Test showing status messages."""
    test_message = "Test status message"
    main_window.show_status(test_message)
    assert main_window.statusBar().currentMessage() == test_message

def test_switch_to_prompts_catalog(main_window):
    """Test switching to prompts catalog tab."""
    # Switch to a different tab first
    main_window.tabs.setCurrentIndex(1)
    
    # Switch to prompts catalog
    main_window.switch_to_prompts_catalog()
    assert main_window.tabs.currentIndex() == 0

def test_prompt_selected_for_eval(main_window, qtbot):
    """Test handling prompt selection for evaluation."""
    # Create and mock a test prompt
    test_prompt = Prompt(
        title="Test Prompt",
        user_prompt="Test content",
        system_prompt=None,
        prompt_type=PromptType.SIMPLE,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        id="test"
    )
    main_window.prompts_catalog._prompts = [test_prompt]
    
    # Mock QTreeWidgetItem to return title without column index
    mock_item = MagicMock()
    mock_item.text.return_value = "Test Prompt"
    
    # Test prompt selection
    with patch.object(main_window.llm_playground, 'set_prompt') as mock_set_prompt:
        main_window.on_prompt_selected_for_eval(mock_item, None)
        mock_set_prompt.assert_called_once_with(test_prompt)
