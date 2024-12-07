from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QTableWidget, QTableWidgetItem, QTextEdit, 
                              QComboBox, QLabel, QLineEdit, QMessageBox,
                              QItemDelegate, QFrame, QSplitter, QGroupBox,
                              QCheckBox, QInputDialog, QProgressDialog, QHeaderView,
                              QTabWidget)
from PySide6.QtCore import Qt, Signal, QSettings, Slot, QThread
from PySide6.QtCharts import QChart, QChartView, QBarSet, QBarSeries, QValueAxis, QBarCategoryAxis
from PySide6.QtGui import QPainter

from .test_storage import TestSetStorage
from .llm_utils import run_llm
from .output_analyzer import OutputAnalyzer, OutputAnalysis, DifferenceAnalysis
from .models import TestSet, TestCase

from datetime import datetime
import uuid

from typing import List, Dict, Optional, Tuple

class MultilineTextDelegate(QItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QTextEdit(parent)
        editor.setStyleSheet("""
            QTextEdit {
                padding: 16px;
                min-height: 100px;
                border: 1px solid #E5E7EB;
            }
        """)
        return editor

    def setEditorData(self, editor, index):
        editor.setPlainText(index.data())

    def setModelData(self, editor, model, index):
        model.setData(index, editor.toPlainText())

class ExpandableTextWidget(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(False)

class LLMEvaluationWorker(QThread):
    """Worker thread for running LLM evaluations."""
    progress = Signal(int)
    finished = Signal()

    def __init__(self, test_cases: List[TestCase], system_prompt: str, model: str = "gpt-4o-mini"):
        super().__init__()
        self.test_cases = test_cases
        self.system_prompt = system_prompt
        self.model = model
        
    def run(self):
        total = len(self.test_cases)
        for i, test_case in enumerate(self.test_cases):
            try:
                result = run_llm(
                    user_prompt=test_case.input_text,
                    system_prompt=self.system_prompt,
                    model=self.model
                )
                test_case.current_output = result
            except Exception as e:
                print(f"Error running test case: {e}")
            
            self.progress.emit(int((i + 1) * 100 / total))
            
        self.finished.emit()

class EvaluationWidget(QWidget):
    """Main widget for the system prompt evaluation tool."""
    
    test_set_saved = Signal(str)
    test_set_loaded = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_test_set = None
        self.output_analyzer = OutputAnalyzer()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Top Bar: Test Set Management
        test_set_frame = QFrame()
        test_set_frame.setFrameStyle(QFrame.StyledPanel)
        test_set_frame.setStyleSheet("""
            QFrame { 
                border: 1px solid #E5E7EB;
                padding: 8px;
                margin-bottom: 8px;
            }
        """)
        test_set_layout = QHBoxLayout(test_set_frame)
        test_set_layout.setSpacing(16)

        # Test Set Name and Model Selection
        test_set_layout.addWidget(QLabel("Test Set:"))
        self.test_set_name = QLineEdit()
        self.test_set_name.setFixedWidth(200)
        self.test_set_name.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #E5E7EB;
                min-height: 40px;
            }
        """)
        test_set_layout.addWidget(self.test_set_name)

        self.model_combo = QComboBox()
        self.model_combo.addItems(["gpt-4o-mini", "gpt-4o", "o1-mini", "o1-preview", "groq-llama3.1", "groq-llama3.3"])
        self.model_combo.setFixedWidth(150)
        self.model_combo.setFixedHeight(40)
        self.model_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #E5E7EB;
            }
        """)
        test_set_layout.addWidget(QLabel("Model:"))
        test_set_layout.addWidget(self.model_combo)
        
        # Test Set Actions
        self.new_test_set_btn = QPushButton("New Test Set")
        self.load_test_set_btn = QPushButton("Load Test Set")
        self.save_test_set_btn = QPushButton("Save Test Set")
        for btn in [self.new_test_set_btn, self.load_test_set_btn, self.save_test_set_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    padding: 8px 16px;
                    border: 1px solid #E5E7EB;
                    min-height: 40px;
                    min-width: 120px;
                }
                QPushButton:hover {
                    background: #F3F4F6;
                }
            """)
            test_set_layout.addWidget(btn)
        
        test_set_layout.addStretch()
        layout.addWidget(test_set_frame)

        # Main content splitter
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setChildrenCollapsible(False)
        main_splitter.setStyleSheet("""
            QSplitter {
                padding: 4px;
            }
            QSplitter::handle {
                background: #E5E7EB;
                width: 4px;
            }
            QSplitter::handle:hover {
                background: #D1D5DB;
            }
            QSplitter::handle:pressed {
                background: #9CA3AF;
            }
        """)

        # Left Panel: Test Cases and Actions
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Test Cases Table
        test_cases_group = QGroupBox("Test Cases")
        test_cases_layout = QVBoxLayout(test_cases_group)
        self.test_cases_table = QTableWidget()
        self.test_cases_table.setColumnCount(2)
        self.test_cases_table.setHorizontalHeaderLabels(["User Prompt", "Baseline Output"])
        self.test_cases_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.test_cases_table.setMinimumHeight(300)
        test_cases_layout.addWidget(self.test_cases_table)
        
        # Test Case Actions
        test_case_actions = QHBoxLayout()
        self.add_test_case_btn = QPushButton("Add Test Case")
        self.remove_test_case_btn = QPushButton("Remove Test Case")
        self.generate_baseline_btn = QPushButton("Generate Baseline")
        for btn in [self.add_test_case_btn, self.remove_test_case_btn, self.generate_baseline_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    padding: 8px 16px;
                    border: 1px solid #E5E7EB;
                    min-height: 40px;
                }
                QPushButton:hover {
                    background: #F3F4F6;
                }
            """)
            test_case_actions.addWidget(btn)
        test_cases_layout.addLayout(test_case_actions)
        left_layout.addWidget(test_cases_group)
        
        # Right Panel: System Prompts and Evaluation
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # System Prompts
        prompts_group = QGroupBox("System Prompts")
        prompts_layout = QVBoxLayout(prompts_group)
        
        baseline_layout = QVBoxLayout()
        baseline_layout.addWidget(QLabel("Baseline System Prompt:"))
        self.baseline_prompt = ExpandableTextWidget()
        self.baseline_prompt.setMinimumHeight(100)
        baseline_layout.addWidget(self.baseline_prompt)
        
        proposed_layout = QVBoxLayout()
        proposed_layout.addWidget(QLabel("Proposed System Prompt:"))
        self.proposed_prompt = ExpandableTextWidget()
        self.proposed_prompt.setMinimumHeight(100)
        proposed_layout.addWidget(self.proposed_prompt)
        
        prompts_layout.addLayout(baseline_layout)
        prompts_layout.addLayout(proposed_layout)
        right_layout.addWidget(prompts_group)
        
        # Evaluation Results
        results_group = QGroupBox("Evaluation Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels([
            "User Prompt", "Baseline Output", "Current Output", "Semantic Sim.", "LLM Grade"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.setMinimumHeight(200)
        results_layout.addWidget(self.results_table)
        
        # Difference Analysis with tabs
        analysis_tabs = QTabWidget()
        
        # Semantic similarity tab
        self.semantic_view = ExpandableTextWidget()
        self.semantic_view.setMinimumHeight(100)
        self.semantic_view.setReadOnly(True)
        analysis_tabs.addTab(self.semantic_view, "Semantic Analysis")
        
        # LLM feedback tab
        self.llm_feedback_view = ExpandableTextWidget()
        self.llm_feedback_view.setMinimumHeight(100)
        self.llm_feedback_view.setReadOnly(True)
        analysis_tabs.addTab(self.llm_feedback_view, "LLM Feedback")
        
        results_layout.addWidget(QLabel("Analysis:"))
        results_layout.addWidget(analysis_tabs)
        
        right_layout.addWidget(results_group)
        
        # Run Evaluation Button
        self.run_eval_btn = QPushButton("Run Evaluation")
        self.run_eval_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border: 1px solid #E5E7EB;
                min-height: 40px;
                background: #4F46E5;
                color: white;
            }
            QPushButton:hover {
                background: #4338CA;
            }
        """)
        right_layout.addWidget(self.run_eval_btn)
        
        # Add panels to splitter
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([400, 600])  # 40% left, 60% right
        
        layout.addWidget(main_splitter)
        
        # Connect signals
        self.new_test_set_btn.clicked.connect(self.new_test_set)
        self.load_test_set_btn.clicked.connect(self.load_test_set)
        self.save_test_set_btn.clicked.connect(self.save_test_set)
        self.add_test_case_btn.clicked.connect(self.add_test_case)
        self.remove_test_case_btn.clicked.connect(self.remove_test_case)
        self.generate_baseline_btn.clicked.connect(self.generate_baseline)
        self.run_eval_btn.clicked.connect(self.run_evaluation)
        self.results_table.itemSelectionChanged.connect(self.update_diff_view)
        
    def new_test_set(self):
        self.current_test_set = TestSet(name=f"Test Set {uuid.uuid4()}", cases=[])
        self.test_set_name.setText(self.current_test_set.name)
        self.test_cases_table.setRowCount(0)
        
    def load_test_set(self):
        test_sets = TestSetStorage().get_all_test_sets()
        if not test_sets:
            QMessageBox.information(self, "Info", "No test sets found")
            return

        name, ok = QInputDialog.getItem(
            self, "Load Test Set", "Select test set:", test_sets, 0, False
        )
        if not ok:
            return

        self.current_test_set = TestSetStorage().load_test_set(name)
        if not self.current_test_set:
            return

        self.test_set_name.setText(self.current_test_set.name)
        self.test_cases_table.setRowCount(len(self.current_test_set.cases))
        for i, test_case in enumerate(self.current_test_set.cases):
            self.test_cases_table.setItem(i, 0, QTableWidgetItem(test_case.input_text))
            self.test_cases_table.setItem(i, 1, QTableWidgetItem(test_case.baseline_output or ""))
            
    def save_test_set(self):
        if not self.current_test_set:
            QMessageBox.warning(self, "Error", "Please create or load a test set first")
            return

        self.current_test_set.name = self.test_set_name.text()
        self.current_test_set.cases = []
        for row in range(self.test_cases_table.rowCount()):
            input_text = self.test_cases_table.item(row, 0).text()
            baseline_output = self.test_cases_table.item(row, 1).text()
            self.current_test_set.cases.append(TestCase(input_text, baseline_output))
        TestSetStorage().save_test_set(self.current_test_set)
        self.test_set_saved.emit(self.current_test_set.name)
        
    def add_test_case(self):
        if not self.current_test_set:
            QMessageBox.warning(self, "Error", "Please create or load a test set first")
            return

        row = self.test_cases_table.rowCount()
        self.test_cases_table.insertRow(row)
        self.test_cases_table.setItem(row, 0, QTableWidgetItem(""))
        self.test_cases_table.setItem(row, 1, QTableWidgetItem(""))
        
    def remove_test_case(self):
        if not self.current_test_set:
            QMessageBox.warning(self, "Error", "Please create or load a test set first")
            return

        selected_items = self.test_cases_table.selectedItems()
        if not selected_items:
            return
            
        row = selected_items[0].row()
        self.test_cases_table.removeRow(row)
        
    def generate_baseline(self):
        if not self.current_test_set:
            QMessageBox.warning(self, "Error", "Please create or load a test set first")
            return

        model = self.model_combo.currentText()
        baseline_system = self.baseline_prompt.toPlainText() or None
        for row in range(self.test_cases_table.rowCount()):
            input_text = self.test_cases_table.item(row, 0).text()
            if not input_text:
                continue

            try:
                result = run_llm(
                    user_prompt=input_text,
                    system_prompt=baseline_system,
                    model=model
                )
                self.test_cases_table.setItem(row, 1, QTableWidgetItem(result))
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to generate baseline: {str(e)}")
                
    def run_evaluation(self):
        if not self.current_test_set:
            QMessageBox.warning(self, "Error", "Please create or load a test set first")
            return

        model = self.model_combo.currentText()
        proposed_system = self.proposed_prompt.toPlainText()
        if not proposed_system:
            QMessageBox.warning(self, "Error", "Please enter a proposed system prompt")
            return

        # Clear previous results
        self.results_table.setRowCount(0)
        
        # Show progress dialog
        progress = QProgressDialog("Running evaluation...", None, 0, len(self.current_test_set.cases), self)
        progress.setWindowModality(Qt.WindowModal)

        for i, test_case in enumerate(self.current_test_set.cases):
            progress.setValue(i)
            if progress.wasCanceled():
                break

            if not test_case.user_prompt:
                continue

            try:
                # Generate new output
                current_output = run_llm(
                    user_prompt=test_case.user_prompt,
                    system_prompt=proposed_system,
                    model=model
                )
                
                # Analyze the output
                analysis = self.output_analyzer.analyze_differences(
                    baseline=test_case.baseline_output,
                    proposed=current_output
                )
                
                # Add to results table
                row = self.results_table.rowCount()
                self.results_table.insertRow(row)
                self.results_table.setItem(row, 0, QTableWidgetItem(test_case.user_prompt))
                self.results_table.setItem(row, 1, QTableWidgetItem(test_case.baseline_output))
                self.results_table.setItem(row, 2, QTableWidgetItem(current_output))
                self.results_table.setItem(row, 3, QTableWidgetItem(f"{analysis.similarity_breakdown['Overall']:.3f}"))
                self.results_table.setItem(row, 4, QTableWidgetItem("Pass" if analysis.similarity_breakdown['Overall'] > 0.8 else "Fail"))
                
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to evaluate test case: {str(e)}")

        progress.setValue(len(self.current_test_set.cases))

    def update_diff_view(self):
        selected_items = self.results_table.selectedItems()
        if not selected_items:
            return
            
        row = selected_items[0].row()
        
        user_prompt = self.results_table.item(row, 0).text()
        baseline_output = self.results_table.item(row, 1).text()
        current_output = self.results_table.item(row, 2).text()
        
        if baseline_output and current_output:
            # Get fresh analysis
            analysis = self.output_analyzer.analyze_differences(
                baseline=baseline_output,
                proposed=current_output
            )
            
            # Update semantic similarity view
            semantic_text = "Sentence-by-sentence Similarity:\n\n"
            for sentence, similarity in analysis.similarity_breakdown.items():
                semantic_text += f"{sentence}\nSimilarity: {similarity:.3f}\n\n"
            self.semantic_view.setPlainText(semantic_text)
            
            # Update LLM feedback view
            llm_text = f"Grade: {'Pass' if analysis.similarity_breakdown['Overall'] > 0.8 else 'Fail'}\n\n"
            self.llm_feedback_view.setPlainText(llm_text)