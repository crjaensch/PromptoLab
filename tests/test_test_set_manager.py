import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QPushButton, QMessageBox, QTableWidgetItem
from datetime import datetime
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from test_set_manager import TestSetManagerWidget
from models import TestSet, TestCase

@pytest.fixture
def manager_widget(qtbot, qapp, settings):
    widget = TestSetManagerWidget(settings)
    widget.show()
    qtbot.addWidget(widget)
    return widget

def test_initial_state(manager_widget):
    """Test the initial state of the TestSetManagerWidget."""
    # Check initial state of UI elements
    assert manager_widget.name_input.text() == ""
    assert manager_widget.system_prompt.toPlainText() == ""
    assert manager_widget.cases_table.rowCount() == 0
    assert manager_widget.cases_table.columnCount() == 2
    
    # Check that buttons are enabled
    assert manager_widget.add_case_btn.isEnabled()
    assert manager_widget.save_btn.isEnabled()
    assert manager_widget.load_btn.isEnabled()

def test_add_remove_test_case(qtbot, manager_widget):
    """Test adding and removing test cases from the table."""
    # Initially no rows
    assert manager_widget.cases_table.rowCount() == 0
    
    # Add a test case
    qtbot.mouseClick(manager_widget.add_case_btn, Qt.LeftButton)
    assert manager_widget.cases_table.rowCount() == 1
    
    # Add another test case
    qtbot.mouseClick(manager_widget.add_case_btn, Qt.LeftButton)
    assert manager_widget.cases_table.rowCount() == 2
    
    # Select and remove a test case
    manager_widget.cases_table.selectRow(0)
    qtbot.mouseClick(manager_widget.remove_case_btn, Qt.LeftButton)
    assert manager_widget.cases_table.rowCount() == 1

def test_test_case_editing(qtbot, manager_widget):
    """Test editing test case content in the table."""
    # Add a test case
    qtbot.mouseClick(manager_widget.add_case_btn, Qt.LeftButton)
    
    # Set test case content
    test_prompt = "Test prompt"
    test_baseline = "Expected output"
    
    prompt_item = QTableWidgetItem(test_prompt)
    baseline_item = QTableWidgetItem(test_baseline)
    manager_widget.cases_table.setItem(0, 0, prompt_item)
    manager_widget.cases_table.setItem(0, 1, baseline_item)
    
    # Verify content
    assert manager_widget.cases_table.item(0, 0).text() == test_prompt
    assert manager_widget.cases_table.item(0, 1).text() == test_baseline

@patch('test_set_manager.run_llm')
def test_generate_baseline(mock_run_llm, qtbot, manager_widget):
    """Test generating baseline outputs for test cases."""
    mock_run_llm.return_value = "Generated baseline"
    
    # Add a test case and set prompt
    qtbot.mouseClick(manager_widget.add_case_btn, Qt.LeftButton)
    prompt_item = QTableWidgetItem("Test prompt")
    manager_widget.cases_table.setItem(0, 0, prompt_item)
    
    # Set system prompt
    manager_widget.system_prompt.setPlainText("System prompt")
    
    # Generate baseline
    qtbot.mouseClick(manager_widget.generate_baseline_btn, Qt.LeftButton)
    qtbot.wait(100)
    
    # Verify baseline was generated
    assert manager_widget.cases_table.item(0, 1).text() == "Generated baseline"
    mock_run_llm.assert_called_once()

@patch('test_set_manager.TestSetStorage')
def test_save_load_test_set(mock_storage, qtbot, manager_widget):
    """Test saving and loading a test set."""
    # Create test data
    manager_widget.name_input.setText("Test Set 1")
    manager_widget.system_prompt.setPlainText("System prompt")
    qtbot.mouseClick(manager_widget.add_case_btn, Qt.LeftButton)
    manager_widget.cases_table.setItem(0, 0, QTableWidgetItem("Test prompt"))
    manager_widget.cases_table.setItem(0, 1, QTableWidgetItem("Test baseline"))
    
    # Mock storage methods
    mock_storage_instance = mock_storage.return_value
    mock_storage_instance.save_test_set.return_value = True
    manager_widget.test_storage = mock_storage_instance  # Set the mock instance
    
    # Save test set
    qtbot.mouseClick(manager_widget.save_btn, Qt.LeftButton)
    qtbot.wait(100)  # Wait for any async operations
    mock_storage_instance.save_test_set.assert_called_once()
    
    # Verify save was called with correct data
    saved_test_set = mock_storage_instance.save_test_set.call_args[0][0]
    assert saved_test_set.name == "Test Set 1"
    assert saved_test_set.system_prompt == "System prompt"
    assert len(saved_test_set.cases) == 1
