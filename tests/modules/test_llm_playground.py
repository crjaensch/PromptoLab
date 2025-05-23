import pytest
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtWidgets import QApplication, QPushButton, QMessageBox, QProgressDialog
from datetime import datetime
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.modules.llm_playground.llm_playground import LLMPlaygroundWidget
from src.llm.llm_utils_adapter import LLMWorker
from src.storage.models import Prompt, PromptType

@pytest.fixture
def playground_widget(qtbot, qapp, settings):
    widget = LLMPlaygroundWidget(settings)
    widget.show()  # Need to show widget for certain operations
    qtbot.addWidget(widget)
    return widget

def test_initial_state(playground_widget):
    """Test the initial state of the LLMPlaygroundWidget."""
    # Check initial visibility
    assert not playground_widget.system_prompt_visible
    assert not playground_widget.system_prompt.isVisible()
    assert playground_widget.user_prompt.isVisible()
    
    # Check initial text
    assert playground_widget.user_prompt.toPlainText() == ""
    assert playground_widget.system_prompt.toPlainText() == ""
    assert playground_widget.playground_output.toPlainText() == ""
    
    # Check model selection
    assert playground_widget.model_combo.currentText() == "gpt-4o"
    
    # Check parameter values
    assert playground_widget.max_tokens_combo.currentText() == ""
    assert playground_widget.temperature_combo.currentText() == ""
    assert playground_widget.top_p_combo.currentText() == ""

def test_system_prompt_toggle(qtbot, playground_widget):
    """Test toggling the system prompt visibility."""
    # Initially hidden
    assert not playground_widget.system_prompt.isVisible()
    
    # Toggle visibility on
    qtbot.mouseClick(playground_widget.system_prompt_checkbox, Qt.LeftButton)
    qtbot.wait(100)
    assert playground_widget.system_prompt.isVisible()
    
    # Toggle visibility off
    qtbot.mouseClick(playground_widget.system_prompt_checkbox, Qt.LeftButton)
    qtbot.wait(100)
    assert not playground_widget.system_prompt.isVisible()

def test_set_prompt(qtbot, playground_widget):
    """Test setting a prompt from a Prompt object."""
    test_prompt = Prompt(
        title="Test Prompt",
        user_prompt="Hello, world!",
        system_prompt="Be helpful",
        prompt_type=PromptType.SIMPLE,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        id="test1"
    )
    
    playground_widget.set_prompt(test_prompt)
    qtbot.wait(100)
    
    assert playground_widget.user_prompt.toPlainText() == "Hello, world!"
    assert playground_widget.system_prompt.toPlainText() == "Be helpful"
    assert playground_widget.system_prompt.isVisible()
    assert playground_widget.system_prompt_checkbox.isChecked()

def test_parameter_changes(qtbot, playground_widget):
    """Test changing LLM parameters."""
    # Change model
    playground_widget.model_combo.setCurrentText("gpt-4o-mini")
    assert playground_widget.model_combo.currentText() == "gpt-4o-mini"
    
    # Change max tokens
    playground_widget.max_tokens_combo.setCurrentText("1024")
    assert playground_widget.max_tokens_combo.currentText() == "1024"
    
    # Change temperature
    playground_widget.temperature_combo.setCurrentText("0.7")
    assert playground_widget.temperature_combo.currentText() == "0.7"
    
    # Change top p
    playground_widget.top_p_combo.setCurrentText("0.9")
    assert playground_widget.top_p_combo.currentText() == "0.9"

