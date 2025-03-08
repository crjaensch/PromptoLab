from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QSpinBox, QPushButton)

class CritiqueRefineConfigDialog(QDialog):
    """Dialog for configuring the critique and refine process."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Critique & Refine Configuration")
        self.setMinimumWidth(400)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Iterations
        iterations_layout = QHBoxLayout()
        iterations_label = QLabel("Number of iterations:")
        self.iterations_spin = QSpinBox()
        self.iterations_spin.setMinimum(1)
        self.iterations_spin.setMaximum(5)  # Limit to 5 iterations to avoid excessive API usage
        self.iterations_spin.setValue(1)  # Default to 1 iteration
        self.iterations_spin.setToolTip("Number of critique and refine cycles to perform")
        iterations_layout.addWidget(iterations_label)
        iterations_layout.addWidget(self.iterations_spin)
        layout.addLayout(iterations_layout)
        
        # Description
        description = QLabel(
            "The Critique & Refine method will iteratively improve your prompt by:\n"
            "1. Analyzing the current prompt for strengths and weaknesses\n"
            "2. Generating specific suggestions for improvement\n"
            "3. Creating a refined version that addresses the identified issues\n\n"
            "More iterations will generally produce better results but will take longer."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        
        # Buttons
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton("Start Optimization")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(ok_btn)
        layout.addLayout(button_layout)
        
    def get_iterations(self) -> int:
        """Get the number of iterations from the dialog."""
        return self.iterations_spin.value()
