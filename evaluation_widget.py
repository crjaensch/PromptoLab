from datetime import datetime
from pathlib import Path
import sys
from typing import List, Dict

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QComboBox, QPushButton, QTextEdit, QProgressBar,
                              QTableWidget, QTableWidgetItem, QMessageBox,
                              QGroupBox, QSplitter, QTabWidget,
                              QHeaderView, QFileDialog)
from PySide6.QtCore import Qt, Signal

# Add the project root directory to Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from models import TestSet
from test_storage import TestSetStorage
from output_analyzer import (OutputAnalyzer, AnalysisResult, AnalysisError,
                           LLMError, SimilarityError)
from llm_utils import run_llm_async, get_llm_models
from expandable_text import ExpandableTextWidget
from html_eval_report import HtmlEvalReport

class EvaluationWidget(QWidget):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.test_storage = TestSetStorage()
        self.output_analyzer = OutputAnalyzer()
        self.current_test_set = None
        self.current_llm_runner = None
        self.current_analyzer = None
        self.pending_cases = []
        self.evaluation_results = []  # Store accumulated results
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
        selector_layout.setSpacing(2)  # Reduce spacing between widgets
        test_set_label = QLabel("Test Set:")
        test_set_label.setFixedWidth(test_set_label.sizeHint().width())  # Set fixed width based on content
        selector_layout.addWidget(test_set_label)
        self.test_set_combo = QComboBox()
        self.test_set_combo.currentIndexChanged.connect(self.load_selected_test_set)
        selector_layout.addWidget(self.test_set_combo)
        
        # Add spacing between the pairs
        spacer = QWidget()
        spacer.setFixedWidth(20)  # 20px spacing
        selector_layout.addWidget(spacer)
        
        # Model Selection
        model_label = QLabel("Model:")
        model_label.setFixedWidth(model_label.sizeHint().width())  # Set fixed width based on content
        selector_layout.addWidget(model_label)
        self.model_combo = QComboBox()
        # Get available models dynamically
        available_models = get_llm_models()
        if available_models:
            self.model_combo.addItems(available_models)
        else:
            # Fallback to default model if we can't get the list
            self.model_combo.addItems(["gpt-4o-mini"])
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
            "Similarity", "LLM Grade"
        ])
        
        # Configure table properties
        header = self.results_table.horizontalHeader()
        
        # Set fixed widths for numeric columns
        self.results_table.setColumnWidth(3, 75)  # Similarity
        self.results_table.setColumnWidth(4, 75)  # LLM Grade
        
        # Configure header resize modes
        header.setStretchLastSection(False)  # Disable automatic stretch of last section
        
        # Make first three columns interactive and stretchable
        header.setSectionResizeMode(0, QHeaderView.Interactive)  # User Prompt
        header.setSectionResizeMode(1, QHeaderView.Interactive)  # Baseline Output
        header.setSectionResizeMode(2, QHeaderView.Interactive)  # Current Output
        header.setSectionResizeMode(3, QHeaderView.Fixed)    # Similarity
        header.setSectionResizeMode(4, QHeaderView.Fixed)    # LLM Grade
        
        # Set initial equal widths for the text columns
        available_width = self.results_table.viewport().width() - 150  # Subtract fixed columns
        column_width = available_width // 3
        for i in range(3):
            self.results_table.setColumnWidth(i, column_width)
        
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
        self.collapse_button = QPushButton("▼ Analysis")
        self.collapse_button.setStyleSheet("text-align: left; padding: 5px;")
        self.collapse_button.clicked.connect(self.toggle_analysis)
        analysis_layout.addWidget(self.collapse_button)
        
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
        
        # Export Results button
        self.export_button = QPushButton("Export Results")
        self.export_button.clicked.connect(self.export_results)
        self.export_button.setFixedWidth(self.export_button.sizeHint().width() + 20)  # Add 20px padding
        self.export_button.setEnabled(False)  # Initially disabled
        self.export_button.setStyleSheet("""
            QPushButton {
                padding: 5px 10px;
                background: white;
                color: black;
                border: 1px solid #ccc;
                border-radius: 2px;
            }
            QPushButton:hover {
                background: #f0f0f0;
                border-color: #999;
            }
            QPushButton:disabled {
                background: #f5f5f5;
                color: #999;
                border-color: #ddd;
            }
        """)
        bottom_layout.addWidget(self.export_button)
        
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
            
            # Show status message
            self.show_status("Evaluation run started...", 5000)
            
            # Clear previous results
            self.results_table.setRowCount(0)
            self.semantic_analysis.clear()
            self.llm_feedback.clear()
            self.evaluation_results = []  # Clear accumulated results
            
            # Clear analyzer history
            self.output_analyzer.clear_history()
            
            # Show progress bar and disable buttons
            self.progress_bar.show()
            self.progress_bar.setValue(0)
            self.progress_bar.setMaximum(len(self.current_test_set.cases))
            self.run_button.setEnabled(False)
            self.export_button.setEnabled(False)
            
            # Start with the first test case
            self.pending_cases = list(enumerate(self.current_test_set.cases))
            self._process_next_case(model)
            
        except Exception as e:
            self._handle_error("Unexpected error during evaluation", str(e))
            
    def _process_next_case(self, model):
        """Process the next test case in the queue."""
        if not self.pending_cases:
            self._finish_evaluation()
            return
            
        i, test_case = self.pending_cases.pop(0)
        
        # Start LLM generation
        self.current_llm_runner = run_llm_async(
            test_case.input_text,
            self.system_prompt_input.toPlainText(),
            model
        )
        
        def handle_llm_result(current_output):
            # Start analysis
            analyzer = self.output_analyzer.create_async_analyzer()
            analyzer.finished.connect(
                lambda result: self._handle_analysis_result(i, result)
            )
            analyzer.error.connect(
                lambda error: self._handle_error("Analysis Error", error)
            )
            
            # Store reference to prevent garbage collection
            self.current_analyzer = analyzer
            
            # Start the analysis
            analyzer.start_analysis(
                input_text=test_case.input_text,
                baseline=test_case.baseline_output,
                current=current_output,
                model=model
            )
            
        def handle_llm_error(error):
            self._handle_error("LLM Error", error)
            
        self.current_llm_runner.finished.connect(handle_llm_result)
        self.current_llm_runner.error.connect(handle_llm_error)
        
    def _handle_analysis_result(self, row, result):
        """Handle completion of analysis for a test case."""
        try:
            # Add row to results table
            self.results_table.insertRow(row)
            
            # Add items to the row
            self.results_table.setItem(row, 0, QTableWidgetItem(result.input_text))
            self.results_table.setItem(row, 1, QTableWidgetItem(result.baseline_output))
            self.results_table.setItem(row, 2, QTableWidgetItem(result.current_output))
            self.results_table.setItem(row, 3, QTableWidgetItem(f"{result.similarity_score:.2f}"))
            self.results_table.setItem(row, 4, QTableWidgetItem(result.llm_grade))
            
            # Store result in accumulator
            self.evaluation_results.append({
                "input_text": result.input_text,
                "baseline_output": result.baseline_output,
                "current_output": result.current_output,
                "similarity_score": result.similarity_score,
                "llm_grade": result.llm_grade
            })
            
            # Update progress
            self.progress_bar.setValue(row + 1)
            
            # Process next case if any
            model = self.model_combo.currentText()
            self._process_next_case(model)
            
        except Exception as e:
            self._handle_error("Error handling analysis result", str(e))
            
    def _finish_evaluation(self):
        """Clean up after evaluation is complete."""
        # Select the first row to show initial analysis
        if self.results_table.rowCount() > 0:
            self.results_table.selectRow(0)
        
        # Reset UI state
        self.progress_bar.hide()
        self.run_button.setEnabled(True)
        self.export_button.setEnabled(True)  # Enable export button after completion
        
        # Show completion message
        self.show_status("Evaluation run completed!", 5000)
        
    def _handle_error(self, title, message):
        """Handle errors during evaluation."""
        self.progress_bar.hide()
        self.run_button.setEnabled(True)
        self.export_button.setEnabled(len(self.evaluation_results) > 0)  # Only enable if we have results
        QMessageBox.critical(self, title, 
                           f"{title}: {message}\n\n"
                           "Please check your inputs and try again.")
        
    def show_status(self, message, timeout=5000):
        """Show a status message in the main window's status bar."""
        main_window = self.window()
        if main_window is not self and main_window and hasattr(main_window, 'show_status'):
            main_window.show_status(message, timeout)

    def toggle_analysis(self):
        if self.analysis_tabs.isVisible():
            # Store current sizes before hiding
            self.last_sizes = self.main_splitter.sizes()
            self.analysis_tabs.hide()
            self.collapse_button.setText("▶ Analysis")
            # Give all space to the upper section
            self.main_splitter.setSizes([self.main_splitter.size().height() - self.collapse_button.height(), 
                                       self.collapse_button.height()])
        else:
            self.analysis_tabs.show()
            self.collapse_button.setText("▼ Analysis")
            # Restore previous sizes if they exist
            if hasattr(self, 'last_sizes'):
                self.main_splitter.setSizes(self.last_sizes)
            else:
                # Default split if no previous sizes
                self.main_splitter.setSizes([700, 300])
            
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

    def resizeEvent(self, event):
        """Handle widget resize to maintain column proportions."""
        super().resizeEvent(event)
        
        # Only adjust if table exists and has correct number of columns
        if hasattr(self, 'results_table') and self.results_table.columnCount() == 5:
            # Calculate total width of user-adjustable columns
            adjustable_width = sum(self.results_table.columnWidth(i) for i in range(3))
            if adjustable_width == 0:  # Avoid division by zero
                return
                
            # Calculate new available width
            new_available = self.results_table.viewport().width() - 150  # Subtract fixed columns
            
            # Adjust each column proportionally
            for i in range(3):
                current_width = self.results_table.columnWidth(i)
                proportion = current_width / adjustable_width
                new_width = int(new_available * proportion)
                self.results_table.setColumnWidth(i, new_width)
                
    def showEvent(self, event):
        """Handle the widget being shown for the first time."""
        super().showEvent(event)
        # Trigger initial column sizing
        if hasattr(self, 'results_table') and self.results_table.columnCount() == 5:
            available_width = self.results_table.viewport().width() - 150  # Subtract fixed columns
            column_width = available_width // 3
            for i in range(3):
                self.results_table.setColumnWidth(i, column_width)
                
    def export_results(self):
        """Export evaluation results to an HTML file."""
        if not self.evaluation_results:
            QMessageBox.information(self, "No Results", "No evaluation results to export.")
            return
            
        # Prompt user for file location with default name and extension
        default_name = f"eval_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Export Results",
            default_name,
            "HTML Files (*.html)"
        )
        if not file_name:
            return
            
        # Prepare metadata
        metadata = {
            'test_set_name': self.current_test_set.name if self.current_test_set else 'N/A',
            'baseline_system_prompt': self.current_test_set.system_prompt if self.current_test_set else 'N/A',
            'new_system_prompt': self.system_prompt_input.toPlainText(),
            'model_name': self.model_combo.currentText()
        }
        
        # Generate HTML report
        report_generator = HtmlEvalReport()
        html_content = report_generator.generate_report(self.evaluation_results, metadata)
        
        # Write HTML content to file
        with open(file_name, "w", encoding='utf-8') as file:
            file.write(html_content)
            
        self.show_status("Evaluation results exported successfully", 5000)