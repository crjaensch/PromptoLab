from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QLineEdit, QTextEdit, QComboBox,
                              QListWidget, QTabWidget, QLabel, QSplitter,
                              QFrame, QSizePolicy, QCheckBox, QListWidgetItem)
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
        self.toggle_btn.setIcon(QIcon("PromptoLab/icons/chevron-left.svg"))
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
                "PromptoLab/icons/chevron-left.svg"
                if self.expanded
                else "PromptoLab/icons/chevron-right.svg"
            )
        )
        self.content.setVisible(self.expanded)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.storage = FileStorage()
        self.settings = QSettings("Codeium", "PromptoLab")
        self._prompts = []
        self.current_prompt = None
        self.setup_ui()
        self.load_prompts()  # Load prompts before loading state
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
                border: 1px solid #CCCCCC; 
                padding: 6px; 
            }
            QLineEdit, QListWidget { 
                background: #F5F5F5;
                border: 1px solid #CCCCCC;
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
                padding: 8px;
                background: #F5F5F5;
                border: 1px solid #CCCCCC;            }
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
                background: #F5F5F5;
                border: 1px solid #CCCCCC;
            }
            QListWidget::item:hover { background: #BBBBBB; }
            QListWidget::item:selected { background: #BBBBBB; }
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

        # System prompt
        self.editor_system_prompt_visible = self.settings.value("editor_system_prompt_visible", False, bool)
        
        # Create horizontal layout for checkbox and label
        editor_system_prompt_header = QHBoxLayout()
        self.editor_system_prompt_checkbox = QCheckBox()
        self.editor_system_prompt_checkbox.setChecked(self.editor_system_prompt_visible)
        self.editor_system_prompt_checkbox.stateChanged.connect(self.toggle_editor_system_prompt)
        editor_system_prompt_label = QLabel("System Prompt:")
        editor_system_prompt_header.addWidget(self.editor_system_prompt_checkbox)
        editor_system_prompt_header.addWidget(editor_system_prompt_label)
        editor_system_prompt_header.addStretch()
        editor_layout.addLayout(editor_system_prompt_header)
        
        # System prompt editor (40% height)
        self.editor_system_prompt = QTextEdit()
        self.editor_system_prompt.setVisible(self.editor_system_prompt_visible)
        self.editor_system_prompt.setMinimumHeight(120)  # 40% of 300px total
        self.editor_system_prompt.setStyleSheet("""
            QTextEdit {
                padding: 16px;  
                background: #F5F5F5;
                border: 1px solid #CCCCCC;
            }
        """)
        self.editor_system_prompt.setPlaceholderText("Enter an optional system prompt...")
        editor_layout.addWidget(self.editor_system_prompt, 40)  # 40% stretch factor

        # User prompt content editor (60% height)
        self.editor_content_edit = QTextEdit()
        self.editor_content_edit.setMinimumHeight(180)  # 60% of 300px total
        self.editor_content_edit.setStyleSheet("""
            QTextEdit {
                padding: 16px;
                background: #F5F5F5;
                border: 1px solid #CCCCCC;
            }
        """)
        self.editor_content_edit.setPlaceholderText("Enter your prompt here...")
        editor_layout.addWidget(self.editor_content_edit, 60)  # 60% stretch factor

        # Save button
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_prompt)
        editor_layout.addWidget(save_btn)
        
        catalog_layout.addWidget(editor_widget)
        catalog_layout.setStretch(0, 0)
        catalog_layout.setStretch(1, 1)
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
        self.model_combo.addItems(["gpt-4o-mini", "gpt-4o-2024-11-20", "o1-mini", "o1-preview", "groq-llama3", "claude-3.5-sonnet"])
        model_layout.addWidget(QLabel("Model:"))
        model_layout.addWidget(self.model_combo)
        params_content_layout.addLayout(model_layout)
        
        self.params_panel.content_layout.addLayout(params_content_layout)
        playground_layout.addWidget(self.params_panel)

        # Main playground area
        playground_main = QWidget()
        playground_main_layout = QVBoxLayout(playground_main)
        
        # System prompt
        self.system_prompt_visible = self.settings.value("playground_system_prompt_visible", False, bool)
        
        # Create horizontal layout for checkbox and label
        system_prompt_header = QHBoxLayout()
        self.system_prompt_checkbox = QCheckBox()
        self.system_prompt_checkbox.setChecked(self.system_prompt_visible)
        self.system_prompt_checkbox.stateChanged.connect(self.toggle_playground_system_prompt)
        system_prompt_label = QLabel("System Prompt:")
        system_prompt_header.addWidget(self.system_prompt_checkbox)
        system_prompt_header.addWidget(system_prompt_label)
        system_prompt_header.addStretch()
        playground_main_layout.addLayout(system_prompt_header)
        
        self.system_prompt = QTextEdit()
        self.system_prompt.setVisible(self.system_prompt_visible)
        self.system_prompt.setStyleSheet("""
            QTextEdit {
                padding: 16px;
                min-height: 80px;
                background: #F5F5F5;
                border: 1px solid #CCCCCC;
            }
        """)
        self.system_prompt.setPlaceholderText("Enter an optional system prompt...")
        playground_main_layout.addWidget(self.system_prompt)

        # Create the user prompt
        self.user_prompt = QTextEdit()
        self.user_prompt.setStyleSheet("""
            QTextEdit {
                padding: 16px;
                min-height: 80px;
                background: #F5F5F5;
                border: 1px solid #CCCCCC;
            }
        """)
        self.user_prompt.setPlaceholderText("Enter your prompt here...")

        # Create a container for user prompt and run button
        input_container = QWidget()
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.addWidget(self.user_prompt)
        
        # Run button
        run_btn = QPushButton("Run")
        run_btn.clicked.connect(self.run_playground)
        input_layout.addWidget(run_btn)
        
        # Output area
        self.playground_output = QTextEdit()
        self.playground_output.setReadOnly(True)
        self.playground_output.setStyleSheet("""
            QTextEdit {
                padding: 16px;
                min-height: 100px;
                background: #F8F8F8;  /* Very light gray */
                border: 1px solid #CCCCCC;
                color: #2F4F4F;  /* Dark slate gray for text */
            }
        """)
        
        # Add widgets to splitter in desired order
        playground_splitter = QSplitter(Qt.Vertical)
        playground_splitter.addWidget(input_container)
        playground_splitter.addWidget(self.playground_output)
        playground_main_layout.addWidget(playground_splitter)

        playground_layout.addWidget(playground_main)
        playground_layout.setSpacing(16)  # Consistent spacing
        
        self.tab_widget.addTab(playground_widget, "LLM Playground")

        # Evaluation tab
        self.evaluation_widget = EvaluationWidget()
        self.tab_widget.addTab(self.evaluation_widget, "Eval Playground")

    def save_state(self):
        self.settings.setValue("left_panel_expanded", self.left_panel.expanded)
        self.settings.setValue("params_panel_expanded", self.params_panel.expanded)
        self.settings.setValue("editor_system_prompt_visible", self.editor_system_prompt_visible)
        self.settings.setValue("playground_system_prompt_visible", self.system_prompt_visible)
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
        self.editor_content_edit.clear()
        self.editor_system_prompt.clear()
        self.type_combo.setCurrentIndex(0)

    @Slot()
    def save_prompt(self):
        old_type = self.current_prompt.prompt_type if self.current_prompt else None
        
        prompt = Prompt(
            title=self.title_edit.text(),
            user_prompt=self.editor_content_edit.toPlainText(),
            system_prompt=self.editor_system_prompt.toPlainText() or None,  # Convert empty string to None
            prompt_type=PromptType(self.type_combo.currentText()),
            created_at=datetime.now() if self.current_prompt is None else self.current_prompt.created_at,
            updated_at=datetime.now(),
            id=self.current_prompt.id if self.current_prompt else ""
        )
        self.storage.save_prompt(prompt, old_type)
        self.load_prompts()

    def load_prompts(self):
        self.prompt_list.clear()
        self._prompts = self.storage.get_all_prompts()
        for i, prompt in enumerate(self._prompts):
            item = QListWidgetItem(prompt.title)
            item.setData(Qt.UserRole, i)  # Store the index in the _prompts list
            self.prompt_list.addItem(item)
            
        # Select the first prompt if available
        if self.prompt_list.count() > 0:
            self.prompt_list.setCurrentRow(0)  # This will trigger on_prompt_selected

    @Slot()
    def on_prompt_selected(self, current, previous):
        if current:
            index = current.data(Qt.UserRole)
            if index is not None and 0 <= index < len(self._prompts):
                selected_prompt = self._prompts[index]
                self.current_prompt = selected_prompt
                self.title_edit.setText(selected_prompt.title)
                self.editor_content_edit.setPlainText(selected_prompt.user_prompt)
                if selected_prompt.system_prompt:
                    self.editor_system_prompt.setPlainText(selected_prompt.system_prompt)
                    self.editor_system_prompt_checkbox.setChecked(True)
                    self.editor_system_prompt.setVisible(True)
                else:
                    self.editor_system_prompt.clear()
                    self.editor_system_prompt_checkbox.setChecked(False)
                    self.editor_system_prompt.setVisible(False)
                self.type_combo.setCurrentText(selected_prompt.prompt_type.value)
                self.user_prompt.setPlainText(selected_prompt.user_prompt)
                if selected_prompt.system_prompt:
                    self.system_prompt.setPlainText(selected_prompt.system_prompt)
                    self.system_prompt_checkbox.setChecked(True)
                    self.system_prompt.setVisible(True)
                else:
                    self.system_prompt.clear()
                    self.system_prompt_checkbox.setChecked(False)
                    self.system_prompt.setVisible(False)

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
            user_prompt_text = self.user_prompt.toPlainText()
            
            # Only get system prompt if the checkbox is checked and prompt is visible
            system_prompt_text = None
            if self.system_prompt_checkbox.isChecked() and self.system_prompt.isVisible():
                system_prompt_text = self.system_prompt.toPlainText()
                if not system_prompt_text.strip():  # If system prompt is empty after stripping whitespace
                    system_prompt_text = None
            
            if not user_prompt_text.strip():
                self.playground_output.setPlainText("Error: User prompt cannot be empty")
                return
                
            result = run_llm(user_prompt_text, system_prompt_text, model)
            self.playground_output.setMarkdown(result)  # render markdown
        except Exception as e:
            self.playground_output.setPlainText(f"Error: {str(e)}")

    @Slot()
    def toggle_editor_system_prompt(self):
        self.editor_system_prompt_visible = self.editor_system_prompt_checkbox.isChecked()
        self.editor_system_prompt.setVisible(self.editor_system_prompt_visible)

    @Slot()
    def toggle_playground_system_prompt(self):
        self.system_prompt_visible = self.system_prompt_checkbox.isChecked()
        self.system_prompt.setVisible(self.system_prompt_visible)
