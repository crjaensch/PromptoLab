# prompt_nanny/evaluation_widget.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QTableWidget, QTableWidgetItem, QTextEdit, 
                              QComboBox, QLabel, QLineEdit, QMessageBox,
                              QItemDelegate)
from PySide6.QtCore import Qt, Signal
from .models import TestCase, TestSet
from .test_storage import TestSetStorage
from .llm_utils import run_llm

class MultilineTextDelegate(QItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QTextEdit(parent)
        return editor

    def setEditorData(self, editor, index):
        editor.setPlainText(index.data())

    def setModelData(self, editor, model, index):
        model.setData(index, editor.toPlainText())

class EvaluationWidget(QWidget):
    test_set_saved = Signal(str)  # Signal emitted when a test set is saved
    test_set_loaded = Signal(str)  # Signal emitted when a test set is loaded

    def __init__(self, parent=None):
        super().__init__(parent)
        self.storage = TestSetStorage()
        self.current_test_set = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Test Set Management
        test_set_layout = QHBoxLayout()
        self.test_set_name = QLineEdit()
        self.test_set_name.setPlaceholderText("Test Set Name")
        test_set_layout.addWidget(self.test_set_name)

        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "gpt-4o-mini", "gpt-4o", "claude-3.5-sonnet",
            "claude-3.5-haiku", "gemini-flash", "gemini-1.5-pro"
        ])
        test_set_layout.addWidget(QLabel("Model:"))
        test_set_layout.addWidget(self.model_combo)
        layout.addLayout(test_set_layout)

        # Test Cases Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Input", "Baseline Output", "Current Output"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setItemDelegate(MultilineTextDelegate())
        layout.addWidget(self.table)

        # Control Buttons
        buttons_layout = QHBoxLayout()
        
        add_row_btn = QPushButton("Add Row")
        add_row_btn.clicked.connect(self.add_row)
        
        generate_baseline_btn = QPushButton("Generate Baseline")
        generate_baseline_btn.clicked.connect(self.generate_baseline)
        
        self.freeze_baseline_btn = QPushButton("Freeze Baseline")
        self.freeze_baseline_btn.setCheckable(True)
        self.freeze_baseline_btn.clicked.connect(self.toggle_baseline_frozen)
        
        save_btn = QPushButton("Save Test Set")
        save_btn.clicked.connect(self.save_test_set)
        
        load_btn = QPushButton("Load Test Set")
        load_btn.clicked.connect(self.load_test_set)
        
        run_current_btn = QPushButton("Run Current")
        run_current_btn.clicked.connect(self.run_current)

        for btn in [add_row_btn, generate_baseline_btn, self.freeze_baseline_btn,
                   save_btn, load_btn, run_current_btn]:
            buttons_layout.addWidget(btn)
        
        layout.addLayout(buttons_layout)

    def add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col in range(3):
            editor = QTextEdit()
            self.table.setCellWidget(row, col, editor)

    def generate_baseline(self):
        if self.freeze_baseline_btn.isChecked():
            QMessageBox.warning(self, "Warning", "Baseline is frozen!")
            return

        model = self.model_combo.currentText()
        for row in range(self.table.rowCount()):
            input_widget = self.table.cellWidget(row, 0)
            if not input_widget or not input_widget.toPlainText():
                continue

            try:
                result = run_llm(input_widget.toPlainText(), model)
                baseline_widget = self.table.cellWidget(row, 1)
                baseline_widget.setPlainText(result)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to generate baseline: {str(e)}")

    def toggle_baseline_frozen(self, checked):
        if self.current_test_set:
            self.current_test_set.baseline_frozen = checked

    def save_test_set(self):
        name = self.test_set_name.text()
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a test set name")
            return

        cases = []
        for row in range(self.table.rowCount()):
            input_widget = self.table.cellWidget(row, 0)
            baseline_widget = self.table.cellWidget(row, 1)
            current_widget = self.table.cellWidget(row, 2)

            if input_widget and input_widget.toPlainText():
                case = TestCase(
                    input_text=input_widget.toPlainText(),
                    baseline_output=baseline_widget.toPlainText() if baseline_widget else None,
                    current_output=current_widget.toPlainText() if current_widget else None
                )
                cases.append(case)

        test_set = TestSet(
            name=name,
            cases=cases,
            baseline_model=self.model_combo.currentText(),
            baseline_frozen=self.freeze_baseline_btn.isChecked()
        )
        self.storage.save_test_set(test_set)
        self.current_test_set = test_set
        self.test_set_saved.emit(name)  # Emit signal when test set is saved

    def load_test_set(self):
        from PySide6.QtWidgets import QInputDialog
        test_sets = self.storage.get_all_test_sets()
        if not test_sets:
            QMessageBox.information(self, "Info", "No test sets found")
            return

        name, ok = QInputDialog.getItem(
            self, "Load Test Set", "Select test set:", test_sets, 0, False
        )
        if not ok:
            return

        test_set = self.storage.load_test_set(name)
        if not test_set:
            return

        self.current_test_set = test_set
        self.test_set_name.setText(test_set.name)
        self.model_combo.setCurrentText(test_set.baseline_model or "")
        self.freeze_baseline_btn.setChecked(test_set.baseline_frozen)

        self.table.setRowCount(0)
        for case in test_set.cases:
            row = self.table.rowCount()
            self.table.insertRow(row)

            input_editor = QTextEdit()
            input_editor.setPlainText(case.input_text)
            self.table.setCellWidget(row, 0, input_editor)

            baseline_editor = QTextEdit()
            if case.baseline_output:
                baseline_editor.setPlainText(case.baseline_output)
            self.table.setCellWidget(row, 1, baseline_editor)

            current_editor = QTextEdit()
            if case.current_output:
                current_editor.setPlainText(case.current_output)
            self.table.setCellWidget(row, 2, current_editor)
            
        self.test_set_loaded.emit(name)  # Emit signal when test set is loaded

    def run_current(self):
        if not self.current_test_set:
            QMessageBox.warning(self, "Warning", "Please save or load a test set first")
            return

        model = self.model_combo.currentText()
        for row in range(self.table.rowCount()):
            input_widget = self.table.cellWidget(row, 0)
            if not input_widget or not input_widget.toPlainText():
                continue

            try:
                result = run_llm(input_widget.toPlainText(), model)
                current_widget = self.table.cellWidget(row, 2)
                current_widget.setPlainText(result)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to generate current output: {str(e)}")