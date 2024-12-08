from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QComboBox, QPushButton, QTextEdit, QProgressBar,
                               QTableWidget, QTableWidgetItem, QMessageBox,
                               QGroupBox, QFrame, QSplitter, QTabWidget,
                               QHeaderView, QApplication)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from .models import TestSet
from .test_storage import TestSetStorage
from .output_analyzer import (OutputAnalyzer, AnalysisResult, AnalysisError,
                            LLMError, SimilarityError)
from .llm_utils import run_llm
from .expandable_text import ExpandableTextWidget

from datetime import datetime
from typing import List, Dict, Optional, Tuple

class EvaluationWidget(QWidget):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.test_storage = TestSetStorage()
        self.output_analyzer = OutputAnalyzer()
        self.current_test_set = None
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Main splitter to allow resizing between table and analysis
        self.main_splitter = QSplitter(Qt.Vertical)
        layout.addWidget(self.main_splitter)
        
        # Upper section for controls and table
        upper_widget = QWidget()
        upper_layout = QVBoxLayout(upper_widget)
        upper_layout.setContentsMargins(0, 0, 0, 0)
        
        # Test Set Selection
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Test Set:"))
        self.test_set_combo = QComboBox()
        self.test_set_combo.currentIndexChanged.connect(self.load_selected_test_set)
        selector_layout.addWidget(self.test_set_combo)
        
        # Model Selection
        selector_layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["gpt-4o-mini", "gpt-4o", "o1-mini", "o1-preview", "groq-llama3.1", "groq-llama3.3"])
        selector_layout.addWidget(self.model_combo)
        
        upper_layout.addLayout(selector_layout)

        # System Prompt Input
        system_prompt_label = QLabel("New System Prompt")
        system_prompt_label.setStyleSheet("QLabel { color: #666; margin-bottom: 2px; }")
        upper_layout.addWidget(system_prompt_label)
        
        self.system_prompt_input = ExpandableTextWidget()
        self.system_prompt_input.setFixedHeight(35)
        self.system_prompt_input.setPlaceholderText("Enter the new system prompt to evaluate...")
        self.system_prompt_input.expandedChanged.connect(self.on_system_prompt_expanded)
        self.system_prompt_input.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 2px;
                padding: 2px;
            }
        """)
        upper_layout.addWidget(self.system_prompt_input)
        
        # Results Table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels([
            "User Prompt", "Baseline Output", "Current Output",
            "Semantic Sim.", "LLM Grade"
        ])
        
        # Configure table properties
        header = self.results_table.horizontalHeader()
        
        # Set specific widths for numeric columns
        self.results_table.setColumnWidth(3, 100)  # Semantic Sim.
        self.results_table.setColumnWidth(4, 80)   # LLM Grade
        
        # Make the text columns stretch to fill remaining space
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # User Prompt
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Baseline Output
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Current Output
        header.setSectionResizeMode(3, QHeaderView.Fixed)    # Semantic Sim.
        header.setSectionResizeMode(4, QHeaderView.Fixed)    # LLM Grade
        
        # Enable text wrapping and auto-adjust row heights
        self.results_table.setWordWrap(True)
        self.results_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        # Connect selection changed signal
        self.results_table.itemSelectionChanged.connect(self.on_table_selection_changed)
        
        upper_layout.addWidget(self.results_table)
        self.main_splitter.addWidget(upper_widget)
        
        # Lower section for analysis
        self.analysis_widget = QWidget()
        analysis_layout = QVBoxLayout(self.analysis_widget)
        analysis_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add collapse/expand button for analysis section
        collapse_button = QPushButton("▼ Analysis")
        collapse_button.setStyleSheet("text-align: left; padding: 5px;")
        collapse_button.clicked.connect(self.toggle_analysis)
        analysis_layout.addWidget(collapse_button)
        
        # Analysis tabs
        self.analysis_tabs = QTabWidget()
        self.semantic_analysis = QTextEdit()
        self.semantic_analysis.setReadOnly(True)
        self.llm_feedback = QTextEdit()
        self.llm_feedback.setReadOnly(True)
        
        self.analysis_tabs.addTab(self.semantic_analysis, "Semantic Analysis")
        self.analysis_tabs.addTab(self.llm_feedback, "LLM Feedback")
        analysis_layout.addWidget(self.analysis_tabs)
        
        self.main_splitter.addWidget(self.analysis_widget)
        
        # Set initial splitter sizes to favor the table
        self.main_splitter.setSizes([700, 300])
        
        # Add Run Evaluation button and progress bar in a horizontal layout
        bottom_layout = QHBoxLayout()
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Processing test case %v of %m")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 2px;
                text-align: center;
                padding: 1px;
                background: white;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                width: 1px;
            }
        """)
        self.progress_bar.hide()  # Initially hidden
        bottom_layout.addWidget(self.progress_bar, stretch=1)
        
        # Run Evaluation button
        self.run_button = QPushButton("Run Evaluation")
        self.run_button.clicked.connect(self.run_evaluation)
        self.run_button.setStyleSheet("""
            QPushButton {
                padding: 5px 15px;
                background: #2ecc71;
                color: white;
                border: none;
                border-radius: 2px;
            }
            QPushButton:hover {
                background: #27ae60;
            }
            QPushButton:disabled {
                background: #95a5a6;
            }
        """)
        bottom_layout.addWidget(self.run_button)
        
        layout.addLayout(bottom_layout)
        
        self.refresh_test_sets()
        
    def refresh_test_sets(self):
        """Update the test set combo box with available test sets."""
        self.test_set_combo.clear()
        test_set_names = self.test_storage.get_all_test_sets()
        for name in test_set_names:
            test_set = self.test_storage.load_test_set(name)
            if test_set:
                self.test_set_combo.addItem(test_set.name, userData=test_set)
            
    def load_selected_test_set(self, index):
        """Load the selected test set and update the UI."""
        if index >= 0:
            self.current_test_set = self.test_set_combo.itemData(index)
            self.update_results_table()
            
    def update_results_table(self):
        """Update the results table with current test set data."""
        self.results_table.setRowCount(0)
        if not self.current_test_set:
            return
            
        for case in self.current_test_set.cases:
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            self.results_table.setItem(row, 0, QTableWidgetItem(case.input_text))
            self.results_table.setItem(row, 1, QTableWidgetItem(case.baseline_output or ""))
            self.results_table.setItem(row, 2, QTableWidgetItem(case.current_output or ""))
            # Semantic similarity and LLM grade will be populated during evaluation
            
    def run_evaluation(self):
        """Run evaluation on the current test set."""
        try:
            if not self.current_test_set:
                raise RuntimeError("No test set selected")
            
            if not self.current_test_set.cases:
                raise RuntimeError("Selected test set has no test cases")
            
            model = self.model_combo.currentText()
            
            # Clear previous results
            self.results_table.setRowCount(0)
            self.semantic_analysis.clear()
            self.llm_feedback.clear()
            
            # Clear analyzer history
            self.output_analyzer.clear_history()
            
            # Show progress bar and disable run button
            self.progress_bar.show()
            self.progress_bar.setValue(0)
            self.progress_bar.setMaximum(len(self.current_test_set.cases))
            self.run_button.setEnabled(False)
            
            # Process each test case
            for i, test_case in enumerate(self.current_test_set.cases):
                # Generate current output
                current = run_llm(test_case.input_text, self.system_prompt_input.toPlainText(), model)
                
                # Analyze the test case
                result = self.output_analyzer.analyze_test_case(
                    input_text=test_case.input_text,
                    baseline=test_case.baseline_output,
                    current=current,
                    model=model
                )
                
                # Add row to results table
                row = self.results_table.rowCount()
                self.results_table.insertRow(row)
                
                # Add items to the row
                self.results_table.setItem(row, 0, QTableWidgetItem(result.input_text))
                self.results_table.setItem(row, 1, QTableWidgetItem(result.baseline_output))
                self.results_table.setItem(row, 2, QTableWidgetItem(result.current_output))
                self.results_table.setItem(row, 3, QTableWidgetItem(f"{result.similarity_score:.2f}"))
                self.results_table.setItem(row, 4, QTableWidgetItem(result.llm_grade))
                
                # Update progress
                self.progress_bar.setValue(i + 1)
                QApplication.processEvents()  # Allow UI updates
            
            # Select the first row to show initial analysis
            if self.results_table.rowCount() > 0:
                self.results_table.selectRow(0)
            
            # Reset UI state
            self.progress_bar.hide()
            self.run_button.setEnabled(True)
            
        except LLMError as e:
            self.progress_bar.hide()
            self.run_button.setEnabled(True)
            QMessageBox.critical(self, "LLM Error", 
                               f"Error during LLM processing: {str(e)}\n\n"
                               "Please check your model settings and try again.")
            
        except SimilarityError as e:
            self.progress_bar.hide()
            self.run_button.setEnabled(True)
            QMessageBox.critical(self, "Analysis Error", 
                               f"Error computing similarity: {str(e)}\n\n"
                               "Please check your inputs and try again.")
            
        except AnalysisError as e:
            self.progress_bar.hide()
            self.run_button.setEnabled(True)
            QMessageBox.critical(self, "Analysis Error", 
                               f"Error during analysis: {str(e)}\n\n"
                               "Please check your inputs and try again.")
            
        except Exception as e:
            self.progress_bar.hide()
            self.run_button.setEnabled(True)
            QMessageBox.critical(self, "Error", 
                               f"Unexpected error during evaluation: {str(e)}\n\n"
                               "Please check the application logs for more details.")
            
    def toggle_analysis(self):
        if self.analysis_widget.isVisible():
            self.analysis_widget.hide()
            self.sender().setText("▶ Analysis")
        else:
            self.analysis_widget.show()
            self.sender().setText("▼ Analysis")
            
    def on_table_selection_changed(self):
        """Handle table selection changes by updating analysis displays."""
        # Force the table to recalculate row heights
        self.results_table.resizeRowsToContents()
        
        # Get selected items
        selected_items = self.results_table.selectedItems()
        if not selected_items:
            return
            
        # Get the row index
        row = selected_items[0].row()
        
        # Update analysis text areas
        self.semantic_analysis.setText(self.output_analyzer.get_analysis_text(row))
        self.llm_feedback.setText(self.output_analyzer.get_feedback_text(row))
        
        # Scroll to make the selected row fully visible
        self.results_table.scrollToItem(selected_items[0])

    def on_system_prompt_expanded(self, is_expanded: bool):
        """Handle system prompt expansion/contraction"""
        if is_expanded:
            self.system_prompt_input.setFixedHeight(200)
        else:
            self.system_prompt_input.setFixedHeight(35)
        
        # Force the group box to resize to its content
        # self.system_prompt_group.adjustSize()
        # self.system_prompt_group.updateGeometry()
            
    def update_test_set(self, test_set: TestSet):
        """Update the widget when a test set is modified externally."""
        self.refresh_test_sets()
        # Select the updated test set
        index = self.test_set_combo.findText(test_set.name)
        if index >= 0:
            self.test_set_combo.setCurrentIndex(index)