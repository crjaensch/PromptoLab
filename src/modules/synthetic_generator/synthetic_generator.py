import re
import random
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QTextEdit, QComboBox, QLabel, QSpinBox,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QLineEdit, QMessageBox, QProgressDialog,
                              QSlider, QCheckBox, QGroupBox, QGridLayout)
from PySide6.QtCore import Qt, Signal, Slot, QSettings, QObject, QThread

from src.storage.models import TestCase, TestSet
from src.llm.llm_utils_adapter import LLMWorker

class SyntheticExampleGeneratorSignals(QObject):
    """Signals for the synthetic example generator."""
    finished = Signal()
    progress = Signal(int)
    error = Signal(str)
    result = Signal(object)

class SyntheticExampleGeneratorWorker(QObject):
    """Worker for generating synthetic examples using PromptWizard's algorithm."""
    finished = Signal()
    progress = Signal(int)
    error = Signal(str)
    result = Signal(object)  # Changed to object to properly pass TestCase objects
    
    def __init__(self, task_description: str, system_prompt: str, model: str, 
                 num_examples: int = 5, diversity_level: float = 0.7,
                 complexity_level: float = 0.5, max_tokens: int = None, 
                 temperature: float = 0.7, top_p: float = 1.0):
        super().__init__()
        self.task_description = task_description
        self.system_prompt = system_prompt
        self.model = model
        self.num_examples = num_examples
        self.diversity_level = diversity_level
        self.complexity_level = complexity_level
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        self._worker = None
        self._thread = None
    
    def start(self):
        """Start the synthetic example generation process."""
        try:
            # Create worker thread
            self._thread = QThread()
            
            # Generate the prompt for synthetic example generation
            prompt = self._create_synthetic_example_prompt()
            
            self._worker = LLMWorker(
                model_name=self.model,
                user_prompt=prompt,
                system_prompt=self.system_prompt,
                model_params={
                    'temperature': self.temperature,
                    'max_tokens': self.max_tokens,
                    'top_p': self.top_p
                }
            )
            
            self._worker.moveToThread(self._thread)
            self._worker.finished.connect(self._handle_result)
            self._worker.error.connect(self.error.emit)
            self._thread.started.connect(self._worker.run)
            
            # Start thread
            self._thread.start()
            
        except Exception as e:
            self.error.emit(f"Error starting synthetic example generation: {str(e)}")
    
    def _create_synthetic_example_prompt(self) -> str:
        """Create a prompt for generating synthetic examples based on PromptWizard's algorithm."""
        # This is based on PromptWizard's prompt templates for synthetic example generation
        prompt = f"""
        I need you to generate {self.num_examples} diverse and high-quality synthetic examples for the following task:
        
        TASK DESCRIPTION:
        {self.task_description}
        
        INSTRUCTIONS:
        1. Generate {self.num_examples} synthetic examples that are diverse, realistic, and task-aware.
        2. Each example should include a user input/question and the expected output/answer.
        3. Diversity level: {self.diversity_level*10}/10 (higher means more diverse examples covering different aspects of the task)
        4. Complexity level: {self.complexity_level*10}/10 (higher means more complex examples that test edge cases)
        5. Include a mix of common cases and edge cases.
        6. Ensure the examples are representative of real-world usage.
        
        For each example, provide:
        - USER INPUT: The input or question for this example
        - EXPECTED OUTPUT: The expected output or answer for this input
        
        Format each example as follows:
        <EXAMPLE>
        USER INPUT: [input text]
        EXPECTED OUTPUT: [output text]
        </EXAMPLE>
        
        Generate {self.num_examples} examples following this format.
        """
        
        return prompt
    
    def _handle_result(self, result: str):
        """Process the result from the LLM and extract the synthetic examples."""
        try:
            # Log the LLM response for debugging
            logging.info(f"LLM Response received: {result[:100]}...")
            
            if not result or len(result.strip()) == 0:
                self.error.emit("Received empty response from LLM")
                self.finished.emit()
                return
            
            # Extract examples using regex pattern
            examples = self._extract_examples(result)
            logging.info(f"Extracted {len(examples)} examples from LLM response")
            
            if not examples:
                self.error.emit("No examples could be extracted from the LLM response. Check the format.")
                self.finished.emit()
                return
            
            # Convert to TestCase objects
            test_cases = []
            for example in examples:
                test_cases.append(TestCase(
                    input_text=example['input'],
                    baseline_output=example['output'],
                    test_id=None,  # Will be assigned when saved
                    created_at=datetime.now()
                ))
            
            logging.info(f"Created {len(test_cases)} TestCase objects")
            self.result.emit(test_cases)
            self.finished.emit()
            
            # Clean up
            if self._thread:
                self._thread.quit()
                self._thread.wait()
                self._thread = None
                self._worker = None
                
        except Exception as e:
            logging.error(f"Error in _handle_result: {str(e)}")
            self.error.emit(f"Error processing synthetic examples: {str(e)}")
    
    def _extract_examples(self, text: str) -> List[Dict[str, str]]:
        """Extract examples from the LLM output using regex."""
        examples = []
        
        # Log the text for debugging
        logging.info(f"Extracting examples from text of length {len(text)}")
        
        # Pattern to match examples between <EXAMPLE> tags
        example_pattern = r'<EXAMPLE>\s*(.+?)\s*</EXAMPLE>'
        example_matches = re.findall(example_pattern, text, re.DOTALL)
        logging.info(f"Found {len(example_matches)} example matches with <EXAMPLE> tags")
        
        if not example_matches:
            # Try alternative format without tags
            logging.info("No <EXAMPLE> tags found, trying alternative format...")
            # Look for USER INPUT/EXPECTED OUTPUT pattern directly
            example_sections = re.split(r'\n\s*\d+\.\s*|\n\n', text)
            for section in example_sections:
                if "USER INPUT:" in section and "EXPECTED OUTPUT:" in section:
                    example_matches.append(section)
            logging.info(f"Found {len(example_matches)} example matches with alternative format")
        
        for i, example_text in enumerate(example_matches):
            logging.info(f"Processing example {i+1}: {example_text[:50]}...")
            # Extract input and output
            input_match = re.search(r'USER INPUT:\s*(.+?)\s*(?:EXPECTED OUTPUT|$)', example_text, re.DOTALL)
            output_match = re.search(r'EXPECTED OUTPUT:\s*(.+?)\s*$', example_text, re.DOTALL)
            
            if input_match and output_match:
                examples.append({
                    'input': input_match.group(1).strip(),
                    'output': output_match.group(1).strip()
                })
                logging.info(f"Successfully extracted example {i+1}")
            else:
                logging.warning(f"Failed to extract input/output from example {i+1}")
                if not input_match:
                    logging.warning("Input match failed")
                if not output_match:
                    logging.warning("Output match failed")
        
        return examples

