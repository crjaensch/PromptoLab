from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QLineEdit, QTextEdit, QComboBox,
                              QListWidget, QTabWidget, QLabel, QSplitter)
from PySide6.QtCore import Qt, Slot
from datetime import datetime
from .models import Prompt, PromptType
from .storage import FileStorage
from .llm_utils import run_llm
    
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.storage = FileStorage()
        self.setup_ui()
        self.current_prompt = None

    def setup_ui(self):
        self.setWindowTitle("Prompt Nanny")
        self.setMinimumSize(1200, 800)

        # Main layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        # Left panel (prompt list and search)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search prompts...")
        self.search_box.textChanged.connect(self.filter_prompts)
        left_layout.addWidget(self.search_box)

        # Prompt list
        self.prompt_list = QListWidget()
        self.prompt_list.currentItemChanged.connect(self.on_prompt_selected)
        left_layout.addWidget(self.prompt_list)

        # New prompt button
        new_prompt_btn = QPushButton("New Prompt")
        new_prompt_btn.clicked.connect(self.create_new_prompt)
        left_layout.addWidget(new_prompt_btn)

        # Right panel (tabs)
        right_panel = QTabWidget()
        
        # Editor tab
        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        
        # Title and type selection
        title_layout = QHBoxLayout()
        self.title_edit = QLineEdit()
        self.type_combo = QComboBox()
        for prompt_type in PromptType:
            self.type_combo.addItem(prompt_type.value)
        title_layout.addWidget(QLabel("Title:"))
        title_layout.addWidget(self.title_edit)
        title_layout.addWidget(QLabel("Type:"))
        title_layout.addWidget(self.type_combo)
        editor_layout.addLayout(title_layout)

        # Prompt content editor
        self.content_edit = QTextEdit()
        editor_layout.addWidget(self.content_edit)

        # Save button
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_prompt)
        editor_layout.addWidget(save_btn)

        right_panel.addTab(editor_widget, "Editor")

        # Playground tab
        playground_widget = QWidget()
        playground_layout = QVBoxLayout(playground_widget)
        
        # Model selection
        model_layout = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.addItems(["gpt-4o-mini", "gpt-4o", "o1-mini", "o1-preview", "claude-3.5-sonnet", "claude-3.5-haiku"])
        model_layout.addWidget(QLabel("Model:"))
        model_layout.addWidget(self.model_combo)
        playground_layout.addLayout(model_layout)

        # Input and output
        playground_splitter = QSplitter(Qt.Vertical)
        self.playground_input = QTextEdit()
        self.playground_output = QTextEdit()
        self.playground_output.setReadOnly(True)
        playground_splitter.addWidget(self.playground_input)
        playground_splitter.addWidget(self.playground_output)
        playground_layout.addWidget(playground_splitter)

        # Run button
        run_btn = QPushButton("Run")
        run_btn.clicked.connect(self.run_playground)
        playground_layout.addWidget(run_btn)

        right_panel.addTab(playground_widget, "Playground")

        # Add panels to main layout
        layout.addWidget(left_panel, 1)
        layout.addWidget(right_panel, 2)

        self.load_prompts()

    @Slot()
    def create_new_prompt(self):
        self.current_prompt = None
        self.title_edit.clear()
        self.content_edit.clear()
        self.type_combo.setCurrentIndex(0)

    @Slot()
    def save_prompt(self):
        prompt = Prompt(
            title=self.title_edit.text(),
            content=self.content_edit.toPlainText(),
            prompt_type=PromptType(self.type_combo.currentText()),
            created_at=datetime.now() if self.current_prompt is None else self.current_prompt.created_at,
            updated_at=datetime.now(),
            id=self.current_prompt.id if self.current_prompt else None
        )
        self.storage.save_prompt(prompt)
        self.load_prompts()

    def load_prompts(self):
        self.prompt_list.clear()
        self._prompts = self.storage.get_all_prompts()
        for prompt in self._prompts:
            self.prompt_list.addItem(prompt.title)

    @Slot()
    def on_prompt_selected(self, current, previous):
        if not current:
            return
        
        selected_title = current.text()
        selected_prompt = next((p for p in self._prompts if p.title == selected_title), None)
        
        if selected_prompt:
            self.current_prompt = selected_prompt
            self.title_edit.setText(selected_prompt.title)
            self.content_edit.setPlainText(selected_prompt.content)
            self.type_combo.setCurrentText(selected_prompt.prompt_type.value)
            self.playground_input.setPlainText(selected_prompt.content)


    @Slot()
    def filter_prompts(self):
        search_text = self.search_box.text().lower()
        for i in range(self.prompt_list.count()):
            item = self.prompt_list.item(i)
            item.setHidden(search_text not in item.text().lower())

    @Slot()
    def run_playground(self):
        if not self.current_prompt:
            return
        
        try:
            model = self.model_combo.currentText()
            prompt_text = self.playground_input.toPlainText()
            result = run_llm(prompt_text, model)
            self.playground_output.setMarkdown(result) # render markdown
        except Exception as e:
            self.playground_output.setPlainText(f"Error: {str(e)}")
