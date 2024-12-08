from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QTextEdit, QComboBox, QLabel, QSplitter,
                              QCheckBox)
from PySide6.QtCore import Qt, Slot
from .collapsible_panel import CollapsiblePanel
from .expandable_text import ExpandableTextWidget
from .llm_utils import run_llm
from .special_prompts import get_prompt_improvement_prompt

class LLMPlaygroundWidget(QWidget):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.improve_prompt_cmd = get_prompt_improvement_prompt()
        self.setup_ui()
        self.load_state()

    def setup_ui(self):
        playground_layout = QHBoxLayout(self)
        
        # Parameters panel as collapsible
        self.params_panel = CollapsiblePanel("Parameters")
        params_content_layout = QVBoxLayout()
        
        # Model selection
        model_layout = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.addItems(["gpt-4o-mini", "gpt-4o", "o1-mini", "o1-preview", "groq-llama3.1", "groq-llama3.3"])
        model_layout.addWidget(QLabel("Model:"))
        model_layout.addWidget(self.model_combo)
        params_content_layout.addLayout(model_layout)
        
        self.params_panel.content_layout.addLayout(params_content_layout)
        playground_layout.addWidget(self.params_panel)

        # Main playground area
        playground_main = QWidget()
        playground_main_layout = QVBoxLayout(playground_main)
        
        # System prompt
        self.system_prompt_visible = self.settings.value("playground_system_prompt_visible", False, bool)
        
        # Create horizontal layout for checkbox and label
        system_prompt_header = QHBoxLayout()
        self.system_prompt_checkbox = QCheckBox()
        self.system_prompt_checkbox.setChecked(self.system_prompt_visible)
        self.system_prompt_checkbox.stateChanged.connect(self.toggle_system_prompt)
        system_prompt_label = QLabel("System Prompt:")
        system_prompt_header.addWidget(self.system_prompt_checkbox)
        system_prompt_header.addWidget(system_prompt_label)
        system_prompt_header.addStretch()
        playground_main_layout.addLayout(system_prompt_header)
        
        self.system_prompt = QTextEdit()
        self.system_prompt.setVisible(self.system_prompt_visible)
        self.system_prompt.setStyleSheet("""
            QTextEdit {
                padding: 16px;
                min-height: 80px;
                background: #F5F5F5;
                border: 1px solid #CCCCCC;
            }
        """)
        self.system_prompt.setPlaceholderText("Enter an optional system prompt...")
        playground_main_layout.addWidget(self.system_prompt)

        # Create the user prompt
        self.user_prompt = QTextEdit()
        self.user_prompt.setStyleSheet("""
            QTextEdit {
                padding: 16px;
                min-height: 80px;
                background: #F5F5F5;
                border: 1px solid #CCCCCC;
            }
        """)
        self.user_prompt.setPlaceholderText("Enter your prompt here...")

        # Create a container for user prompt and run button
        input_container = QWidget()
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.addWidget(self.user_prompt)
        
        # Run and Improve Prompt buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        run_btn = QPushButton("Run")
        run_btn.clicked.connect(self.run_playground)
        improve_btn = QPushButton("Improve Prompt")
        improve_btn.clicked.connect(self.improve_prompt)
        button_layout.addWidget(run_btn)
        button_layout.addWidget(improve_btn)
        button_layout.addStretch()
        input_layout.addLayout(button_layout)
        
        # Output area
        self.playground_output = ExpandableTextWidget()
        self.playground_output.setReadOnly(True)
        self.playground_output.setStyleSheet("""
            QTextEdit {
                padding: 16px;
                min-height: 100px;
                background: #F8F8F8;  /* Very light gray */
                border: 1px solid #CCCCCC;
                color: #2F4F4F;  /* Dark slate gray for text */
            }
        """)
        
        # Add widgets to splitter in desired order
        playground_splitter = QSplitter(Qt.Vertical)
        playground_splitter.addWidget(input_container)
        playground_splitter.addWidget(self.playground_output)
        
        # Set initial sizes for the splitter (equal distribution)
        playground_splitter.setSizes([1000, 1000])
        
        # Store original heights for restoration
        self.original_heights = {
            'system_prompt': self.system_prompt.minimumHeight(),
            'user_prompt': self.user_prompt.minimumHeight()
        }
        
        # Connect the expandable widget's signals to update UI
        self.playground_output.expandedChanged.connect(self.toggle_compact_mode)
        self.playground_output.sizeChanged.connect(lambda: playground_splitter.setSizes(
            [200, 1800] if self.playground_output.is_expanded else [1000, 1000]
        ))
        
        playground_main_layout.addWidget(playground_splitter)

        playground_layout.addWidget(playground_main)
        playground_layout.setSpacing(16)  # Consistent spacing

    def save_state(self):
        self.settings.setValue("params_panel_expanded", self.params_panel.expanded)
        self.settings.setValue("playground_system_prompt_visible", self.system_prompt_visible)
        self.settings.setValue("selected_model", self.model_combo.currentText())
        self.settings.setValue("system_prompt_text", self.system_prompt.toPlainText())

    def load_state(self):
        params_expanded = self.settings.value("params_panel_expanded", True, bool)
        if not params_expanded:
            self.params_panel.toggle_panel()
            
        # Restore LLM settings
        model = self.settings.value("selected_model", "gpt-4o")
        self.model_combo.setCurrentText(model)
        
        system_prompt = self.settings.value("system_prompt_text", "")
        self.system_prompt.setPlainText(system_prompt)

    @Slot()
    def run_playground(self):
        try:
            model = self.model_combo.currentText()
            user_prompt_text = self.user_prompt.toPlainText()
            
            # Only get system prompt if the checkbox is checked and prompt is visible
            system_prompt_text = None
            if self.system_prompt_checkbox.isChecked() and self.system_prompt.isVisible():
                system_prompt_text = self.system_prompt.toPlainText()
                if not system_prompt_text.strip():  # If system prompt is empty after stripping whitespace
                    system_prompt_text = None
            
            if not user_prompt_text.strip():
                self.playground_output.setPlainText("Error: User prompt cannot be empty")
                return
                
            result = run_llm(user_prompt_text, system_prompt_text, model)
            self.playground_output.setMarkdown(result)  # render markdown
        except Exception as e:
            self.playground_output.setPlainText(f"Error: {str(e)}")

    @Slot()
    def improve_prompt(self):
        """Handle improve prompt button click."""
        user_prompt = self.user_prompt.toPlainText()
        if not user_prompt:
            self.playground_output.setPlainText("Please enter a prompt to improve.")
            return
            
        try:
            # Combine system and user prompts if system prompt exists and is visible
            overall_prompt = f"<original_prompt>\n User: {user_prompt}\n</original_prompt>"
            if self.system_prompt_checkbox.isChecked() and self.system_prompt.isVisible():
                system_prompt = self.system_prompt.toPlainText()
                if system_prompt.strip():
                    overall_prompt = f"<original_prompt>\nSystem: {system_prompt}\n\nUser: {user_prompt}\n</original_prompt>"
            
            improved_prompt = run_llm(overall_prompt, self.improve_prompt_cmd, self.model_combo.currentText())
            self.playground_output.setMarkdown(improved_prompt)
        except Exception as e:
            self.playground_output.setPlainText(f"Error improving prompt: {str(e)}")

    @Slot()
    def toggle_system_prompt(self):
        self.system_prompt_visible = self.system_prompt_checkbox.isChecked()
        self.system_prompt.setVisible(self.system_prompt_visible)

    def set_prompt(self, prompt):
        """Set the prompt in the playground from a Prompt object"""
        if prompt:
            self.user_prompt.setPlainText(prompt.user_prompt)
            if prompt.system_prompt:
                self.system_prompt.setPlainText(prompt.system_prompt)
                self.system_prompt_checkbox.setChecked(True)
                self.system_prompt.setVisible(True)
            else:
                self.system_prompt.clear()
                self.system_prompt_checkbox.setChecked(False)
                self.system_prompt.setVisible(False)

    def toggle_compact_mode(self, expanded):
        """Toggle between compact and normal mode for input controls"""
        if expanded:
            # Compact mode
            if self.system_prompt.isVisible():
                self.system_prompt.setMinimumHeight(40)
                self.system_prompt.setMaximumHeight(60)
            self.user_prompt.setMinimumHeight(40)
            self.user_prompt.setMaximumHeight(60)
            
            # Update placeholders for better visibility in compact mode
            if self.system_prompt.toPlainText():
                self.system_prompt.setPlaceholderText("System: " + self.system_prompt.toPlainText()[:50] + "...")
            self.user_prompt.setPlaceholderText("User: " + (self.user_prompt.toPlainText() or "Enter your prompt here..."))
            
            # Optional: Collapse parameters panel if expanded
            if self.params_panel.expanded:
                self.params_panel.toggle_panel()
        else:
            # Normal mode
            if self.system_prompt.isVisible():
                self.system_prompt.setMinimumHeight(self.original_heights['system_prompt'])
                self.system_prompt.setMaximumHeight(16777215)  # Qt's maximum value
            self.user_prompt.setMinimumHeight(self.original_heights['user_prompt'])
            self.user_prompt.setMaximumHeight(16777215)  # Qt's maximum value
            
            # Restore original placeholders
            self.system_prompt.setPlaceholderText("Enter an optional system prompt...")
            self.user_prompt.setPlaceholderText("Enter your prompt here...")