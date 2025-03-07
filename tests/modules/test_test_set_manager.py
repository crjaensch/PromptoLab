import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
from datetime import datetime
from PySide6.QtCore import Qt, Signal, QObject, QSettings
from PySide6.QtWidgets import QApplication, QPushButton, QMessageBox, QTableWidgetItem

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.modules.test_set_manager.test_set_manager import TestSetManagerWidget, BaselineGeneratorWorker
from src.modules.synthetic_generator.synthetic_generator import SyntheticExampleGeneratorWidget
from src.storage.models import TestSet, TestCase
from src.storage.test_storage import TestSetStorage

@pytest.fixture
def manager_widget(qtbot, qapp):
    """Create a TestSetManagerWidget instance for testing."""
    mock_storage = MagicMock()
    widget = TestSetManagerWidget(mock_storage, QSettings())
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

    def run(self):
        """Simulate the run method of LLMWorker."""
        self.finished.emit("Generated baseline output")

@patch('src.modules.test_set_manager.test_set_manager.QProgressDialog')
@patch('src.modules.test_set_manager.test_set_manager.LLMWorker')
def test_generate_baseline(mock_llm_worker, mock_progress_dialog, qtbot, manager_widget):
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

    # Add test cases
    test_prompts = ["Test prompt 1", "Test prompt 2"]
    for prompt in test_prompts:
        qtbot.mouseClick(manager_widget.add_case_btn, Qt.LeftButton)
        row = manager_widget.cases_table.rowCount() - 1
        manager_widget.cases_table.setItem(row, 0, QTableWidgetItem(prompt))

    # Setup mock LLMWorker
    mock_worker = MockRunner()
    mock_llm_worker.return_value = mock_worker

    # Set system prompt
    system_prompt = "Test system prompt"
    manager_widget.system_prompt.setPlainText(system_prompt)

    # Start baseline generation
    qtbot.mouseClick(manager_widget.generate_baseline_btn, Qt.LeftButton)

    # Verify progress dialog creation
    mock_progress_dialog.assert_called_once_with(
        "Generating baseline outputs...", 
        "Cancel", 
        0, 
        len(test_prompts),
        manager_widget
    )
    progress.setWindowModality.assert_called_once()

    # Verify LLMWorker creation and usage
    assert mock_llm_worker.call_count == len(test_prompts)
    for i, call in enumerate(mock_llm_worker.call_args_list):
        args, kwargs = call
        assert kwargs["model_name"] == "gpt-4o-mini"
        assert kwargs["user_prompt"] == test_prompts[i]
        assert kwargs["system_prompt"] == system_prompt

    # Emit results for each test case
    for i in range(len(test_prompts)):
        mock_worker.finished.emit("Generated baseline output")
        qtbot.wait(100)  # Wait for signal processing

    # Verify results in table
    for i in range(len(test_prompts)):
        assert manager_widget.cases_table.item(i, 1).text() == "Generated baseline output"

@patch('src.storage.test_storage.TestSetStorage')
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
    manager_widget.test_set_storage = mock_storage_instance  # Set the mock instance
    
    # Save test set
    qtbot.mouseClick(manager_widget.save_btn, Qt.LeftButton)
    qtbot.wait(100)  # Wait for any async operations
    mock_storage_instance.save_test_set.assert_called_once()
    
    # Verify save was called with correct data
    saved_test_set = mock_storage_instance.save_test_set.call_args[0][0]
    assert saved_test_set.name == "Test Set 1"
    assert saved_test_set.system_prompt == "System prompt"
    assert len(saved_test_set.cases) == 1

@pytest.fixture
def synthetic_generator_widget(qtbot, qapp):
    """Create a SyntheticExampleGeneratorWidget instance for testing."""
    widget = SyntheticExampleGeneratorWidget(QSettings())
    widget.show()
    qtbot.addWidget(widget)
    return widget

def test_integration_with_synthetic_generator(qtbot, manager_widget, synthetic_generator_widget):
    """Test integration between TestSetManager and SyntheticExampleGenerator."""
    # Create synthetic examples
    synthetic_examples = [
        TestCase(input_text="Synthetic input 1", baseline_output="Synthetic output 1"),
        TestCase(input_text="Synthetic input 2", baseline_output="Synthetic output 2")
    ]
    
    # Simulate the examples being generated
    # In a real integration, this would happen through the UI
    # Here we directly populate the examples table
    for example in synthetic_examples:
        row = synthetic_generator_widget.examples_table.rowCount()
        synthetic_generator_widget.examples_table.insertRow(row)
        synthetic_generator_widget.examples_table.setItem(row, 0, QTableWidgetItem(example.input_text))
        synthetic_generator_widget.examples_table.setItem(row, 1, QTableWidgetItem(example.baseline_output))
    
    # Get examples from the generator widget
    examples = synthetic_generator_widget.get_examples()
    assert len(examples) == 2
    
    # Add examples to the test set manager
    # In a real integration, this would happen through a signal/slot connection
    initial_row_count = manager_widget.cases_table.rowCount()
    for example in examples:
        row = manager_widget.cases_table.rowCount()
        manager_widget.cases_table.insertRow(row)
        manager_widget.cases_table.setItem(row, 0, QTableWidgetItem(example.input_text))
        manager_widget.cases_table.setItem(row, 1, QTableWidgetItem(example.baseline_output))
    
    # Verify the examples were added to the test set manager
    assert manager_widget.cases_table.rowCount() == initial_row_count + 2
    assert manager_widget.cases_table.item(initial_row_count, 0).text() == "Synthetic input 1"
    assert manager_widget.cases_table.item(initial_row_count, 1).text() == "Synthetic output 1"
    assert manager_widget.cases_table.item(initial_row_count + 1, 0).text() == "Synthetic input 2"
    assert manager_widget.cases_table.item(initial_row_count + 1, 1).text() == "Synthetic output 2"
