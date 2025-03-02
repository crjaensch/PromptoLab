import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QPushButton, QMessageBox
from datetime import datetime
import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.storage.models import Prompt, PromptType
from src.modules.prompt_catalog.prompts_catalog import PromptsCatalogWidget

class MockStorage:
    def __init__(self):
        self.prompts = {}
        
    def save_prompt(self, prompt, old_type=None):
        self.prompts[prompt.id] = prompt
        
    def get_all_prompts(self):
        return list(self.prompts.values())
    
    def load_prompts(self):
        return list(self.prompts.values())
    
    def delete_prompt(self, prompt_id, prompt_type=None):
        if prompt_id in self.prompts:
            del self.prompts[prompt_id]

@pytest.fixture
def mock_storage():
    return MockStorage()

@pytest.fixture
def catalog_widget(qtbot, qapp, settings, mock_storage):
    widget = PromptsCatalogWidget(mock_storage, settings)
    widget.show()  # Need to show widget for certain operations
    qtbot.addWidget(widget)
    return widget

def test_initial_state(catalog_widget):
    """Test the initial state of the PromptsCatalogWidget."""
    assert catalog_widget.current_prompt is None
    assert catalog_widget.title_edit.text() == ""
    assert catalog_widget.user_prompt.toPlainText() == ""
    assert catalog_widget.system_prompt.toPlainText() == ""
    assert catalog_widget.type_combo.currentText() == PromptType.SIMPLE.value

def test_create_new_prompt(qtbot, catalog_widget):
    """Test creating a new prompt."""
    # Fill in the prompt details
    qtbot.keyClicks(catalog_widget.title_edit, "Test Prompt")
    qtbot.keyClicks(catalog_widget.user_prompt, "Hello World")
    qtbot.keyClicks(catalog_widget.system_prompt, "Be helpful")
    
    # Select prompt type
    catalog_widget.type_combo.setCurrentText(PromptType.STRUCTURED.value)
    
    # Find and click the save button
    save_buttons = catalog_widget.findChildren(QPushButton, "")
    save_button = next(btn for btn in save_buttons if btn.text() == "Save")
    qtbot.mouseClick(save_button, Qt.LeftButton)
    
    # Verify prompt was saved
    saved_prompts = catalog_widget.storage.get_all_prompts()
    assert len(saved_prompts) == 1
    saved_prompt = saved_prompts[0]
    assert saved_prompt.title == "Test Prompt"
    assert saved_prompt.user_prompt == "Hello World"
    assert saved_prompt.system_prompt == "Be helpful"
    assert saved_prompt.prompt_type == PromptType.STRUCTURED

def test_load_prompts(qtbot, catalog_widget, mock_storage):
    """Test loading prompts into the list."""
    # Create some test prompts
    test_prompts = [
        Prompt(
            title="Prompt 1",
            user_prompt="Test 1",
            system_prompt="System 1",
            prompt_type=PromptType.SIMPLE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            id="test1"
        ),
        Prompt(
            title="Prompt 2",
            user_prompt="Test 2",
            system_prompt="System 2",
            prompt_type=PromptType.STRUCTURED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            id="test2"
        )
    ]
    
    # Add prompts to storage
    for prompt in test_prompts:
        mock_storage.save_prompt(prompt)
    
    # Reload prompts
    catalog_widget.load_prompts()
    
    # Check if prompts are in the list
    assert catalog_widget.prompt_list.count() == 2
    items = [catalog_widget.prompt_list.item(i).text() for i in range(catalog_widget.prompt_list.count())]
    assert "Prompt 1" in items
    assert "Prompt 2" in items

def test_filter_prompts(qtbot, catalog_widget, mock_storage):
    """Test the prompt filtering functionality."""
    # Create test prompts
    test_prompts = [
        Prompt(
            title="AI Assistant",
            user_prompt="Test 1",
            system_prompt="System 1",
            prompt_type=PromptType.SIMPLE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            id="test1"
        ),
        Prompt(
            title="Code Review",
            user_prompt="Test 2",
            system_prompt="System 2",
            prompt_type=PromptType.STRUCTURED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            id="test2"
        )
    ]
    
    # Add prompts to storage and load them
    for prompt in test_prompts:
        mock_storage.save_prompt(prompt)
    catalog_widget.load_prompts()
    
    # Test filtering
    qtbot.keyClicks(catalog_widget.search_box, "AI")
    qtbot.wait(100)  # Give time for filter to apply
    
    # Count visible items
    visible_count = sum(1 for i in range(catalog_widget.prompt_list.count())
                       if not catalog_widget.prompt_list.item(i).isHidden())
    assert visible_count == 1
    
    visible_items = [catalog_widget.prompt_list.item(i).text()
                    for i in range(catalog_widget.prompt_list.count())
                    if not catalog_widget.prompt_list.item(i).isHidden()]
    assert "AI Assistant" in visible_items
    
    # Clear filter
    catalog_widget.search_box.clear()
    qtbot.wait(100)  # Give time for filter to clear
    visible_count = sum(1 for i in range(catalog_widget.prompt_list.count())
                       if not catalog_widget.prompt_list.item(i).isHidden())
    assert visible_count == 2

def test_delete_prompt(qtbot, catalog_widget, mock_storage, monkeypatch):
    """Test deleting a prompt."""
    # Create and save a test prompt
    test_prompt = Prompt(
        title="Test Prompt",
        user_prompt="Delete me",
        system_prompt="System",
        prompt_type=PromptType.SIMPLE,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        id="test1"
    )
    mock_storage.save_prompt(test_prompt)
    catalog_widget.load_prompts()
    
    # Select the prompt
    catalog_widget.prompt_list.setCurrentRow(0)
    
    # Mock QMessageBox to always return Yes
    def mock_question(*args, **kwargs):
        return QMessageBox.Yes
    monkeypatch.setattr(QMessageBox, 'question', mock_question)
    
    # Simulate right-click and delete action
    current_item = catalog_widget.prompt_list.currentItem()
    catalog_widget.delete_prompt(current_item)
    
    # Verify prompt was deleted
    assert catalog_widget.prompt_list.count() == 0
    assert len(mock_storage.prompts) == 0

def test_system_prompt_visibility(qtbot, catalog_widget):
    """Test toggling system prompt visibility."""
    # Check initial state
    initial_visibility = catalog_widget.system_prompt.isVisible()
    
    # Toggle visibility
    qtbot.mouseClick(catalog_widget.system_prompt_checkbox, Qt.LeftButton)
    qtbot.wait(100)  # Give time for visibility change
    
    # Verify visibility changed
    assert catalog_widget.system_prompt.isVisible() != initial_visibility
    
    # Toggle back
    qtbot.mouseClick(catalog_widget.system_prompt_checkbox, Qt.LeftButton)
    qtbot.wait(100)  # Give time for visibility change
    assert catalog_widget.system_prompt.isVisible() == initial_visibility
