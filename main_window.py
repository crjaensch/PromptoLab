from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTabWidget
from PySide6.QtCore import QSettings, Slot
from .storage import FileStorage
from .prompts_catalog import PromptsCatalogWidget
from .llm_playground import LLMPlaygroundWidget
from .evaluation_widget import EvaluationWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.storage = FileStorage()
        self.settings = QSettings("Codeium", "PromptoLab")
        self.setup_ui()
        self.load_state()

    def setup_ui(self):
        self.setWindowTitle("PromptoLab")
        self.setMinimumSize(1200, 800)

        # Main layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # Tab widget at top left
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        main_layout.addWidget(self.tab_widget)
        
        # Create and add the Prompts Catalog tab
        self.prompts_catalog = PromptsCatalogWidget(self.storage, self.settings)
        self.tab_widget.addTab(self.prompts_catalog, "Prompts Catalog")

        # Create and add the LLM Playground tab
        self.llm_playground = LLMPlaygroundWidget(self.settings)
        self.tab_widget.addTab(self.llm_playground, "LLM Playground")

        # Create and add the Evaluation tab
        self.evaluation_widget = EvaluationWidget()
        self.tab_widget.addTab(self.evaluation_widget, "Eval Playground")

        # Connect signals
        self.prompts_catalog.prompt_selected_for_eval.connect(self.on_prompt_selected_for_eval)

    def save_state(self):
        self.prompts_catalog.save_state()
        self.llm_playground.save_state()

    def load_state(self):
        self.prompts_catalog.load_state()
        self.llm_playground.load_state()

    def closeEvent(self, event):
        self.save_state()
        super().closeEvent(event)

    @Slot()
    def on_prompt_selected_for_eval(self, current, previous):
        if not current:
            return
            
        selected_title = current.text()
        selected_prompt = next((p for p in self.prompts_catalog._prompts if p.title == selected_title), None)
        
        if selected_prompt:
            # Update the LLM Playground with the selected prompt
            self.llm_playground.set_prompt(selected_prompt)