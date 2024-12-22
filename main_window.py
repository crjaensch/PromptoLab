import sys
from pathlib import Path
from PySide6.QtWidgets import QMainWindow, QTabWidget, QWidget, QVBoxLayout
from PySide6.QtCore import QSettings

# Add the project root directory to Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from prompts_catalog import PromptsCatalogWidget
from llm_playground import LLMPlaygroundWidget
from test_set_manager import TestSetManagerWidget
from evaluation_widget import EvaluationWidget
from storage import FileStorage

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PromptoLab")
        self.settings = QSettings("cjLabs", "PromptoLab")
        self.storage = FileStorage()
        self.setup_ui()
        
    def setup_ui(self):
        self.setMinimumSize(1200, 800)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tabs = QTabWidget()  # Make tabs accessible as instance variable
        
        # Create and add widgets to tabs
        self.prompts_catalog = PromptsCatalogWidget(self.storage, self.settings)
        self.llm_playground = LLMPlaygroundWidget(self.settings)
        self.test_set_manager = TestSetManagerWidget(self.settings)
        self.evaluation_widget = EvaluationWidget(self.settings)
        
        self.tabs.addTab(self.prompts_catalog, "Prompts Catalog")
        self.tabs.addTab(self.llm_playground, "LLM Playground")
        self.tabs.addTab(self.test_set_manager, "TestSet Manager")
        self.tabs.addTab(self.evaluation_widget, "Eval Playground")
        
        layout.addWidget(self.tabs)
        
        # Create status bar
        self.statusBar().showMessage("Ready")
        
        # Connect signals
        self.test_set_manager.test_set_updated.connect(self.evaluation_widget.update_test_set)
        self.prompts_catalog.prompt_selected_for_eval.connect(self.on_prompt_selected_for_eval)
        
    def closeEvent(self, event):
        """Save settings when closing the window."""
        self.settings.sync()
        event.accept()
        
    def on_prompt_selected_for_eval(self, current, previous):
        """Handle when a prompt is selected for evaluation."""
        if not current:
            return
            
        selected_title = current.text()
        selected_prompt = next((p for p in self.prompts_catalog._prompts if p.title == selected_title), None)
        
        if selected_prompt:
            # Update the LLM Playground with the selected prompt
            self.llm_playground.set_prompt(selected_prompt)

    def show_status(self, message, timeout=5000):
        """Show a message in the status bar with optional timeout in milliseconds."""
        self.statusBar().showMessage(message, timeout)

    def switch_to_prompts_catalog(self):
        """Switch to the Prompts Catalog tab"""
        prompts_catalog_index = self.tabs.indexOf(self.prompts_catalog)
        self.tabs.setCurrentIndex(prompts_catalog_index)