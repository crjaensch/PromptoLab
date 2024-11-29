from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QLineEdit, QTextEdit, QComboBox,
                              QListWidget, QTabWidget, QLabel, QSplitter,
                              QFrame, QSizePolicy)
from PySide6.QtCore import Qt, Slot, QSettings, QPropertyAnimation, QSize
from PySide6.QtGui import QIcon
from datetime import datetime
from .models import Prompt, PromptType
from .storage import FileStorage
from .llm_utils import run_llm
from .evaluation_widget import EvaluationWidget

class CollapsiblePanel(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.expanded = True
        self.animation = QPropertyAnimation(self, b"minimumWidth")
        self.animation.setDuration(200)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)  # Remove spacing between toggle button and content
        
        # Top container for the toggle button
        toggle_container = QWidget()
        toggle_container.setFixedHeight(48)  # Match button height
        toggle_layout = QHBoxLayout(toggle_container)
        toggle_layout.setContentsMargins(0, 0, 0, 0)
        toggle_layout.setAlignment(Qt.AlignRight | Qt.AlignTop)  # Align to top-right
        
        # Toggle button with chevron
        self.toggle_btn = QPushButton()
        self.toggle_btn.setIcon(QIcon("PromptNanny/icons/chevron-left.svg"))
        self.toggle_btn.clicked.connect(self.toggle_panel)
        self.toggle_btn.setFixedSize(48, 48)
        toggle_layout.addWidget(self.toggle_btn)
        
        # Add toggle container to main layout
        layout.addWidget(toggle_container)
        
        # Content widget
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        layout.addWidget(self.content)

    def toggle_panel(self):
        self.expanded = not self.expanded
        target_width = self.sizeHint().width() if self.expanded else 48
        self.animation.setStartValue(self.width())
        self.animation.setEndValue(target_width)
        self.animation.start()
        
        self.toggle_btn.setIcon(
            QIcon(
                "PromptNanny/icons/chevron-left.svg"
                if self.expanded
                else "PromptNanny/icons/chevron-right.svg"
            )
        )
        self.content.setVisible(self.expanded)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.storage = FileStorage()
        self.settings = QSettings("Codeium", "PromptNanny")
        self._prompts = []
        self.current_prompt = None
        self.setup_ui()
        self.load_prompts()  # Load prompts before loading state
        self.load_state()

    def setup_ui(self):
        self.setWindowTitle("Prompt Nanny")
        self.setMinimumSize(1200, 800)

        # Main layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # Tab widget at top left
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.West)
        main_layout.addWidget(self.tab_widget)
        
        # Prompts Catalog Tab
        catalog_widget = QWidget()
        catalog_layout = QHBoxLayout(catalog_widget)
        
        # Left panel as collapsible
        self.left_panel = CollapsiblePanel("Prompts")
        
        # Create a frame for search and list controls
        search_list_frame = QFrame()
        search_list_frame.setFrameStyle(QFrame.StyledPanel)
        search_list_frame.setStyleSheet("""
            QFrame { 
                border: 1px solid white; 
                padding: 12px; 
            }
            QLineEdit, QListWidget { 
                border: 1px solid white;
                background: transparent;
            }
            QLabel { 
                border: none;
                background: transparent;
            }
        """)
        search_list_layout = QVBoxLayout(search_list_frame)
        search_list_layout.setSpacing(12)
        
        # Search box with label
        search_label = QLabel("Search:")
        search_list_layout.addWidget(search_label)
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search prompts...")
        self.search_box.setStyleSheet("""
            QLineEdit {
                border: 1px solid white;
                padding: 8px;
                background: transparent;
            }
        """)
        self.search_box.textChanged.connect(self.filter_prompts)
        search_list_layout.addWidget(self.search_box)

        # Prompt list with label
        prompts_label = QLabel("All Prompts:")
        search_list_layout.addWidget(prompts_label)
        
        self.prompt_list = QListWidget()
        self.prompt_list.currentItemChanged.connect(self.on_prompt_selected)
        self.prompt_list.setStyleSheet("""
            QListWidget {
                border: 1px solid white;
                background: transparent;
            }
            QListWidget::item:hover { background: #4169E1; }
            QListWidget::item:selected { background: #4169E1; }
        """)
        search_list_layout.addWidget(self.prompt_list)
        
        self.left_panel.content_layout.addWidget(search_list_frame)

        # New prompt button
        new_prompt_btn = QPushButton("New Prompt")
        new_prompt_btn.clicked.connect(self.create_new_prompt)
        self.left_panel.content_layout.addWidget(new_prompt_btn)
        
        catalog_layout.addWidget(self.left_panel)

        # Right panel (editor)
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

        # Prompt content editor with styling
        self.content_edit = QTextEdit()
        self.content_edit.setStyleSheet("""
            QTextEdit {
                padding: 16px;
                min-height: 100px;
                border: 1px solid #E5E7EB;
            }
        """)
        editor_layout.addWidget(self.content_edit)

        # Save button
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_prompt)
        editor_layout.addWidget(save_btn)
        
        catalog_layout.addWidget(editor_widget)
        catalog_layout.setSpacing(16)  # Consistent spacing
        
        self.tab_widget.addTab(catalog_widget, "Prompts Catalog")

        # LLM Playground tab
        playground_widget = QWidget()
        playground_layout = QHBoxLayout(playground_widget)
        
        # Parameters panel as collapsible
        self.params_panel = CollapsiblePanel("Parameters")
        params_content_layout = QVBoxLayout()
        
        # Model selection
        model_layout = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.addItems(["gpt-4o-mini", "gpt-4o", "o1-mini", "o1-preview", "claude-3.5-sonnet", "claude-3.5-haiku"])
        model_layout.addWidget(QLabel("Model:"))
        model_layout.addWidget(self.model_combo)
        params_content_layout.addLayout(model_layout)
        
        self.params_panel.content_layout.addLayout(params_content_layout)
        playground_layout.addWidget(self.params_panel)

        # Main playground area
        playground_main = QWidget()
        playground_main_layout = QVBoxLayout(playground_main)
        
        # System prompt
        self.system_prompt_visible = self.settings.value("system_prompt_visible", True, bool)
        self.system_prompt = QTextEdit()
        self.system_prompt.setVisible(self.system_prompt_visible)
        self.system_prompt.setStyleSheet("""
            QTextEdit {
                padding: 16px;
                min-height: 100px;
                border: 1px solid #E5E7EB;
            }
        """)
        playground_main_layout.addWidget(self.system_prompt)

        # Input and output
        playground_splitter = QSplitter(Qt.Vertical)
        self.playground_input = QTextEdit()
        self.playground_output = QTextEdit()
        self.playground_output.setReadOnly(True)
        
        # Apply consistent styling
        for editor in [self.playground_input, self.playground_output]:
            editor.setStyleSheet("""
                QTextEdit {
                    padding: 16px;
                    min-height: 100px;
                    border: 1px solid #E5E7EB;
                }
            """)
        
        playground_splitter.addWidget(self.playground_input)
        playground_splitter.addWidget(self.playground_output)
        playground_main_layout.addWidget(playground_splitter)

        # Run button
        run_btn = QPushButton("Run")
        run_btn.clicked.connect(self.run_playground)
        playground_main_layout.addWidget(run_btn)
        
        playground_layout.addWidget(playground_main)
        playground_layout.setSpacing(16)  # Consistent spacing
        
        self.tab_widget.addTab(playground_widget, "LLM Playground")

        # Evaluation tab
        self.evaluation_widget = EvaluationWidget()
        self.tab_widget.addTab(self.evaluation_widget, "Eval Playground")

    def save_state(self):
        self.settings.setValue("left_panel_expanded", self.left_panel.expanded)
        self.settings.setValue("params_panel_expanded", self.params_panel.expanded)
        self.settings.setValue("system_prompt_visible", self.system_prompt_visible)
        self.settings.setValue("selected_model", self.model_combo.currentText())
        self.settings.setValue("system_prompt_text", self.system_prompt.toPlainText())
        
    def load_state(self):
        # Restore panel states
        left_expanded = self.settings.value("left_panel_expanded", True, bool)
        params_expanded = self.settings.value("params_panel_expanded", True, bool)
        
        if not left_expanded:
            self.left_panel.toggle_panel()
        if not params_expanded:
            self.params_panel.toggle_panel()
            
        # Restore LLM settings
        model = self.settings.value("selected_model", "gpt-4o")
        self.model_combo.setCurrentText(model)
        
        system_prompt = self.settings.value("system_prompt_text", "")
        self.system_prompt.setPlainText(system_prompt)
        
    def closeEvent(self, event):
        self.save_state()
        super().closeEvent(event)

    @Slot()
    def on_prompt_selected_for_eval(self, current, previous):
        if not current or not self.evaluation_widget:
            return
            
        selected_title = current.text()
        selected_prompt = next((p for p in self._prompts if p.title == selected_title), None)
        
        if selected_prompt:
            self.evaluation_widget.set_current_prompt(selected_prompt)

    @Slot()
    def on_test_set_saved(self, test_set_name):
        self.statusBar().showMessage(f"Test set '{test_set_name}' saved", 3000)

    @Slot()
    def on_test_set_loaded(self, test_set_name):
        self.statusBar().showMessage(f"Test set '{test_set_name}' loaded", 3000)

    @Slot()
    def create_new_prompt(self):
        self.current_prompt = None
        self.title_edit.clear()
        self.content_edit.clear()
        self.type_combo.setCurrentIndex(0)

    @Slot()
    def save_prompt(self):
        # Get the old type if this is an existing prompt
        old_type = self.current_prompt.prompt_type if self.current_prompt else None
        
        prompt = Prompt(
            title=self.title_edit.text(),
            content=self.content_edit.toPlainText(),
            prompt_type=PromptType(self.type_combo.currentText()),
            created_at=datetime.now() if self.current_prompt is None else self.current_prompt.created_at,
            updated_at=datetime.now(),
            id=self.current_prompt.id if self.current_prompt else None
        )
        self.storage.save_prompt(prompt, old_type)
        self.load_prompts()

    def load_prompts(self):
        self.prompt_list.clear()
        self._prompts = self.storage.get_all_prompts()
        for prompt in self._prompts:
            self.prompt_list.addItem(prompt.title)
            
        # Select the first prompt if available
        if self.prompt_list.count() > 0:
            self.prompt_list.setCurrentRow(0)  # This will trigger on_prompt_selected

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
