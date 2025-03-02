from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy
from PySide6.QtCore import Qt, QPropertyAnimation
from PySide6.QtGui import QFont

class CollapsiblePanel(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.expanded = True
        self.animation = QPropertyAnimation(self, b"minimumWidth")
        self.animation.setDuration(200)
        
        # Main layout
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Content widget first (on the left)
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 36, 0, 0)  # Add top margin for toggle button
        
        # Create vertical filler container that stays full height (on the right)
        self.toggle_container = QWidget()
        self.toggle_container.setFixedWidth(44)  # Width to accommodate button + margins
        toggle_layout = QVBoxLayout(self.toggle_container)
        toggle_layout.setContentsMargins(0, 0, 8, 0)
        toggle_layout.setAlignment(Qt.AlignRight | Qt.AlignTop)
        
        # Toggle button with plus/minus symbol in rounded square
        self.toggle_btn = QPushButton("-" if self.expanded else "+")  # Set initial state correctly
        self.toggle_btn.setFont(QFont("Arial", 16, QFont.ExtraBold))
        self.toggle_btn.setFixedSize(28, 28)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #f8f8f8;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                color: #666666;
                padding: 0px;
                text-align: center;
                line-height: 26px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-color: #cccccc;
                color: #000000;
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle_panel)
        toggle_layout.addWidget(self.toggle_btn)
        
        # Add vertical spacer to keep toggle_container full height
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        toggle_layout.addWidget(spacer)
        
        # Add widgets to main layout in correct order (content first, then toggle)
        self.main_layout.addWidget(self.content)
        self.main_layout.addWidget(self.toggle_container)
        
    def toggle_panel(self):
        self.expanded = not self.expanded
        target_width = self.sizeHint().width() if self.expanded else 44  # Width to accommodate button + margins
        self.animation.setStartValue(self.width())
        self.animation.setEndValue(target_width)
        self.animation.start()
        
        self.toggle_btn.setText("-" if self.expanded else "+")
        self.content.setVisible(self.expanded)