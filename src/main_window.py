import sys
from pathlib import Path
from PySide6.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout,
                              QMenuBar, QMenu)
from PySide6.QtCore import QSettings, Slot
import logging

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.modules.prompt_catalog.prompts_catalog import PromptsCatalogWidget
from src.modules.llm_playground.llm_playground import LLMPlaygroundWidget
from src.modules.test_set_manager.test_set_manager import TestSetManagerWidget
from src.modules.eval_playground.evaluation_widget import EvaluationWidget
from src.storage.storage import FileStorage
from src.storage.test_storage import TestSetStorage
from src.utils.settings_dialog import SettingsDialog

class MainWindow(QMainWindow):
    def __init__(self, prompt_storage: FileStorage, test_set_storage: TestSetStorage):
        super().__init__()
        self.setWindowTitle("PromptoLab")
        self.settings = QSettings("cjLabs", "PromptoLab")
        self.prompt_storage = prompt_storage
        self.test_set_storage = test_set_storage
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
        self.prompts_catalog = PromptsCatalogWidget(self.prompt_storage, self.settings)
        self.llm_playground = LLMPlaygroundWidget(self.settings)
        self.test_set_manager = TestSetManagerWidget(self.test_set_storage, self.settings)
        self.evaluation_widget = EvaluationWidget(self.test_set_storage, self.settings)
        
        self.tabs.addTab(self.prompts_catalog, "📚 Prompt Catalog")
        self.tabs.addTab(self.llm_playground, "🧪 LLM Playground")
        self.tabs.addTab(self.test_set_manager, "📋 Test Sets")
        self.tabs.addTab(self.evaluation_widget, "📊 Test Evaluation")
        
        layout.addWidget(self.tabs)
        
        # Create status bar
        self.statusBar().showMessage("Ready")
        
        # Connect signals
        self.test_set_manager.test_set_updated.connect(self.evaluation_widget.update_test_set)
        self.prompts_catalog.prompt_selected_for_eval.connect(self.on_prompt_selected_for_eval)
        self.evaluation_widget.status_changed.connect(self.show_status)
        
        # Load initial data after signals are connected
        self.prompts_catalog.load_prompts()
        
        self.setup_menu()
        
    def setup_menu(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        file_menu.addAction("Exit", self.close)
        
        # Settings menu
        settings_menu = menubar.addMenu("Settings")
        settings_menu.addAction("Configure...", self.show_settings_dialog)
        
    @Slot()
    def show_settings_dialog(self):
        dialog = SettingsDialog(self)
        # Connect the api_changed signal to both widgets
        dialog.api_changed.connect(self.llm_playground.update_models)
        dialog.api_changed.connect(self.evaluation_widget.update_models)
        dialog.exec()

    def cleanup(self):
        """Clean up all widgets with threads before application exit."""
        logging.debug("Starting MainWindow cleanup...")
        
        # Clean up evaluation widget
        if hasattr(self, 'evaluation_widget'):
            logging.debug("Cleaning up evaluation widget...")
            try:
                self.evaluation_widget.cleanup_threads()
            except Exception as e:
                logging.error(f"Error cleaning up evaluation widget: {e}")
            
        # Clean up playground widget
        if hasattr(self, 'llm_playground'):
            logging.debug("Cleaning up playground widget...")
            try:
                self.llm_playground.cleanup_threads()
            except Exception as e:
                logging.error(f"Error cleaning up playground widget: {e}")
            
        logging.debug("MainWindow cleanup completed.")

    def closeEvent(self, event):
        """Save settings when closing the window."""
        self.settings.sync()
        try:
            self.cleanup()
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
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