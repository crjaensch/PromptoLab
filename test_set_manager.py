from datetime import datetime
import uuid
from pathlib import Path
import sys
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QTableWidget, QTableWidgetItem, QTextEdit, 
                              QComboBox, QLabel, QLineEdit, QHeaderView, QDialog, 
                              QDialogButtonBox, QProgressDialog)
from PySide6.QtCore import Qt, Signal, QObject, QSettings

# Add the project root directory to Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from models import TestSet, TestCase
from test_storage import TestSetStorage
from llm_utils import run_llm_async
from expandable_text import ExpandableTextWidget

class BaselineGeneratorSignals(QObject):
    """Signals for the baseline generator."""
    finished = Signal()
    progress = Signal(int)
    error = Signal(str)
    result = Signal(int, str)

class BaselineGeneratorWorker(QObject):
    """Worker for generating baselines using QProcess."""
    finished = Signal()
    progress = Signal(int)
    error = Signal(str)
    result = Signal(int, str)
    
    def __init__(self, row, user_prompt, system_prompt, model, max_tokens=None, temperature=None, top_p=None):
        super().__init__()
        self.row = row
        self.user_prompt = user_prompt
        self.system_prompt = system_prompt
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        self._test_runner = None  # For testing only
        
    def start(self):
        """Start the baseline generation process."""
        # Use test runner if provided (for testing only)
        if self._test_runner is not None:
            runner = self._test_runner
        else:
            runner = run_llm_async(
                self.user_prompt,
                self.system_prompt,
                self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=self.top_p
            )
        
        # Connect signals
        runner.finished.connect(self._handle_result)
        runner.error.connect(self.error.emit)
        
    def _handle_result(self, result):
        self.result.emit(self.row, result)
        self.finished.emit()