class SyntheticExampleGeneratorWidget(QWidget):
    """Widget for generating synthetic examples using PromptWizard's algorithm."""
    examples_generated = Signal(object)  # Emitted when examples are generated with a list of TestCase objects
    
    def __init__(self, settings: QSettings):
        super().__init__()
        self.settings = settings
        self.setup_ui()
        
    def setup_ui(self):        
        layout = QVBoxLayout(self)
        
        # Task Description
        task_description_label = QLabel("Task Description:")
        layout.addWidget(task_description_label)
        
        self.task_description = QTextEdit()
        self.task_description.setPlaceholderText("Describe the task for which you want to generate examples...")
        self.task_description.setMinimumHeight(100)
        layout.addWidget(self.task_description)
        
        # System Prompt
        system_prompt_label = QLabel("System Prompt (optional):")
        layout.addWidget(system_prompt_label)
        
        self.system_prompt = QTextEdit()
        self.system_prompt.setPlaceholderText("Enter system prompt here (optional)...")
        self.system_prompt.setMinimumHeight(80)
        layout.addWidget(self.system_prompt)
        
        # Parameters Group
        params_group = QGroupBox("Generation Parameters")
        # Adjust font size to match other labels
        font = params_group.font()
        font.setPointSize(font.pointSize())  # Keep same point size but ensure consistent styling
        params_group.setFont(font)
        params_layout = QVBoxLayout(params_group)
        
        # Number of examples
        num_examples_layout = QHBoxLayout()
        num_examples_label = QLabel("Number of Examples:")
        num_examples_label.setMinimumWidth(120)  # Fixed width for alignment
        num_examples_layout.addWidget(num_examples_label)
        self.num_examples_spin = QSpinBox()
        self.num_examples_spin.setRange(1, 20)
        self.num_examples_spin.setValue(5)
        self.num_examples_spin.setMinimumWidth(60)  # Increase width for two-digit numbers
        num_examples_layout.addWidget(self.num_examples_spin)
        num_examples_layout.addStretch(1)  # Push content to the left
        params_layout.addLayout(num_examples_layout)
        
        # Diversity Level
        diversity_layout = QGridLayout()
        diversity_label = QLabel("Diversity Level:")
        diversity_label.setMinimumWidth(120)  # Fixed width for alignment
        diversity_layout.addWidget(diversity_label, 0, 0)
        
        self.diversity_slider = QSlider(Qt.Horizontal)
        self.diversity_slider.setRange(1, 10)
        self.diversity_slider.setValue(7)  # Default 0.7
        self.diversity_slider.setFixedWidth(300)  # Fixed width for slider
        
        self.diversity_value_label = QLabel("7/10")
        self.diversity_value_label.setMinimumWidth(40)  # Fixed width for value label
        
        self.diversity_slider.valueChanged.connect(lambda v: self.diversity_value_label.setText(f"{v}/10"))
        
        diversity_layout.addWidget(self.diversity_slider, 0, 1)
        diversity_layout.addWidget(self.diversity_value_label, 0, 2)
        diversity_layout.setColumnStretch(3, 1)  # Add stretch in the last column
        params_layout.addLayout(diversity_layout)
        
        # Complexity Level
        complexity_layout = QGridLayout()
        complexity_label = QLabel("Complexity Level:")
        complexity_label.setMinimumWidth(120)  # Fixed width for alignment
        complexity_layout.addWidget(complexity_label, 0, 0)
        
        self.complexity_slider = QSlider(Qt.Horizontal)
        self.complexity_slider.setRange(1, 10)
        self.complexity_slider.setValue(5)  # Default 0.5
        self.complexity_slider.setFixedWidth(300)  # Fixed width for slider
        
        self.complexity_value_label = QLabel("5/10")
        self.complexity_value_label.setMinimumWidth(40)  # Fixed width for value label
        
        self.complexity_slider.valueChanged.connect(lambda v: self.complexity_value_label.setText(f"{v}/10"))
        
        complexity_layout.addWidget(self.complexity_slider, 0, 1)
        complexity_layout.addWidget(self.complexity_value_label, 0, 2)
        complexity_layout.setColumnStretch(3, 1)  # Add stretch in the last column
        params_layout.addLayout(complexity_layout)
        
        # Model Selection (moved into Generation Parameters section)
        model_layout = QGridLayout()
        model_label = QLabel("Model:")
        model_label.setMinimumWidth(120)  # Fixed width for alignment
        model_layout.addWidget(model_label, 0, 0)
        
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(300)  # Match width of sliders
        
        # Populate with models from LLMWorker.get_models()
        available_models = LLMWorker.get_models()
        for model in available_models:
            self.model_combo.addItem(model)
        
        # Set the previously selected model if available, otherwise use the first model
        saved_model = self.settings.value("selected_model", "", str)
        if saved_model and self.model_combo.findText(saved_model) >= 0:
            self.model_combo.setCurrentText(saved_model)
        elif self.model_combo.count() > 0:
            # Save the first model as the default if no saved model
            self.settings.setValue("selected_model", self.model_combo.itemText(0))
        
        # Connect model selection change to save the selection
        self.model_combo.currentTextChanged.connect(
            lambda text: self.settings.setValue("selected_model", text)
        )
        
        model_layout.addWidget(self.model_combo, 0, 1)
        model_layout.setColumnStretch(3, 1)  # Add stretch in the last column
        params_layout.addLayout(model_layout)
        
        layout.addWidget(params_group)
        
        # Generated Examples Table
        self.examples_table = QTableWidget()
        self.examples_table.setColumnCount(2)
        self.examples_table.setHorizontalHeaderLabels(["User Input", "Expected Output"])
        header = self.examples_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.examples_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.generate_btn = QPushButton("Generate Examples")
        self.add_to_test_set_btn = QPushButton("Add to Test Set")
        self.add_to_test_set_btn.setEnabled(False)  # Disabled until examples are generated
        self.clear_btn = QPushButton("Clear")
        
        button_layout.addWidget(self.generate_btn)
        button_layout.addWidget(self.add_to_test_set_btn)
        button_layout.addWidget(self.clear_btn)
        layout.addLayout(button_layout)
        
        # Connect signals
        self.generate_btn.clicked.connect(self.generate_examples)
        self.clear_btn.clicked.connect(self.clear)
        
    def generate_examples(self):
        """Generate synthetic examples based on the task description and parameters."""
        task_description = self.task_description.toPlainText().strip()
        if not task_description:
            self.show_status("Please enter a task description", 5000)
            return
        
        # Get model and parameters
        model = self.model_combo.currentText()
        if not model:
            self.show_status("No model selected", 5000)
            return
        
        # Get parameters from UI
        num_examples = self.num_examples_spin.value()
        diversity_level = self.diversity_slider.value() / 10.0
        complexity_level = self.complexity_slider.value() / 10.0
        
        # Get optional parameters from settings
        max_tokens = self.settings.value("max_tokens", "", str)
        temperature = self.settings.value("temperature", "", str)
        top_p = self.settings.value("top_p", "", str)
        
        # Convert parameters to correct type if they're provided
        max_tokens = int(max_tokens) if max_tokens else None
        temperature = float(temperature) if temperature else 0.7
        top_p = float(top_p) if top_p else 1.0
        
        # Create progress dialog
        self.progress_dialog = QProgressDialog("Generating synthetic examples...", "Cancel", 0, 100, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setValue(10)  # Initial progress
        self.progress_dialog.canceled.connect(self.cancel_generation)
        
        # Create and configure the worker
        self.worker = SyntheticExampleGeneratorWorker(
            task_description=task_description,
            system_prompt=self.system_prompt.toPlainText(),
            model=model,
            num_examples=num_examples,
            diversity_level=diversity_level,
            complexity_level=complexity_level,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p
        )
        
        # Connect signals
        self.worker.result.connect(self.handle_examples)
        self.worker.error.connect(self.handle_error)
        self.worker.progress.connect(self.progress_dialog.setValue)
        self.worker.finished.connect(self.progress_dialog.close)
        
        # Start the worker
        self.worker.start()
        self.progress_dialog.setValue(20)  # Update progress
        
    def handle_examples(self, examples: List[TestCase]):
        """Handle the generated examples by populating the table."""
        # Clear existing examples
        self.examples_table.setRowCount(0)
        
        # Add examples to the table
        for example in examples:
            row = self.examples_table.rowCount()
            self.examples_table.insertRow(row)
            self.examples_table.setItem(row, 0, QTableWidgetItem(example.input_text))
            self.examples_table.setItem(row, 1, QTableWidgetItem(example.baseline_output))
        
        # Enable the add to test set button
        self.add_to_test_set_btn.setEnabled(True)
        
        # Emit signal with the examples
        self.examples_generated.emit(examples)
        
        # Show success message
        self.show_status(f"Successfully generated {len(examples)} synthetic examples", 5000)
        
    def get_examples(self) -> List[TestCase]:
        """Get the current examples as TestCase objects."""
        examples = []
        for row in range(self.examples_table.rowCount()):
            input_text = self.examples_table.item(row, 0).text()
            output_text = self.examples_table.item(row, 1).text()
            examples.append(TestCase(
                input_text=input_text,
                baseline_output=output_text,
                test_id=None,  # Will be assigned when saved
                created_at=datetime.now()
            ))
        return examples
    
    def clear(self):
        """Clear all inputs and reset the form."""
        self.task_description.clear()
        self.system_prompt.clear()
        self.examples_table.setRowCount(0)
        self.add_to_test_set_btn.setEnabled(False)
        
    def handle_error(self, error_message: str):
        """Handle errors from the worker."""
        # Close the progress dialog
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
        
        # Show the error message
        self.show_status(error_message, 7000)
        
    def cancel_generation(self):
        """Cancel the generation process."""
        if hasattr(self, 'worker') and self.worker:
            # Clean up the worker thread
            if hasattr(self.worker, '_thread') and self.worker._thread:
                self.worker._thread.quit()
                self.worker._thread.wait()
            
            # Reset worker
            self.worker = None
            
        self.show_status("Generation cancelled", 5000)
    
    def show_status(self, message, timeout=5000):
        """Show a message in the status bar."""
        main_window = self.window()
        if main_window is not self and main_window and hasattr(main_window, 'show_status'):
            main_window.show_status(message, timeout)
