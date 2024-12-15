import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSizePolicy
import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from expandable_text import ExpandableTextWidget

@pytest.fixture
def text_widget(qtbot):
    """Create an ExpandableTextWidget instance"""
    widget = ExpandableTextWidget()
    qtbot.addWidget(widget)
    return widget

def test_initial_state(text_widget):
    """Test the initial state of the ExpandableTextWidget"""
    assert text_widget.is_expanded is False
    assert text_widget.toggle_button.text() == "⤢"
    assert text_widget.toggle_button.toolTip() == "Expand"
    
    # Check button size and position
    assert text_widget.toggle_button.width() == 24
    assert text_widget.toggle_button.height() == 24

def test_toggle_size(qtbot, text_widget):
    """Test toggling between expanded and contracted states"""
    # Store initial properties
    initial_height = text_widget.minimumHeight()
    initial_policy = text_widget.sizePolicy()
    
    # Expand the widget
    qtbot.mouseClick(text_widget.toggle_button, Qt.LeftButton)
    
    assert text_widget.is_expanded is True
    assert text_widget.toggle_button.text() == "⤡"
    assert text_widget.toggle_button.toolTip() == "Contract"
    assert text_widget.minimumHeight() == 600
    assert text_widget.sizePolicy().verticalPolicy() == QSizePolicy.Expanding
    
    # Contract the widget
    qtbot.mouseClick(text_widget.toggle_button, Qt.LeftButton)
    
    assert text_widget.is_expanded is False
    assert text_widget.toggle_button.text() == "⤢"
    assert text_widget.toggle_button.toolTip() == "Expand"
    assert text_widget.minimumHeight() == initial_height
    assert text_widget.sizePolicy().verticalPolicy() == initial_policy.verticalPolicy()

def test_signals(qtbot, text_widget):
    """Test that signals are emitted correctly"""
    # Setup signal tracking
    size_changed_signal = False
    expanded_state = None
    
    def on_size_changed():
        nonlocal size_changed_signal
        size_changed_signal = True
    
    def on_expanded_changed(state):
        nonlocal expanded_state
        expanded_state = state
    
    text_widget.sizeChanged.connect(on_size_changed)
    text_widget.expandedChanged.connect(on_expanded_changed)
    
    # Trigger expansion
    qtbot.mouseClick(text_widget.toggle_button, Qt.LeftButton)
    
    assert size_changed_signal is True
    assert expanded_state is True
    
    # Reset and test contraction
    size_changed_signal = False
    expanded_state = None
    
    qtbot.mouseClick(text_widget.toggle_button, Qt.LeftButton)
    
    assert size_changed_signal is True
    assert expanded_state is False

def test_button_position_update(text_widget):
    """Test that button position updates correctly on resize"""
    # Show the widget and set a specific size
    text_widget.show()
    text_widget.resize(300, 200)
    
    # Force a layout update
    text_widget.update_button_position()
    
    # Button should be in top-right corner with 5px margin
    expected_x = text_widget.width() - text_widget.toggle_button.width() - 5
    expected_y = 5
    
    assert text_widget.toggle_button.x() == expected_x
    assert text_widget.toggle_button.y() == expected_y