class MockRunner(QObject):
    """Mock runner for LLM async operations."""
    finished = Signal(str)
    error = Signal(str)
    cancelled = Signal()
    
    def __init__(self):
        super().__init__()
        self._runnable = None
        self._should_succeed = True
        self._cancelled = False
        # Add a mock for the run method
        self.run = MagicMock()
        # Make run actually call our _run method when called
        self.run.side_effect = self._run
        # Add a mock for the cancel method
        self.cancel = MagicMock()
        # Make cancel actually call our _cancel method when called
        self.cancel.side_effect = self._cancel
    
    def _run(self):
        """Simulate the run method of LLMWorker."""
        # In the real implementation, this would create a runnable and start it
        # For testing, we'll just emit the signal directly if _should_succeed is True
        if self._should_succeed:
            self.finished.emit("Test response")
        
    def _cancel(self):
        """Simulate the cancel method of LLMWorker."""
        # Only emit the signal if we haven't already cancelled to prevent recursion
        if not self._cancelled:
            self._cancelled = True
            # We don't emit the cancelled signal in tests to prevent recursion
            # self.cancelled.emit()

@patch('src.modules.llm_playground.llm_playground.LLMWorker')
def test_submit_prompt(mock_llm_worker, playground_widget, qtbot):
    """Test running the playground with a basic prompt."""
    # Set up mock worker
    mock_worker = MockRunner()
    mock_llm_worker.return_value = mock_worker
    
    # Set input text
    playground_widget.user_prompt.setPlainText("Test prompt")
    
    # Run playground
    playground_widget.submit_prompt()
    
    # Verify LLMWorker was created with correct parameters
    mock_llm_worker.assert_called_once()
    args, kwargs = mock_llm_worker.call_args
    assert kwargs["user_prompt"] == "Test prompt"
    assert kwargs["system_prompt"] is None
    assert kwargs["model_name"] == "gpt-4o"
    
    # Verify worker was run
    assert mock_worker.run.called
    
    # Emit result
    mock_worker.finished.emit("Test response")
    qtbot.wait(100)
    
    # Check output
    assert playground_widget.playground_output.toPlainText() == "Test response"

@patch('src.modules.llm_playground.llm_playground.LLMWorker')
def test_submit_prompt_with_system_prompt(mock_llm_worker, playground_widget, qtbot):
    """Test running the playground with a system prompt."""
    # Set up mock worker
    mock_worker = MockRunner()
    mock_llm_worker.return_value = mock_worker
    
    # Set input text and system prompt
    playground_widget.user_prompt.setPlainText("Test prompt")
    playground_widget.system_prompt.setPlainText("Test system prompt")
    playground_widget.system_prompt_checkbox.setChecked(True)  # Enable system prompt
    
    # Run playground
    playground_widget.submit_prompt()
    
    # Verify LLMWorker was created with correct parameters
    mock_llm_worker.assert_called_once()
    args, kwargs = mock_llm_worker.call_args
    assert kwargs["user_prompt"] == "Test prompt"
    assert kwargs["system_prompt"] == "Test system prompt"
    assert kwargs["model_name"] == "gpt-4o"
    
    # Verify worker was run
    assert mock_worker.run.called
    
    # Emit result
    mock_worker.finished.emit("Test response")
    qtbot.wait(100)
    
    # Check output
    assert playground_widget.playground_output.toPlainText() == "Test response"

