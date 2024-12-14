from datetime import datetime
import uuid
from pathlib import Path
import sys
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QTableWidget, QTableWidgetItem, QTextEdit, 
                              QComboBox, QLabel, QLineEdit, QMessageBox,
                              QHeaderView, QDialog, QDialogButtonBox, QProgressDialog)
from PySide6.QtCore import Qt, Signal

# Add the project root directory to Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from models import TestSet, TestCase
from test_storage import TestSetStorage
from llm_utils import run_llm
from expandable_text import ExpandableTextWidget

class TestSetManagerWidget(QWidget):
    test_set_updated = Signal(TestSet)  # Emitted when test set is modified
    
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.test_storage = TestSetStorage()
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
        layout.addWidget(QLabel("System Prompt:"))
        self.system_prompt = ExpandableTextWidget()
        # Set height for approximately 2 lines of text (using font metrics)
        self.system_prompt.setMinimumHeight(35)  # Smaller initial height for 2 lines
        self.system_prompt.setMaximumHeight(35)  # Force initial height to be small
        self.system_prompt.setPlaceholderText("Enter system prompt here...")
        layout.addWidget(self.system_prompt)
        
        # Test Cases Table
        self.cases_table = QTableWidget()
        self.cases_table.setColumnCount(2)
        self.cases_table.setHorizontalHeaderLabels(["User Prompt", "Baseline Output"])
        self.cases_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
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
        """Generate baseline outputs for all test cases using the LLM."""
        if not self.system_prompt.toPlainText().strip():
            QMessageBox.warning(self, "Error", "Please enter a system prompt first")
            return
            
        # Get the model from settings or use default
        model = self.settings.value("default_model", "gpt-4o-mini", str)
        
        # Get LLM parameters from settings
        max_tokens = self.settings.value("max_tokens", "", str)
        temperature = self.settings.value("temperature", "", str)
        top_p = self.settings.value("top_p", "", str)
        
        # Convert parameters to correct type if they're provided
        max_tokens = int(max_tokens) if max_tokens else None
        temperature = float(temperature) if temperature else None
        top_p = float(top_p) if top_p else None
        
        progress = QProgressDialog("Generating baseline outputs...", "Cancel", 0, self.cases_table.rowCount(), self)
        progress.setWindowModality(Qt.WindowModal)
        
        try:
            for row in range(self.cases_table.rowCount()):
                if progress.wasCanceled():
                    break
                    
                # Update progress
                progress.setValue(row)
                
                # Get the user prompt
                user_prompt = self.cases_table.item(row, 0).text()
                if not user_prompt.strip():
                    continue
                    
                try:
                    # Generate baseline using LLM with optional parameters
                    baseline = run_llm(
                        user_prompt,
                        self.system_prompt.toPlainText(),
                        model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        top_p=top_p
                    )
                    
                    # Update the baseline output in the table
                    self.cases_table.setItem(row, 1, QTableWidgetItem(baseline))
                    
                except Exception as e:
                    QMessageBox.warning(
                        self,
                        "Error",
                        f"Failed to generate baseline for row {row + 1}: {str(e)}"
                    )
                    
            progress.setValue(self.cases_table.rowCount())
            QMessageBox.information(self, "Success", "Baseline generation completed!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate baselines: {str(e)}")
            
    def save_test_set(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Error", "Please enter a test set name")
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
            self.test_storage.save_test_set(test_set)
            self.current_test_set = test_set
            self.test_set_updated.emit(test_set)
            QMessageBox.information(self, "Success", "Test set saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save test set: {str(e)}")
            
    def load_test_set(self):
        """Load a test set from storage."""
        # Get list of available test sets
        test_set_names = self.test_storage.get_all_test_sets()
        if not test_set_names:
            QMessageBox.information(self, "Info", "No test sets available to load")
            return

        # Create dialog to select test set
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Test Set")
        layout = QVBoxLayout(dialog)
        
        # Add combo box with test set names
        combo = QComboBox()
        combo.addItems(test_set_names)
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
            test_set = self.test_storage.load_test_set(selected_name)
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
                QMessageBox.information(self, "Success", f"Test set '{selected_name}' loaded successfully!")
            else:
                QMessageBox.critical(self, "Error", f"Failed to load test set '{selected_name}'")
                
    def clear(self):
        """Clear all inputs and reset the form."""
        self.name_input.clear()
        self.system_prompt.clear()
        self.cases_table.setRowCount(0)
        self.current_test_set = None
