import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QPushButton, QMessageBox
from datetime import datetime
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from llm_playground import LLMPlaygroundWidget
from models import Prompt, PromptType

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
    assert playground_widget.model_combo.currentText() == "gpt-4o-mini"
    
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
    playground_widget.model_combo.setCurrentText("gpt-4")
    assert playground_widget.model_combo.currentText() == "gpt-4"
    
    # Change max tokens
    playground_widget.max_tokens_combo.setCurrentText("1024")
    assert playground_widget.max_tokens_combo.currentText() == "1024"
    
    # Change temperature
    playground_widget.temperature_combo.setCurrentText("0.7")
    assert playground_widget.temperature_combo.currentText() == "0.7"
    
    # Change top p
    playground_widget.top_p_combo.setCurrentText("0.9")
    assert playground_widget.top_p_combo.currentText() == "0.9"

@patch('llm_playground.run_llm')
def test_run_playground(mock_run_llm, qtbot, playground_widget):
    """Test running the playground with a prompt."""
    mock_run_llm.return_value = "Generated response"
    
    # Set up prompt
    qtbot.keyClicks(playground_widget.user_prompt, "Test prompt")
    
    # Find and click the run button
    run_buttons = playground_widget.findChildren(QPushButton, "")
    run_button = next(btn for btn in run_buttons if btn.text() == "Run")
    qtbot.mouseClick(run_button, Qt.LeftButton)
    qtbot.wait(100)
    
    # Verify run_llm was called with correct parameters
    mock_run_llm.assert_called_once()
    args = mock_run_llm.call_args[0]
    assert args[0] == "Test prompt"  # user_prompt
    assert args[1] is None  # system_prompt (not visible)
    assert args[2] == "gpt-4o-mini"  # model
    
    # Verify output
    assert playground_widget.playground_output.toPlainText() == "Generated response"

@patch('llm_playground.run_llm')
def test_run_playground_with_system_prompt(mock_run_llm, qtbot, playground_widget):
    """Test running the playground with both system and user prompts."""
    mock_run_llm.return_value = "Generated response"
    
    # Enable and set system prompt
    qtbot.mouseClick(playground_widget.system_prompt_checkbox, Qt.LeftButton)
    qtbot.wait(100)
    qtbot.keyClicks(playground_widget.system_prompt, "Be helpful")
    
    # Set user prompt
    qtbot.keyClicks(playground_widget.user_prompt, "Test prompt")
    
    # Run the playground
    run_buttons = playground_widget.findChildren(QPushButton, "")
    run_button = next(btn for btn in run_buttons if btn.text() == "Run")
    qtbot.mouseClick(run_button, Qt.LeftButton)
    qtbot.wait(100)
    
    # Verify run_llm was called with correct parameters
    mock_run_llm.assert_called_once()
    args = mock_run_llm.call_args[0]
    assert args[0] == "Test prompt"  # user_prompt
    assert args[1] == "Be helpful"  # system_prompt
    assert args[2] == "gpt-4o-mini"  # model

@patch('llm_playground.run_llm')
def test_improve_prompt(mock_run_llm, qtbot, playground_widget):
    """Test the improve prompt functionality."""
    mock_run_llm.return_value = "Improved prompt suggestion"
    
    # Set up prompt
    qtbot.keyClicks(playground_widget.user_prompt, "Test prompt")
    
    # Find and click the improve button
    improve_buttons = playground_widget.findChildren(QPushButton, "")
    improve_button = next(btn for btn in improve_buttons if btn.text() == "Improve Prompt")
    qtbot.mouseClick(improve_button, Qt.LeftButton)
    qtbot.wait(100)
    
    # Verify run_llm was called with correct parameters
    mock_run_llm.assert_called_once()
    args = mock_run_llm.call_args[0]
    assert "<original_prompt>" in args[0]  # Check if prompt was wrapped
    assert "Test prompt" in args[0]  # Check if original prompt is included
    assert playground_widget.improve_prompt_cmd == args[1]  # Check if improvement prompt is used
    
    # Verify output
    assert playground_widget.playground_output.toPlainText() == "Improved prompt suggestion"

def test_error_handling(qtbot, playground_widget):
    """Test error handling for empty prompts."""
    # Try to run with empty prompt
    run_buttons = playground_widget.findChildren(QPushButton, "")
    run_button = next(btn for btn in run_buttons if btn.text() == "Run")
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
    playground_widget.model_combo.setCurrentText("gpt-4")
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
    assert new_widget.model_combo.currentText() == "gpt-4"
    assert new_widget.max_tokens_combo.currentText() == "1024"
    assert new_widget.temperature_combo.currentText() == "0.7"
    assert new_widget.top_p_combo.currentText() == "0.9"
    assert new_widget.system_prompt.toPlainText() == "Test system prompt"