@patch('src.modules.llm_playground.llm_playground.LLMWorker')
def test_improve_prompt(mock_llm_worker, playground_widget, qtbot):
    """Test the improve prompt functionality."""
    # Set up mock worker
    mock_worker = MockRunner()
    mock_llm_worker.return_value = mock_worker
    
    # Set input text and ensure TAG pattern is selected (default)
    playground_widget.user_prompt.setPlainText("Test prompt")
    playground_widget.pattern_combo.setCurrentText("TAG")
    
    # Run improve prompt
    playground_widget.improve_prompt()
    
    # Verify LLMWorker was created with TAG pattern
    mock_llm_worker.assert_called_once()
    args, kwargs = mock_llm_worker.call_args
    
    # Verify user prompt format
    expected_user_prompt = "<original_prompt>\n User: Test prompt\n</original_prompt>"
    assert kwargs["user_prompt"] == expected_user_prompt
    
    # Verify system prompt (pattern)
    assert "task-action-guideline" in kwargs["system_prompt"].lower()
    assert kwargs["model_name"] == "gpt-4o"
    
    # Verify worker was run
    assert mock_worker.run.called
    
    # Test with system prompt
    mock_llm_worker.reset_mock()
    playground_widget.system_prompt.setPlainText("Test system prompt")
    playground_widget.system_prompt_checkbox.setChecked(True)
    playground_widget.improve_prompt()
    
    # Verify combined prompt format with system prompt
    args, kwargs = mock_llm_worker.call_args
    expected_user_prompt = "<original_prompt>\nSystem: Test system prompt\n\nUser: Test prompt\n</original_prompt>"
    assert kwargs["user_prompt"] == expected_user_prompt
    
    # Test different patterns
    for pattern, expected_text in [
        ("PIC", "persona-instruction-context"),
        ("LIFE", "learn-improvise-feedback-evaluate")
    ]:
        mock_llm_worker.reset_mock()
        playground_widget.pattern_combo.setCurrentText(pattern)
        playground_widget.improve_prompt()
        
        args, kwargs = mock_llm_worker.call_args
        assert expected_text in kwargs["system_prompt"].lower()
        assert mock_worker.run.called
    
    # Emit result and verify output
    mock_worker.finished.emit("Improved test prompt")
    qtbot.wait(100)
    assert "Improved test prompt" in playground_widget.playground_output.toPlainText()

def test_error_handling(qtbot, playground_widget):
    """Test error handling for empty prompts."""
    # Try to run with empty prompt
    run_buttons = playground_widget.findChildren(QPushButton, "")
    run_button = next(btn for btn in run_buttons if btn.text() == "Submit Prompt")
    qtbot.mouseClick(run_button, Qt.LeftButton)
    qtbot.wait(100)
    
    assert "Error: User prompt cannot be empty" in playground_widget.playground_output.toPlainText()
    
    # Try to improve empty prompt
    improve_buttons = playground_widget.findChildren(QPushButton, "")
    improve_button = next(btn for btn in improve_buttons if btn.text() == "Improve Prompt")
    qtbot.mouseClick(improve_button, Qt.LeftButton)
    qtbot.wait(100)
    
    assert "Please enter a prompt to improve" in playground_widget.playground_output.toPlainText()

def test_save_load_state(qtbot, playground_widget, settings):
    """Test saving and loading widget state."""
    # Set up some state
    playground_widget.model_combo.setCurrentText("gpt-4o-mini")
    playground_widget.max_tokens_combo.setCurrentText("1024")
    playground_widget.temperature_combo.setCurrentText("0.7")
    playground_widget.top_p_combo.setCurrentText("0.9")
    qtbot.mouseClick(playground_widget.system_prompt_checkbox, Qt.LeftButton)
    qtbot.wait(100)
    qtbot.keyClicks(playground_widget.system_prompt, "Test system prompt")
    
    # Save state
    playground_widget.save_state()
    
    # Create new widget with same settings
    new_widget = LLMPlaygroundWidget(settings)
    new_widget.show()
    qtbot.addWidget(new_widget)
    
    # Verify state was restored
    assert new_widget.model_combo.currentText() == "gpt-4o"
    assert new_widget.max_tokens_combo.currentText() == "1024"
    assert new_widget.temperature_combo.currentText() == "0.7"
    assert new_widget.top_p_combo.currentText() == "0.9"
    assert new_widget.system_prompt.toPlainText() == "Test system prompt"

@patch('src.modules.llm_playground.llm_playground.LLMWorker')
def test_llm_error_handling(mock_llm_worker, playground_widget, qtbot):
    """Test error handling during LLM processing."""
    # Set up mock
    mock_worker = MockRunner()
    mock_worker._should_succeed = False  # Prevent automatic success response
    mock_llm_worker.return_value = mock_worker
    
    # Set input text
    playground_widget.user_prompt.setPlainText("Test prompt")
    
    # Run playground
    playground_widget.submit_prompt()
    
    # Emit error
    mock_worker.error.emit("Test error message")
    qtbot.wait(100)
    
    # Check error is displayed in output
    assert "Error: Test error message" in playground_widget.playground_output.toPlainText()

