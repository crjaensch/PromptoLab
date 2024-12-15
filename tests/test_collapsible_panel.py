import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget
import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from collapsible_panel import CollapsiblePanel

@pytest.fixture
def panel(qtbot):
    """Create a CollapsiblePanel instance"""
    widget = CollapsiblePanel("Test Panel")
    qtbot.addWidget(widget)
    return widget

def test_initial_state(panel):
    """Test the initial state of the CollapsiblePanel"""
    assert panel.expanded is True
    assert panel.toggle_btn.text() == "-"
    # The content might not be visible until the widget is shown
    panel.show()
    assert panel.content.isVisible() is True

def test_toggle_panel(qtbot, panel):
    """Test toggling the panel state"""
    # Show the widget first
    panel.show()
    panel.resize(300, 200)
    qtbot.wait(100)  # Wait for initial layout
    
    # Get initial width
    initial_width = panel.width()
    
    # Click the toggle button to collapse
    qtbot.mouseClick(panel.toggle_btn, Qt.LeftButton)
    qtbot.wait(250)  # Wait for animation
    
    assert panel.expanded is False
    assert panel.toggle_btn.text() == "+"
    assert panel.content.isVisible() is False
    
    # Click again to expand
    qtbot.mouseClick(panel.toggle_btn, Qt.LeftButton)
    qtbot.wait(250)  # Wait for animation
    
    assert panel.expanded is True
    assert panel.toggle_btn.text() == "-"
    assert panel.content.isVisible() is True
    assert panel.width() >= initial_width  # Should be back to original width

def test_content_layout(panel):
    """Test the layout structure and properties"""
    assert panel.main_layout.contentsMargins().left() == 0
    assert panel.main_layout.contentsMargins().right() == 0
    assert panel.main_layout.spacing() == 0
    
    # Test toggle button container width
    assert panel.toggle_container.width() == 44
    
    # Test content layout margins
    content_margins = panel.content_layout.contentsMargins()
    assert content_margins.top() == 36  # Top margin for toggle button
    assert content_margins.left() == 0
    assert content_margins.right() == 0

def test_add_content(qtbot, panel):
    """Test adding content to the panel"""
    test_widget = QWidget()
    panel.content_layout.addWidget(test_widget)
    
    assert test_widget.parent() == panel.content
    assert test_widget in [panel.content_layout.itemAt(i).widget() 
                          for i in range(panel.content_layout.count())]