class TestSetManagerWidget(QWidget):
    test_set_updated = Signal(TestSet)  # Emitted when test set is modified
    
    def __init__(self, test_set_storage: TestSetStorage, settings: QSettings):
        super().__init__()
        self.settings = settings
        self.test_set_storage = test_set_storage
        self.current_test_set = None
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Test Set Info
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel("Test Set Name:"))
        self.name_input = QLineEdit()
        info_layout.addWidget(self.name_input)
        layout.addLayout(info_layout)
        
        # System Prompt
        system_prompt_label = QLabel("System Prompt:")
        layout.addWidget(system_prompt_label)
        
        self.system_prompt = ExpandableTextWidget()
        self.system_prompt.setFixedHeight(35)  # Initial collapsed height
        self.system_prompt.setPlaceholderText("Enter system prompt here...")
        self.system_prompt.expandedChanged.connect(self.on_system_prompt_expanded)
        self.system_prompt.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 2px;
                padding: 2px;
            }
        """)
        layout.addWidget(self.system_prompt)
        
        # Test Cases Table
        self.cases_table = QTableWidget()
        self.cases_table.setColumnCount(2)
        self.cases_table.setHorizontalHeaderLabels(["User Prompt", "Baseline Output"])
        # Configure headers to stretch but allow resizing
        header = self.cases_table.horizontalHeader()
        header.setStretchLastSection(True)  # Make last section stretch to fill remaining space
        header.setSectionResizeMode(0, QHeaderView.Interactive)  # Allow first column to be resized
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Last column stretches to fill space
        
        layout.addWidget(self.cases_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.add_case_btn = QPushButton("Add Test Case")
        self.remove_case_btn = QPushButton("Remove Selected")
        self.generate_baseline_btn = QPushButton("Generate Baseline")
        self.save_btn = QPushButton("Save Test Set")
        self.load_btn = QPushButton("Load Test Set")
        
        button_layout.addWidget(self.add_case_btn)
        button_layout.addWidget(self.remove_case_btn)
        button_layout.addWidget(self.generate_baseline_btn)
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.load_btn)
        layout.addLayout(button_layout)
        
        # Connect signals
        self.add_case_btn.clicked.connect(self.add_test_case)
        self.remove_case_btn.clicked.connect(self.remove_test_case)
        self.generate_baseline_btn.clicked.connect(self.generate_baseline)
        self.save_btn.clicked.connect(self.save_test_set)
        self.load_btn.clicked.connect(self.load_test_set)
        
    def showEvent(self, event):
        """Handle the widget being shown for the first time."""
        super().showEvent(event)
        # Set initial column widths to 1/3 and 2/3 ratio
        self.cases_table.horizontalHeader().resizeSection(0, self.width() // 3)
        
    def show_status(self, message, timeout=5000):
        """Show a message in the status bar."""
        main_window = self.window()
        if main_window is not self and main_window and hasattr(main_window, 'show_status'):
            main_window.show_status(message, timeout)
            
    def add_test_case(self):
        row = self.cases_table.rowCount()
        self.cases_table.insertRow(row)
        self.cases_table.setItem(row, 0, QTableWidgetItem(""))
        self.cases_table.setItem(row, 1, QTableWidgetItem(""))
        
    def remove_test_case(self):
        current_row = self.cases_table.currentRow()
        if current_row >= 0:
            self.cases_table.removeRow(current_row)
            
    def generate_baseline(self):
        """Generate baseline outputs for all test cases using the LLM asynchronously."""
        if self.cases_table.rowCount() == 0:
            self.show_status("No test cases to generate baselines for.", 5000)
            return
            
        # Get model and parameters from settings
        model = self.settings.value("selected_model", "gpt-4o-mini", str)
        if not model:
            self.show_status("No model selected in settings.", 5000)
            return
            
        max_tokens = self.settings.value("max_tokens", "", str)
        temperature = self.settings.value("temperature", "", str)
        top_p = self.settings.value("top_p", "", str)
        
        # Convert parameters to correct type if they're provided
        max_tokens = int(max_tokens) if max_tokens else None
        temperature = float(temperature) if temperature else None
        top_p = float(top_p) if top_p else None
        
        progress = QProgressDialog("Generating baseline outputs...", "Cancel", 0, self.cases_table.rowCount(), self)
        progress.setWindowModality(Qt.WindowModal)
        
        # Counter for completed tasks
        self.completed_tasks = 0
        self.active_workers = []
        
        def handle_result(row, baseline):
            self.cases_table.setItem(row, 1, QTableWidgetItem(baseline))
            self.completed_tasks += 1
            progress.setValue(self.completed_tasks)
            if self.completed_tasks == self.cases_table.rowCount():
                self.show_status("Baseline generation completed successfully!", 5000)
                
        def handle_error(error_msg):
            self.show_status(error_msg, 7000)
            
        try:
            for row in range(self.cases_table.rowCount()):
                if progress.wasCanceled():
                    break
                    
                # Get the user prompt
                user_prompt = self.cases_table.item(row, 0).text()
                if not user_prompt.strip():
                    self.completed_tasks += 1
                    continue
                    
                # Create and configure the worker
                worker = BaselineGeneratorWorker(
                    row,
                    user_prompt,
                    self.system_prompt.toPlainText(),
                    model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p
                )
                
                # Connect signals
                worker.result.connect(handle_result)
                worker.error.connect(handle_error)
                
                # Keep reference to prevent garbage collection
                self.active_workers.append(worker)
                
                # Start the worker
                worker.start()
                
        except Exception as e:
            self.show_status(f"Failed to generate baselines: {str(e)}", 7000)
            
    def save_test_set(self):
        if not self.name_input.text().strip():
            self.show_status("Please enter a test set name", 5000)
            return
            
        test_cases = []
        for row in range(self.cases_table.rowCount()):
            user_prompt = self.cases_table.item(row, 0).text()
            baseline = self.cases_table.item(row, 1).text()
            if user_prompt.strip():  # Only add non-empty test cases
                test_cases.append(TestCase(
                    input_text=user_prompt,
                    baseline_output=baseline if baseline.strip() else None,
                    test_id=str(uuid.uuid4()),
                    created_at=datetime.now()
                ))
                
        test_set = TestSet(
            name=self.name_input.text(),
            cases=test_cases,
            system_prompt=self.system_prompt.toPlainText(),
            created_at=datetime.now(),
            last_modified=datetime.now()
        )
        
        try:
            self.test_set_storage.save_test_set(test_set)
            self.current_test_set = test_set
            self.test_set_updated.emit(test_set)
            self.show_status("Test set saved successfully!", 5000)
        except Exception as e:
            self.show_status(f"Failed to save test set: {str(e)}", 7000)
            
    def load_test_set(self):
        """Load a test set from storage."""
        # Get list of available test sets
        test_sets = self.test_set_storage.get_all_test_sets()
        if not test_sets:
            self.show_status("No test sets available to load.", 5000)
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Load Test Set")
        layout = QVBoxLayout(dialog)
        
        combo = QComboBox()
        combo.addItems(test_sets)
        layout.addWidget(combo)
        
        # Add buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec() == QDialog.Accepted:
            selected_name = combo.currentText()
            test_set = self.test_set_storage.load_test_set(selected_name)
            if test_set:
                # Update UI with loaded test set
                self.clear()  # Clear current data
                self.name_input.setText(test_set.name)
                self.system_prompt.setPlainText(test_set.system_prompt)
                
                # Add test cases to table
                for case in test_set.cases:
                    row = self.cases_table.rowCount()
                    self.cases_table.insertRow(row)
                    self.cases_table.setItem(row, 0, QTableWidgetItem(case.input_text))
                    self.cases_table.setItem(row, 1, QTableWidgetItem(case.baseline_output or ""))
                
                self.current_test_set = test_set
                self.test_set_updated.emit(test_set)
                self.show_status(f"Test set '{selected_name}' loaded successfully!", 5000)
            else:
                self.show_status(f"Failed to load test set '{selected_name}'", 7000)
                
    def clear(self):
        """Clear all inputs and reset the form."""
        self.name_input.clear()
        self.system_prompt.clear()
        self.cases_table.setRowCount(0)
        self.current_test_set = None
        
    def on_system_prompt_expanded(self, expanded: bool):
        """Handle system prompt expansion/collapse."""
        if expanded:
            self.system_prompt.setFixedHeight(400)  # Expanded height
        else:
            self.system_prompt.setFixedHeight(35)   # Collapsed height
