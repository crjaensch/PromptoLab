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

from src.modules.synthetic_generator.synthetic_generator import SyntheticExampleGeneratorWidget, SyntheticExampleGeneratorWorker
from src.storage.models import TestCase

@pytest.fixture
def generator_widget(qtbot, qapp):
    """Create a SyntheticExampleGeneratorWidget instance for testing."""
    widget = SyntheticExampleGeneratorWidget(QSettings())
    widget.show()
    qtbot.addWidget(widget)
    return widget

def test_initial_state(generator_widget):
    """Test the initial state of the SyntheticExampleGeneratorWidget."""
    # Check initial state of UI elements
    assert generator_widget.task_description.toPlainText() == ""
    assert generator_widget.system_prompt.toPlainText() == ""
    assert generator_widget.examples_table.rowCount() == 0
    assert generator_widget.examples_table.columnCount() == 2
    
    # Check that buttons are in expected states
    assert generator_widget.generate_btn.isEnabled()
    assert not generator_widget.add_to_test_set_btn.isEnabled()  # Should be disabled initially
    assert generator_widget.clear_btn.isEnabled()

def test_clear_functionality(qtbot, generator_widget):
    """Test clearing the form."""
    # Set some values
    generator_widget.task_description.setPlainText("Test task")
    generator_widget.system_prompt.setPlainText("Test system prompt")
    
    # Add a row to the examples table
    generator_widget.examples_table.insertRow(0)
    generator_widget.examples_table.setItem(0, 0, QTableWidgetItem("Test input"))
    generator_widget.examples_table.setItem(0, 1, QTableWidgetItem("Test output"))
    generator_widget.add_to_test_set_btn.setEnabled(True)
    
    # Clear the form
    qtbot.mouseClick(generator_widget.clear_btn, Qt.LeftButton)
    
    # Verify everything is cleared
    assert generator_widget.task_description.toPlainText() == ""
    assert generator_widget.system_prompt.toPlainText() == ""
    assert generator_widget.examples_table.rowCount() == 0
    assert not generator_widget.add_to_test_set_btn.isEnabled()

class MockSyntheticGenerator(QObject):
    """Mock generator for synthetic examples."""
    finished = Signal()
    progress = Signal(int)
    error = Signal(str)
    result = Signal(list)
    
    def __init__(self):
        super().__init__()
    
    def start(self):
        """Simulate the start method."""
        # Generate some test examples
        examples = [
            TestCase(input_text="Test input 1", baseline_output="Test output 1"),
            TestCase(input_text="Test input 2", baseline_output="Test output 2")
        ]
        self.result.emit(examples)
        self.finished.emit()

@patch('src.modules.synthetic_generator.synthetic_generator.QProgressDialog')
@patch('src.modules.synthetic_generator.synthetic_generator.SyntheticExampleGeneratorWorker')
def test_generate_examples(mock_worker_class, mock_progress_dialog, qtbot, generator_widget):
    """Test generating synthetic examples."""
    # Setup mock progress dialog
    progress = mock_progress_dialog.return_value
    
    # Setup mock worker
    mock_worker = MockSyntheticGenerator()
    mock_worker_class.return_value = mock_worker
    
    # Set task description
    task_description = "Test task description"
    generator_widget.task_description.setPlainText(task_description)
    
    # Set system prompt
    system_prompt = "Test system prompt"
    generator_widget.system_prompt.setPlainText(system_prompt)
    
    # Start example generation
    qtbot.mouseClick(generator_widget.generate_btn, Qt.LeftButton)
    
    # Verify progress dialog creation
    mock_progress_dialog.assert_called_once()
    progress.setWindowModality.assert_called_once_with(Qt.WindowModal)
    
    # Verify worker creation
    mock_worker_class.assert_called_once()
    
    # Emit results
    examples = [
        TestCase(input_text="Test input 1", baseline_output="Test output 1"),
        TestCase(input_text="Test input 2", baseline_output="Test output 2")
    ]
    mock_worker.result.emit(examples)
    qtbot.wait(100)  # Wait for signal processing
    
    # Verify results in table
    assert generator_widget.examples_table.rowCount() == 2
    assert generator_widget.examples_table.item(0, 0).text() == "Test input 1"
    assert generator_widget.examples_table.item(0, 1).text() == "Test output 1"
    assert generator_widget.examples_table.item(1, 0).text() == "Test input 2"
    assert generator_widget.examples_table.item(1, 1).text() == "Test output 2"
    
    # Verify add to test set button is enabled
    assert generator_widget.add_to_test_set_btn.isEnabled()

def test_get_examples(generator_widget):
    """Test getting examples as TestCase objects."""
    # Add examples to the table
    generator_widget.examples_table.insertRow(0)
    generator_widget.examples_table.setItem(0, 0, QTableWidgetItem("Test input 1"))
    generator_widget.examples_table.setItem(0, 1, QTableWidgetItem("Test output 1"))
    
    generator_widget.examples_table.insertRow(1)
    generator_widget.examples_table.setItem(1, 0, QTableWidgetItem("Test input 2"))
    generator_widget.examples_table.setItem(1, 1, QTableWidgetItem("Test output 2"))
    
    # Get examples
    examples = generator_widget.get_examples()
    
    # Verify examples
    assert len(examples) == 2
    assert examples[0].input_text == "Test input 1"
    assert examples[0].baseline_output == "Test output 1"
    assert examples[1].input_text == "Test input 2"
    assert examples[1].baseline_output == "Test output 2"
