from pathlib import Path
import sys
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QTextEdit, QComboBox, QLabel, QSplitter,
                              QCheckBox, QProgressDialog)
from PySide6.QtCore import Qt, Slot

# Add the project root directory to Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from expandable_text import ExpandableTextWidget
from llm_utils import run_llm_async, get_llm_models
from special_prompts import (get_TAG_pattern_improvement_prompt,
                             get_PIC_pattern_improvement_prompt,
                             get_LIFE_pattern_improvement_prompt)
from collapsible_panel import CollapsiblePanel

class LLMPlaygroundWidget(QWidget):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        # Store all prompt patterns
        self.prompt_patterns = {
            "TAG": get_TAG_pattern_improvement_prompt(),
            "PIC": get_PIC_pattern_improvement_prompt(),
            "LIFE": get_LIFE_pattern_improvement_prompt()
        }
        self.setup_ui()
        self.load_state()
        self.current_runner = None  # Keep track of current LLM process

    def show_status(self, message, timeout=5000):
        """Show a status message in the main window's status bar."""
        # Find the main window instance
        main_window = self.window()
        if main_window is not self and main_window and hasattr(main_window, 'show_status'):
            main_window.show_status(message, timeout)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create horizontal layout for main area and params
        playground_layout = QHBoxLayout()
        
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
        
        # Submit Prompt button on the left
        submit_btn = QPushButton("Submit Prompt")
        submit_btn.clicked.connect(self.submit_prompt)
        button_layout.addWidget(submit_btn)
        
        # Add significant space between Submit Prompt and Improve Prompt section
        button_layout.addStretch(3)  # More stretch weight for bigger gap
        
        # Group Improve Prompt button with Pattern selector
        improve_btn = QPushButton("Improve Prompt")
        improve_btn.clicked.connect(self.improve_prompt)
        pattern_label = QLabel("Prompt Pattern:")
        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems(["TAG", "PIC", "LIFE"])
        self.pattern_combo.setCurrentText("TAG")
        
        # Add tooltips for each pattern
        self.pattern_combo.setItemData(0, "Task-Action-Guideline pattern", Qt.ToolTipRole)
        self.pattern_combo.setItemData(1, "Persona-Instruction-Context pattern", Qt.ToolTipRole)
        self.pattern_combo.setItemData(2, "Learn-Improvise-Feedback-Evaluate pattern", Qt.ToolTipRole)
        
        button_layout.addWidget(improve_btn)
        button_layout.addWidget(pattern_label)
        button_layout.addWidget(self.pattern_combo)
        
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
        
        # Save as New Prompt button (right-aligned)
        save_button_layout = QHBoxLayout()
        save_button_layout.addStretch()
        self.save_as_prompt_button = QPushButton("Save as New Prompt")
        self.save_as_prompt_button.clicked.connect(self.save_as_new_prompt)
        self.save_as_prompt_button.setEnabled(False)  # Initially disabled
        save_button_layout.addWidget(self.save_as_prompt_button)
        playground_main_layout.addLayout(save_button_layout)

        playground_layout.addWidget(playground_main)
        
        # Parameters panel as collapsible (now on the right)
        self.params_panel = CollapsiblePanel("Parameters")
        self.params_panel.expanded = False  # Closed by default
        params_content_layout = QVBoxLayout()
        params_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Model selection
        model_layout = QHBoxLayout()
        model_label = QLabel("Model:")
        self.model_combo = QComboBox()
        # Get available models dynamically
        available_models = get_llm_models()
        if available_models:
            self.model_combo.addItems(available_models)
        else:
            # Fallback to default model if we can't get the list
            self.model_combo.addItems(["gpt-4o-mini"])
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_combo)
        params_content_layout.addLayout(model_layout)
        
        # Max tokens
        max_tokens_layout = QHBoxLayout()
        max_tokens_label = QLabel("Max Tokens:")
        self.max_tokens_combo = QComboBox()
        self.max_tokens_combo.addItems(["", "512", "1024", "2048", "4096", "8192"])
        self.max_tokens_combo.setCurrentText("")
        max_tokens_layout.addWidget(max_tokens_label)
        max_tokens_layout.addWidget(self.max_tokens_combo)
        params_content_layout.addLayout(max_tokens_layout)
        
        # Temperature
        temperature_layout = QHBoxLayout()
        temperature_label = QLabel("Temperature:")
        self.temperature_combo = QComboBox()
        self.temperature_combo.addItems(["", "0.0", "0.3", "0.5", "0.7", "0.9", "1.0"])
        self.temperature_combo.setCurrentText("")
        temperature_layout.addWidget(temperature_label)
        temperature_layout.addWidget(self.temperature_combo)
        params_content_layout.addLayout(temperature_layout)
        
        # Top P
        top_p_layout = QHBoxLayout()
        top_p_label = QLabel("Top P:")
        self.top_p_combo = QComboBox()
        self.top_p_combo.addItems(["", "0.1", "0.5", "0.7", "0.8", "0.9", "0.95", "1.0"])
        self.top_p_combo.setCurrentText("")
        top_p_layout.addWidget(top_p_label)
        top_p_layout.addWidget(self.top_p_combo)
        params_content_layout.addLayout(top_p_layout)
        
        self.params_panel.content_layout.addLayout(params_content_layout)
        playground_layout.addWidget(self.params_panel)
        playground_layout.setSpacing(16)  # Consistent spacing
        
        layout.addLayout(playground_layout)
        
    def save_state(self):
        self.settings.setValue("params_panel_expanded", self.params_panel.expanded)
        self.settings.setValue("playground_system_prompt_visible", self.system_prompt_visible)
        self.settings.setValue("selected_model", self.model_combo.currentText())
        self.settings.setValue("system_prompt_text", self.system_prompt.toPlainText())
        self.settings.setValue("max_tokens", self.max_tokens_combo.currentText())
        self.settings.setValue("temperature", self.temperature_combo.currentText())
        self.settings.setValue("top_p", self.top_p_combo.currentText())
        self.settings.setValue("prompt_pattern", self.pattern_combo.currentText())

    def load_state(self):
        params_expanded = self.settings.value("params_panel_expanded", False, bool)  
        self.params_panel.expanded = params_expanded
            
        # Restore LLM settings
        model = self.settings.value("selected_model", "gpt-4o-mini", str)
        self.model_combo.setCurrentText(model)
        
        system_prompt = self.settings.value("system_prompt_text", "", str)
        self.system_prompt.setPlainText(system_prompt)
        
        max_tokens = self.settings.value("max_tokens", "", str)
        self.max_tokens_combo.setCurrentText(max_tokens)
        
        temperature = self.settings.value("temperature", "", str)
        self.temperature_combo.setCurrentText(temperature)
        
        top_p = self.settings.value("top_p", "", str)
        self.top_p_combo.setCurrentText(top_p)
        
        pattern = self.settings.value("prompt_pattern", "TAG", str)
        self.pattern_combo.setCurrentText(pattern)

    @Slot()
    def submit_prompt(self):
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
                
            # Convert parameters to the correct type only if they're provided
            max_tokens = int(self.max_tokens_combo.currentText()) if self.max_tokens_combo.currentText() else None
            temperature = float(self.temperature_combo.currentText()) if self.temperature_combo.currentText() else None
            top_p = float(self.top_p_combo.currentText()) if self.top_p_combo.currentText() else None
            
            # Show progress dialog and status
            progress = QProgressDialog("Running LLM...", "Cancel", 0, 0, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(400)  # Show after 400ms to avoid flashing for quick responses
            self.show_status("Running LLM request...", 0)  # Show until completion
            
            # Start async LLM process
            self.current_runner = run_llm_async(
                user_prompt_text, 
                system_prompt_text, 
                model,
                temperature=temperature, 
                max_tokens=max_tokens, 
                top_p=top_p
            )
            
            def handle_result(result):
                progress.close()
                self.playground_output.setMarkdown(result)
                self.save_as_prompt_button.setEnabled(False)  # Ensure button is disabled for regular submit
                self.show_status("LLM request completed successfully!", 5000)
                
            def handle_error(error):
                progress.close()
                self.playground_output.setPlainText(f"Error: {error}")
                self.save_as_prompt_button.setEnabled(False)  # Disable button on error
                self.show_status(f"Error: {error}", 7000)
                
            # Connect signals
            self.current_runner.finished.connect(handle_result)
            self.current_runner.error.connect(handle_error)
            
            # Handle cancellation
            def handle_cancel():
                if self.current_runner:
                    self.current_runner.process.kill()
                    self.show_status("LLM request cancelled", 5000)
                    
            progress.canceled.connect(handle_cancel)
            
        except Exception as e:
            self.playground_output.setPlainText(f"Error: {str(e)}")
            self.save_as_prompt_button.setEnabled(False)  # Disable button on error
            self.show_status(f"Error: {str(e)}", 7000)

    @Slot()
    def improve_prompt(self):
        """Handle improve prompt button click."""
        model = self.model_combo.currentText()
        user_prompt = self.user_prompt.toPlainText()
        if not user_prompt:
            self.playground_output.setPlainText("Please enter a prompt to improve.")
            self.save_as_prompt_button.setEnabled(False)  # Disable button if no prompt
            self.show_status("Please enter a prompt to improve.", 5000)
            return
            
        try:
            # Get the selected pattern
            pattern = self.pattern_combo.currentText()
            pattern_prompt = self.prompt_patterns["TAG"] if pattern not in self.prompt_patterns else self.prompt_patterns[pattern]
            
            # Combine system and user prompts if system prompt exists and is visible
            overall_prompt = f"<original_prompt>\n User: {user_prompt}\n</original_prompt>"
            if self.system_prompt_checkbox.isChecked() and self.system_prompt.isVisible():
                system_prompt = self.system_prompt.toPlainText()
                if system_prompt.strip():
                    overall_prompt = f"<original_prompt>\nSystem: {system_prompt}\n\nUser: {user_prompt}\n</original_prompt>"
            
            # Show progress dialog and status
            progress = QProgressDialog("Improving prompt...", "Cancel", 0, 0, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(400)  # Show after 400ms to avoid flashing for quick responses
            self.show_status(f"Working on improving your prompt using {pattern} pattern...", 0)  # Show until completion
            
            # Start async LLM process
            self.current_runner = run_llm_async(overall_prompt, pattern_prompt, model)
            
            def handle_result(result):
                progress.close()
                self.playground_output.setMarkdown(result)
                self.save_as_prompt_button.setEnabled(True)  # Only enable button for improve prompt results
                self.show_status("Prompt improvement completed!", 5000)
                
            def handle_error(error):
                progress.close()
                self.playground_output.setPlainText(f"Error improving prompt: {error}")
                self.save_as_prompt_button.setEnabled(False)  # Disable button on error
                self.show_status(f"Error improving prompt: {error}", 7000)
                
            # Connect signals
            self.current_runner.finished.connect(handle_result)
            self.current_runner.error.connect(handle_error)
            
            # Handle cancellation
            def handle_cancel():
                if self.current_runner:
                    self.current_runner.process.kill()
                    self.show_status("Prompt improvement cancelled", 5000)
                    
            progress.canceled.connect(handle_cancel)
            
        except Exception as e:
            self.playground_output.setPlainText(f"Error improving prompt: {str(e)}")
            self.save_as_prompt_button.setEnabled(False)  # Disable button on error
            self.show_status(f"Error improving prompt: {str(e)}", 7000)

    @Slot()
    def toggle_system_prompt(self):
        self.system_prompt_visible = self.system_prompt_checkbox.isChecked()
        self.system_prompt.setVisible(self.system_prompt_visible)

    def set_prompt(self, prompt):
        """Set the prompt in the playground from a Prompt object"""
        try:
            # Clear previous output
            self.playground_output.clear()
            
            # Set the new prompt
            self.user_prompt.setPlainText(prompt.user_prompt)
            if prompt.system_prompt:
                self.system_prompt.setPlainText(prompt.system_prompt)
                self.system_prompt_checkbox.setChecked(True)
                self.system_prompt.setVisible(True)
            else:
                self.system_prompt.clear()
                self.system_prompt_checkbox.setChecked(False)
                self.system_prompt.setVisible(False)
                
            # Disable the save button since this is a new prompt
            self.save_as_prompt_button.setEnabled(False)
            
        except Exception as e:
            self.show_status(f"Error setting prompt: {str(e)}", 7000)

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

    @Slot()
    def save_as_new_prompt(self):
        """Switch to the prompts catalog and populate the User Prompt field with the improved prompt"""
        try:
            # Get the raw markdown text
            improved_text = self.playground_output.document().toMarkdown().strip()
            
            # Get the main window and switch to the prompts catalog tab
            main_window = self.window()  # Get the top-level window
            main_window.switch_to_prompts_catalog()
            
            # Get the prompts catalog widget and set the improved text
            catalog = main_window.prompts_catalog
            catalog.create_new_prompt()
            catalog.user_prompt.setPlainText(improved_text)
            
        except Exception as e:
            self.show_status(f"Error switching to prompts catalog: {str(e)}", 7000)