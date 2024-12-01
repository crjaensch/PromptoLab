from PySide6.QtWidgets import QTextEdit, QPushButton, QSizePolicy
from PySide6.QtCore import Qt, Signal, QRect

class ExpandableTextWidget(QTextEdit):
    """
    A QTextEdit widget with expand/contract functionality.
    Features a small button in the top-right corner that allows the widget
    to expand to fill its parent widget and contract back to its original size.
    """
    
    sizeChanged = Signal()  # Signal emitted when size changes
    expandedChanged = Signal(bool)  # Signal emitted when expanded state changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_expanded = False
        self.original_size_policy = None
        self.original_minimum_height = None
        
        # Create expand/contract button with Unicode symbols
        self.toggle_button = QPushButton("⤢", self)  # Unicode expand symbol
        self.toggle_button.setFixedSize(24, 24)
        self.toggle_button.clicked.connect(self.toggle_size)
        self.toggle_button.setToolTip("Expand")
        self.toggle_button.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                font-size: 16px;
                color: #666;
            }
            QPushButton:hover {
                background-color: rgba(200, 200, 200, 30);
                border-radius: 12px;
            }
        """)
        
        # Store original size policy
        self.original_size_policy = self.sizePolicy()
        self.original_minimum_height = self.minimumHeight()
        
        self.update_button_position()
        
    def resizeEvent(self, event):
        """Handle resize events to keep the button in the correct position"""
        super().resizeEvent(event)
        self.update_button_position()
        
    def update_button_position(self):
        """Update the position of the expand/contract button"""
        button_x = self.width() - self.toggle_button.width() - 5
        button_y = 5
        self.toggle_button.move(button_x, button_y)
        
    def toggle_size(self):
        """Toggle between expanded and normal size"""
        if not self.is_expanded:
            # Store original minimum height if not stored
            if self.original_minimum_height is None:
                self.original_minimum_height = self.minimumHeight()
            
            # Expand
            expand_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            expand_policy.setVerticalStretch(3)  # Give even more stretch in vertical direction
            self.setSizePolicy(expand_policy)
            self.setMinimumHeight(600)  # Set a larger minimum height when expanded
            
            # Update button
            self.toggle_button.setText("⤡")
            self.toggle_button.setToolTip("Contract")
        else:
            # Contract
            self.setSizePolicy(self.original_size_policy)
            self.setMinimumHeight(self.original_minimum_height)
            
            # Update button
            self.toggle_button.setText("⤢")
            self.toggle_button.setToolTip("Expand")
        
        self.is_expanded = not self.is_expanded
        self.update_button_position()
        self.sizeChanged.emit()  # Emit signal to notify of size change
        self.expandedChanged.emit(self.is_expanded)  # Emit expanded state change
        
        # Force the splitter to update
        if self.parent():
            self.parent().updateGeometry()