import pytest
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtWidgets import QApplication, QPushButton, QMessageBox, QTableWidgetItem
from datetime import datetime
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from test_set_manager import TestSetManagerWidget, BaselineGeneratorWorker
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

class MockRunner(QObject):
    """Mock runner for LLM async operations."""
    finished = Signal(str)
    error = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.process = MagicMock()

@patch('test_set_manager.QProgressDialog')
@patch('test_set_manager.run_llm_async')
def test_generate_baseline(mock_run_llm, mock_progress_dialog, qtbot, manager_widget):
    """Test generating baseline outputs for test cases."""
    # Setup mock progress dialog
    progress = mock_progress_dialog.return_value
    progress.wasCanceled.return_value = False

    # Setup mock settings
    def mock_settings_value(key, default, type):
        settings = {
            "selected_model": "gpt-4o-mini",
            "max_tokens": "",
            "temperature": "",
            "top_p": ""
        }
        return settings.get(key, default)
    manager_widget.settings.value = mock_settings_value

    # 1. Setup a TestSet with 2 test cases
    test_set = TestSet(
        name="Test Set",
        system_prompt="You are a helpful assistant that provides concise answers.",
        cases=[
            TestCase(
                input_text="What is the capital of France?",
                baseline_output="",
                created_at=datetime.now()
            ),
            TestCase(
                input_text="What is the square root of 16?",
                baseline_output="",
                created_at=datetime.now()
            )
        ],
        created_at=datetime.now(),
        last_modified=datetime.now()
    )

    # Load test set into widget
    manager_widget.current_test_set = test_set
    manager_widget.name_input.setText(test_set.name)
    manager_widget.system_prompt.setPlainText(test_set.system_prompt)

    # Add cases to table
    for case in test_set.cases:
        row = manager_widget.cases_table.rowCount()
        manager_widget.cases_table.insertRow(row)
        manager_widget.cases_table.setItem(row, 0, QTableWidgetItem(case.input_text))
        manager_widget.cases_table.setItem(row, 1, QTableWidgetItem(case.baseline_output))

    # 2. Setup mock LLM runner that produces baseline outputs
    mock_runner = MagicMock()
    mock_run_llm.return_value = mock_runner

    # Generate baseline
    manager_widget.generate_baseline()

    # Verify LLM was called with correct arguments
    assert mock_run_llm.call_count == len(test_set.cases)
    for i, call_args in enumerate(mock_run_llm.call_args_list):
        args = call_args[0]
        assert args[0] == test_set.cases[i].input_text
        assert args[1] == test_set.system_prompt

    # 3. Simulate LLM responses and verify table updates
    expected_outputs = [
        "Paris is the capital of France.",
        "The square root of 16 is 4."
    ]
    
    # Wait for workers to be created
    qtbot.wait(100)
    
    # Verify workers were created
    assert len(manager_widget.active_workers) == len(test_set.cases)
    
    # Simulate LLM responses for each worker
    for i, output in enumerate(expected_outputs):
        # Get the worker for this test case
        worker = manager_widget.active_workers[i]
        # Simulate worker result
        worker.result.emit(i, output)
        # Wait for signal to be processed
        qtbot.wait(100)
        # Verify table was updated with the baseline output
        assert manager_widget.cases_table.item(i, 1).text() == output
        # Verify progress was updated
        assert manager_widget.completed_tasks == i + 1

    # Verify final status
    assert manager_widget.completed_tasks == len(test_set.cases)

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
