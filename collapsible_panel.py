from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, QPropertyAnimation
from PySide6.QtGui import QIcon

class CollapsiblePanel(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.expanded = True
        self.animation = QPropertyAnimation(self, b"minimumWidth")
        self.animation.setDuration(200)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)  # Remove spacing between toggle button and content
        
        # Top container for the toggle button
        toggle_container = QWidget()
        toggle_container.setFixedHeight(48)  # Match button height
        toggle_layout = QHBoxLayout(toggle_container)
        toggle_layout.setContentsMargins(0, 0, 0, 0)
        toggle_layout.setAlignment(Qt.AlignRight | Qt.AlignTop)  # Align to top-right
        
        # Toggle button with chevron
        self.toggle_btn = QPushButton()
        self.toggle_btn.setIcon(QIcon("PromptoLab/icons/chevron-left.svg"))
        self.toggle_btn.clicked.connect(self.toggle_panel)
        self.toggle_btn.setFixedSize(48, 48)
        toggle_layout.addWidget(self.toggle_btn)
        
        # Add toggle container to main layout
        layout.addWidget(toggle_container)
        
        # Content widget
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        layout.addWidget(self.content)

    def toggle_panel(self):
        self.expanded = not self.expanded
        target_width = self.sizeHint().width() if self.expanded else 48
        self.animation.setStartValue(self.width())
        self.animation.setEndValue(target_width)
        self.animation.start()
        
        self.toggle_btn.setIcon(
            QIcon(
                "PromptoLab/icons/chevron-left.svg"
                if self.expanded
                else "PromptoLab/icons/chevron-right.svg"
            )
        )
        self.content.setVisible(self.expanded)