def test_save_as_new_prompt(playground_widget, qtbot):
    """Test the save as new prompt functionality."""
    # Set prompts
    playground_widget.user_prompt.setPlainText("Test user prompt")
    playground_widget.system_prompt.setPlainText("Test system prompt")
    playground_widget.system_prompt_checkbox.setChecked(True)
    
    # Simulate successful LLM response for improve prompt
    mock_runner = MockRunner()
    with patch('src.modules.llm_playground.llm_playground.LLMWorker', return_value=mock_runner):
        playground_widget.improve_prompt()
        assert mock_runner.run.called
        mock_runner.finished.emit("Improved test response")
        qtbot.wait(100)
        
        # Verify save button is enabled
        assert playground_widget.save_as_prompt_button.isEnabled()

def test_compact_mode_toggle(playground_widget, qtbot):
    """Test toggling compact mode."""
    # Expand output by clicking the toggle button
    qtbot.mouseClick(playground_widget.playground_output.toggle_button, Qt.LeftButton)
    qtbot.wait(100)
    
    # Verify expanded state
    assert playground_widget.playground_output.is_expanded
    
    # Contract output
    qtbot.mouseClick(playground_widget.playground_output.toggle_button, Qt.LeftButton)
    qtbot.wait(100)
    
    # Verify contracted state
    assert not playground_widget.playground_output.is_expanded

@patch('src.modules.llm_playground.llm_playground.QProgressDialog')
def test_progress_dialog(mock_progress_dialog, playground_widget, qtbot):
    """Test progress dialog functionality."""
    # Set up mock
    progress = mock_progress_dialog.return_value
    progress.wasCanceled.return_value = False
    
    # Set input text
    playground_widget.user_prompt.setPlainText("Test prompt")
    
    # Run playground with mock LLMWorker
    mock_worker = MockRunner()
    with patch('src.modules.llm_playground.llm_playground.LLMWorker', return_value=mock_worker):
        playground_widget.submit_prompt()
        
        # Make sure run was called
        assert mock_worker.run.called
        
        # Verify progress dialog creation
        mock_progress_dialog.assert_called_once_with(
            "Running LLM...",
            "Cancel",
            0,
            0,
            playground_widget
        )
        
        # Verify progress dialog configuration
        progress.setWindowModality.assert_called_once_with(Qt.WindowModal)
        progress.setMinimumDuration.assert_called_once_with(400)
        
        # Simulate completion
        mock_worker.finished.emit("Test response")
        qtbot.wait(100)
        
        # Verify dialog is closed
        progress.close.assert_called_once()

def test_show_status(playground_widget, qtbot):
    """Test status message display."""
    test_message = "Test status message"
    playground_widget.show_status(test_message)
    
    # Get main window
    main_window = playground_widget.window()
    if main_window is not playground_widget:
        # Verify status message was passed to main window
        assert hasattr(main_window, 'show_status')
        # Note: Further verification would depend on main window implementation

def test_parameter_validation(playground_widget, qtbot):
    """Test parameter validation and constraints."""
    # Test max tokens
    playground_widget.max_tokens_combo.setCurrentText("1024")
    assert playground_widget.max_tokens_combo.currentText() == "1024"
    
    # Test invalid max tokens (should keep previous valid value)
    playground_widget.max_tokens_combo.setCurrentText("invalid")
    assert playground_widget.max_tokens_combo.currentText() == "1024"
    
    # Test temperature
    playground_widget.temperature_combo.setCurrentText("0.7")
    assert playground_widget.temperature_combo.currentText() == "0.7"
    
    # Test top p
    playground_widget.top_p_combo.setCurrentText("0.9")
    assert playground_widget.top_p_combo.currentText() == "0.9"
