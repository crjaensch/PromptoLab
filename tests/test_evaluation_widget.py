import pytest
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtWidgets import QApplication, QPushButton, QMessageBox, QTableWidgetItem
from datetime import datetime
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import numpy as np

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from evaluation_widget import EvaluationWidget
from models import TestSet, TestCase
from output_analyzer import AnalysisResult, OutputAnalyzer

@pytest.fixture
def evaluation_widget(qtbot, qapp, settings):
    widget = EvaluationWidget(settings)
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
    evaluation_widget.test_storage = mock_storage_instance
    
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

class MockRunner(QObject):
    """Mock runner for LLM async operations."""
    finished = Signal(str)
    error = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.process = MagicMock()

class MockAnalyzer(QObject):
    """Mock analyzer for async analysis operations."""
    finished = Signal(object)  # Emits AnalysisResult
    error = Signal(str)
    
    def start_analysis(self, **kwargs):
        """Mock start_analysis method that emits a result."""
        self.finished.emit(AnalysisResult(
            input_text=kwargs.get('input_text', ''),
            baseline_output=kwargs.get('baseline', ''),
            current_output=kwargs.get('current', ''),
            similarity_score=1.0,
            llm_grade="A",
            llm_feedback="Perfect match",
            key_changes=["Using overall semantic similarity for comparison"]
        ))

@patch('subprocess.run')
@patch('evaluation_widget.OutputAnalyzer')
def test_run_evaluation(mock_analyzer, mock_subprocess_run, qtbot, evaluation_widget):
    """Test running evaluation on a test set."""
    # Setup mock responses for subprocess.run
    def mock_subprocess_run_impl(cmd, **kwargs):
        # Create a new mock result for each call
        result = MagicMock()
        result.returncode = 0

        # Mock response for embedding
        if "llm" in cmd and "embed" in cmd:
            # Return same embeddings for baseline and current text
            if "Expected output" in str(cmd):
                result.stdout = "[0.1, 0.2, 0.3]\n"
            elif "Generated output" in str(cmd):
                result.stdout = "[0.1, 0.2, 0.3]\n"
            else:
                result.stdout = "[0.0, 0.0, 0.0]\n"
            return result
        # Mock response for LLM generation
        elif "llm" in cmd:
            result.stdout = "Generated output\n"
            return result
        return result
    mock_subprocess_run.side_effect = mock_subprocess_run_impl

    # Create our mock analyzer instance
    mock_analyzer_instance = mock_analyzer.return_value
    mock_analyzer_instance.finished = Signal(object)

    # Mock analyze_test_case to return a consistent result
    mock_analyzer_instance.create_async_analyzer.return_value = MockAnalyzer()

    # Mock get_analysis_text and get_feedback_text to match the analysis result
    mock_analyzer_instance.get_analysis_text.return_value = "Semantic Similarity Analysis:\n• Overall Similarity Score: 1.0\n\nNote: Using overall semantic similarity for comparison"
    mock_analyzer_instance.get_feedback_text.return_value = "Grade: A\n---\nPerfect match"

    # Replace the widget's analyzer with our mock
    evaluation_widget.output_analyzer = mock_analyzer_instance

    # Create and load a test set
    test_case = TestCase(
        input_text="Test prompt",
        baseline_output="Expected output",
        created_at=datetime.now()
    )
    test_set = TestSet(
        name="Test Set 1",
        system_prompt="Original system prompt",
        cases=[test_case],
        created_at=datetime.now(),
        last_modified=datetime.now()
    )
    evaluation_widget.current_test_set = test_set

    # Set new system prompt
    evaluation_widget.system_prompt_input.setPlainText("New system prompt")

    # Mock LLM process runner
    mock_llm_runner = MockRunner()

    with patch('evaluation_widget.run_llm_async', return_value=mock_llm_runner):
        # Run evaluation
        evaluation_widget.run_evaluation()

        # Emit LLM result
        mock_llm_runner.finished.emit("Generated output")
        qtbot.wait(500)

        # Verify results
        assert evaluation_widget.results_table.rowCount() == 1
        assert evaluation_widget.results_table.item(0, 0).text() == "Test prompt"
        assert evaluation_widget.results_table.item(0, 1).text() == "Expected output"
        assert evaluation_widget.results_table.item(0, 2).text() == "Generated output"
        assert float(evaluation_widget.results_table.item(0, 3).text()) == 1.0
        assert evaluation_widget.results_table.item(0, 4).text() == "A"

def test_system_prompt_expansion(qtbot, evaluation_widget):
    """Test the expandable system prompt behavior."""
    initial_height = evaluation_widget.system_prompt_input.height()
    
    # Set long text to trigger expansion
    long_text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
    evaluation_widget.system_prompt_input.setPlainText(long_text)
    
    # Get expanded height
    expanded_height = evaluation_widget.system_prompt_input.sizeHint().height()
    assert expanded_height > initial_height
