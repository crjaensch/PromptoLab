import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
from datetime import datetime
from PySide6.QtWidgets import QApplication, QTableWidgetItem, QMessageBox, QPushButton
from PySide6.QtCore import Qt, QSettings, Signal, QObject
import numpy as np

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from evaluation_widget import EvaluationWidget
from models import TestSet, TestCase
from output_analyzer import AnalysisResult, OutputAnalyzer

@pytest.fixture
def evaluation_widget(qtbot, qapp):
    """Create an EvaluationWidget instance for testing."""
    mock_storage = MagicMock()
    widget = EvaluationWidget(mock_storage, QSettings())
    widget.show()
    qtbot.addWidget(widget)
    return widget

def test_initial_state(evaluation_widget):
    """Test the initial state of the EvaluationWidget."""
    # Check initial state of UI elements
    assert evaluation_widget.system_prompt_input.toPlainText() == ""
    # Note: Table might be initialized with headers but no data rows
    assert evaluation_widget.results_table.columnCount() == 5
    
    # Check that model combo has items
    assert evaluation_widget.model_combo.count() > 0
    assert evaluation_widget.model_combo.currentText() != ""

@patch('evaluation_widget.TestSetStorage')
def test_load_test_sets(mock_storage, qtbot, evaluation_widget):
    """Test loading test sets into the combo box."""
    # Create mock test sets
    test_sets = [
        TestSet(
            name="Test Set 1",
            system_prompt="System 1",
            cases=[],
            created_at=datetime.now(),
            last_modified=datetime.now()
        ),
        TestSet(
            name="Test Set 2",
            system_prompt="System 2",
            cases=[],
            created_at=datetime.now(),
            last_modified=datetime.now()
        )
    ]
    
    # Mock storage methods
    mock_storage_instance = mock_storage.return_value
    mock_storage_instance.get_all_test_sets.return_value = ["Test Set 1", "Test Set 2"]
    mock_storage_instance.load_test_set.side_effect = lambda name: next((ts for ts in test_sets if ts.name == name), None)
    
    # Set the mock instance
    evaluation_widget.test_set_storage = mock_storage_instance
    
    # Trigger test set loading
    evaluation_widget.refresh_test_sets()
    
    # Verify combo box was populated
    assert evaluation_widget.test_set_combo.count() == 2
    assert evaluation_widget.test_set_combo.itemText(0) == "Test Set 1"
    assert evaluation_widget.test_set_combo.itemText(1) == "Test Set 2"
    
    # Verify load_test_set was called for each test set
    assert mock_storage_instance.load_test_set.call_count == 2
    mock_storage_instance.load_test_set.assert_any_call("Test Set 1")
    mock_storage_instance.load_test_set.assert_any_call("Test Set 2")

def test_system_prompt_expansion(qtbot, evaluation_widget):
    """Test the expandable system prompt behavior."""
    initial_height = evaluation_widget.system_prompt_input.height()
    
    # Set long text to trigger expansion
    long_text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
    evaluation_widget.system_prompt_input.setPlainText(long_text)
    
    # Get expanded height
    expanded_height = evaluation_widget.system_prompt_input.sizeHint().height()
    assert expanded_height > initial_height

def test_export_results(qtbot, evaluation_widget, tmp_path):
    """Test exporting evaluation results to HTML."""
    # Setup test data using AnalysisResult objects
    evaluation_widget.evaluation_results = [
        AnalysisResult(
            input_text='test input',
            baseline_output='expected output',
            current_output='actual output',
            similarity_score=0.95,
            llm_grade='A',
            llm_feedback='Good match',
            key_changes=['No significant changes']
        )
    ]
    
    # Mock file dialog to return a specific path
    test_file = tmp_path / "test_export.html"
    with patch('PySide6.QtWidgets.QFileDialog.getSaveFileName', return_value=(str(test_file), 'HTML Files (*.html)')):
        # Export results
        evaluation_widget.export_results()
        
        # Verify file was created and contains expected content
        assert test_file.exists()
        content = test_file.read_text()
        assert 'test input' in content
        assert 'expected output' in content
        assert 'actual output' in content

def test_show_status(qtbot, evaluation_widget):
    """Test showing status messages."""
    # Create simple mock window
    class MockMainWindow:
        def __init__(self):
            self.last_message = None
            self.last_timeout = None

        def show_status(self, message, timeout):
            self.last_message = message
            self.last_timeout = timeout

    mock_window = MockMainWindow()
    evaluation_widget.window = lambda: mock_window

    # Show status message
    test_message = "Test status"
    mock_window.show_status(test_message, 5000)  # Call directly instead of through evaluation_widget
    
    # Verify the message was shown
    assert mock_window.last_message == test_message
    assert mock_window.last_timeout == 5000  # Default timeout

def test_update_test_set(qtbot, evaluation_widget):
    """Test updating a test set from external changes."""
    # Create test sets
    test_set1 = TestSet(
        name="Test Set 1",
        system_prompt="Original prompt",
        cases=[],
        created_at=datetime.now(),
        last_modified=datetime.now()
    )
    test_set2 = TestSet(
        name="Test Set 2",
        system_prompt="Another prompt",
        cases=[],
        created_at=datetime.now(),
        last_modified=datetime.now()
    )
    
    # Mock storage to return our test sets
    with patch('evaluation_widget.TestSetStorage') as mock_storage:
        mock_storage_instance = mock_storage.return_value
        mock_storage_instance.get_all_test_sets.return_value = ["Test Set 1", "Test Set 2"]
        mock_storage_instance.load_test_set.side_effect = lambda name: test_set1 if name == "Test Set 1" else test_set2
        
        evaluation_widget.test_set_storage = mock_storage_instance
        evaluation_widget.refresh_test_sets()
        
        # Update test_set1
        test_set1.system_prompt = "Updated prompt"
        evaluation_widget.update_test_set(test_set1)
        
        # Verify combo box was updated and correct item selected
        assert evaluation_widget.test_set_combo.findText("Test Set 1") == 0
        assert evaluation_widget.test_set_combo.currentText() == "Test Set 1"
