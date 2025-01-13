from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                               QLabel, QComboBox, QPushButton)
from PySide6.QtCore import Signal, Slot
from pathlib import Path
import sys

# Add the project root directory to Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config import config

class SettingsDialog(QDialog):
    api_changed = Signal(str)  # Signal to emit when API changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PromptoLab Settings")
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # LLM API Selection
        api_layout = QHBoxLayout()
        api_label = QLabel("LLM API:")
        self.api_combo = QComboBox()
        self.api_combo.addItem("llm cmdline tool", "llm-cmd")
        self.api_combo.addItem("LiteLLM library", "litellm")
        
        # Set current value from config
        current_api = config.llm_api
        index = self.api_combo.findData(current_api)
        if index >= 0:
            self.api_combo.setCurrentIndex(index)
            
        api_layout.addWidget(api_label)
        api_layout.addWidget(self.api_combo)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")
        reset_button = QPushButton("Reset")
        
        save_button.clicked.connect(self.save_settings)
        cancel_button.clicked.connect(self.reject)
        reset_button.clicked.connect(self.reset_settings)
        
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(reset_button)
        
        # Add layouts to main layout
        layout.addLayout(api_layout)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def save_settings(self):
        new_api = self.api_combo.currentData()
        if new_api != config.llm_api:  # Only update and emit if value has changed
            config.llm_api = new_api
            self.api_changed.emit(new_api)
        self.accept()
        
    def reset_settings(self):
        config.reset_llm_api()
        index = self.api_combo.findData(config.llm_api)
        if index >= 0:
            self.api_combo.setCurrentIndex(index)
