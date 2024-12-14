from pathlib import Path
import sys
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLineEdit, QTextEdit, QComboBox, QListWidget,
                              QLabel, QFrame, QListWidgetItem, QCheckBox,
                              QMenu, QMessageBox, QSplitter)
from PySide6.QtCore import Qt, Signal, Slot
from datetime import datetime

# Add the project root directory to Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from models import Prompt, PromptType
from collapsible_panel import CollapsiblePanel
from expandable_text import ExpandableTextWidget

class PromptsCatalogWidget(QWidget):
    prompt_selected_for_eval = Signal(QListWidgetItem, QListWidgetItem)

    def __init__(self, storage, settings, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.settings = settings
        self._prompts = []
        self.current_prompt = None
        self.system_prompt_visible = self.settings.value("system_prompt_visible", False, bool)
        self.setup_ui()
        self.load_prompts()

    def setup_ui(self):
        catalog_layout = QHBoxLayout(self)
        
        # Right panel (editor)
        editor_frame = QWidget()
        editor_layout = QVBoxLayout(editor_frame)
        
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

        # System prompt header
        system_prompt_header = QHBoxLayout()
        self.system_prompt_checkbox = QCheckBox()
        self.system_prompt_checkbox.setChecked(self.system_prompt_visible)
        self.system_prompt_checkbox.stateChanged.connect(self.toggle_system_prompt)
        system_prompt_label = QLabel("System Prompt:")
        system_prompt_header.addWidget(self.system_prompt_checkbox)
        system_prompt_header.addWidget(system_prompt_label)
        system_prompt_header.addStretch()
        editor_layout.addLayout(system_prompt_header)
        
        # Create vertical splitter for system and user prompts
        editor_splitter = QSplitter(Qt.Vertical)
        
        # System prompt editor
        self.system_prompt = ExpandableTextWidget()
        self.system_prompt.setVisible(self.system_prompt_visible)
        self.system_prompt.setMinimumHeight(120)  # Initial height
        self.system_prompt.setStyleSheet("""
            QTextEdit {
                padding: 16px;  
                background: #F5F5F5;
                border: 1px solid #CCCCCC;
            }
        """)
        self.system_prompt.setPlaceholderText("Enter an optional system prompt...")
        
        # User prompt editor
        self.user_prompt = QTextEdit()
        self.user_prompt.setMinimumHeight(180)
        self.user_prompt.setStyleSheet("""
            QTextEdit {
                padding: 16px;  
                background: #F5F5F5;
                border: 1px solid #CCCCCC;
            }
        """)
        self.user_prompt.setPlaceholderText("Enter your prompt here...")
        
        # Add editors to splitter
        editor_splitter.addWidget(self.system_prompt)
        editor_splitter.addWidget(self.user_prompt)
        
        # Set initial sizes (40% system, 60% user)
        editor_splitter.setSizes([400, 600])
        
        # Store original heights for restoration
        self.original_heights = {
            'system_prompt': self.system_prompt.minimumHeight(),
            'user_prompt': self.user_prompt.minimumHeight()
        }
        
        # Connect expandable widget signals
        self.system_prompt.expandedChanged.connect(lambda expanded: self.toggle_compact_mode(expanded) if self.system_prompt.isVisible() else None)
        self.system_prompt.sizeChanged.connect(lambda: editor_splitter.setSizes(
            [1800, 200] if self.system_prompt.is_expanded and self.system_prompt.isVisible() else [400, 600]
        ))
        
        editor_layout.addWidget(editor_splitter)
        
        # Save button
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_prompt)
        editor_layout.addWidget(save_btn)
        
        # Add editor frame to main layout first (on the left)
        catalog_layout.addWidget(editor_frame)
        
        # Prompts panel as collapsible (on the right)
        self.prompts_panel = CollapsiblePanel("Prompts")
        
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
                border: 1px solid #CCCCCC;
            }
        """)
        self.search_box.textChanged.connect(self.filter_prompts)
        search_list_layout.addWidget(self.search_box)

        # Prompt list with label
        prompts_label = QLabel("All Prompts:")
        search_list_layout.addWidget(prompts_label)
        
        self.prompt_list = QListWidget()
        self.prompt_list.currentItemChanged.connect(self.on_prompt_selected)
        self.prompt_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.prompt_list.customContextMenuRequested.connect(self.show_context_menu)
        self.prompt_list.setStyleSheet("""
            QListWidget {
                background: #F5F5F5;
                border: 1px solid #CCCCCC;
            }
            QListWidget::item:hover { background: #BBBBBB; }
            QListWidget::item:selected { background: #BBBBBB; }
        """)
        search_list_layout.addWidget(self.prompt_list)
        
        self.prompts_panel.content_layout.addWidget(search_list_frame)

        # New prompt button
        new_prompt_btn = QPushButton("New Prompt")
        new_prompt_btn.clicked.connect(self.create_new_prompt)
        self.prompts_panel.content_layout.addWidget(new_prompt_btn)
        
        # Add prompts panel to main layout last (on the right)
        catalog_layout.addWidget(self.prompts_panel)
        catalog_layout.setStretch(0, 1)
        catalog_layout.setStretch(1, 0)
        catalog_layout.setSpacing(16)  # Consistent spacing

    def save_state(self):
        self.settings.setValue("prompts_panel_expanded", self.prompts_panel.expanded)
        self.settings.setValue("system_prompt_visible", self.system_prompt_visible)

    def load_state(self):
        prompts_expanded = self.settings.value("prompts_panel_expanded", True, bool)
        if not prompts_expanded:
            self.prompts_panel.toggle_panel()

    @Slot()
    def create_new_prompt(self):
        self.current_prompt = None
        self.title_edit.clear()
        self.user_prompt.clear()
        self.system_prompt.clear()
        self.type_combo.setCurrentIndex(0)

    @Slot()
    def save_prompt(self):
        old_type = self.current_prompt.prompt_type if self.current_prompt else None
        
        prompt = Prompt(
            title=self.title_edit.text(),
            user_prompt=self.user_prompt.toPlainText(),
            system_prompt=self.system_prompt.toPlainText() or None,  # Convert empty string to None
            prompt_type=PromptType(self.type_combo.currentText()),
            created_at=datetime.now() if self.current_prompt is None else self.current_prompt.created_at,
            updated_at=datetime.now(),
            id=self.current_prompt.id if self.current_prompt else ""
        )
        self.storage.save_prompt(prompt, old_type)
        self.load_prompts()

    def load_prompts(self):
        # Store the current prompt's title before clearing
        current_title = self.current_prompt.title if self.current_prompt else None
        
        self.prompt_list.clear()
        self._prompts = self.storage.get_all_prompts()
        
        selected_index = 0  # Default to first item
        for i, prompt in enumerate(self._prompts):
            item = QListWidgetItem(prompt.title)
            item.setData(Qt.UserRole, i)  # Store the index in the _prompts list
            self.prompt_list.addItem(item)
            
            # If this is the previously selected prompt, store its index
            if current_title and prompt.title == current_title:
                selected_index = i
        
        # Select the appropriate prompt
        if self.prompt_list.count() > 0:
            self.prompt_list.setCurrentRow(selected_index)  # This will trigger on_prompt_selected

    @Slot()
    def on_prompt_selected(self, current, previous):
        if current:
            index = current.data(Qt.UserRole)
            if index is not None and 0 <= index < len(self._prompts):
                selected_prompt = self._prompts[index]
                self.current_prompt = selected_prompt
                self.title_edit.setText(selected_prompt.title)
                self.user_prompt.setPlainText(selected_prompt.user_prompt)
                if selected_prompt.system_prompt:
                    self.system_prompt.setPlainText(selected_prompt.system_prompt)
                    self.system_prompt_checkbox.setChecked(True)
                    self.system_prompt.setVisible(True)
                else:
                    self.system_prompt.clear()
                    self.system_prompt_checkbox.setChecked(False)
                    self.system_prompt.setVisible(False)
                self.type_combo.setCurrentText(selected_prompt.prompt_type.value)
                # Emit signal when a prompt is selected
                self.prompt_selected_for_eval.emit(current, previous)

    @Slot()
    def filter_prompts(self):
        search_text = self.search_box.text().lower()
        for i in range(self.prompt_list.count()):
            item = self.prompt_list.item(i)
            item.setHidden(search_text not in item.text().lower())

    @Slot()
    def toggle_system_prompt(self):
        """Toggle system prompt visibility and adjust UI accordingly."""
        self.system_prompt_visible = self.system_prompt_checkbox.isChecked()
        self.system_prompt.setVisible(self.system_prompt_visible)
        
        # Reset compact mode when hiding system prompt
        if not self.system_prompt_visible and self.system_prompt.is_expanded:
            self.toggle_compact_mode(False)

    @Slot()
    def toggle_compact_mode(self, expanded):
        """Toggle between compact and normal mode for the user prompt"""
        if expanded:
            # Compact mode for user prompt
            self.user_prompt.setMinimumHeight(40)
            self.user_prompt.setMaximumHeight(60)
            
            # Update placeholder for better visibility in compact mode
            if self.user_prompt.toPlainText():
                self.user_prompt.setPlaceholderText("User: " + self.user_prompt.toPlainText()[:50] + "...")
        else:
            # Normal mode
            self.user_prompt.setMinimumHeight(self.original_heights['user_prompt'])
            self.user_prompt.setMaximumHeight(16777215)  # Qt's QWIDGETSIZE_MAX
            self.user_prompt.setPlaceholderText("Enter your prompt here...")

    @Slot()
    def show_context_menu(self, position):
        item = self.prompt_list.itemAt(position)
        if not item:
            return
            
        menu = QMenu()
        delete_action = menu.addAction("Delete")
        action = menu.exec_(self.prompt_list.viewport().mapToGlobal(position))
        
        if action == delete_action:
            self.delete_prompt(item)
            
    def delete_prompt(self, item):
        index = item.data(Qt.UserRole)
        if index is None or index >= len(self._prompts):
            return
            
        prompt = self._prompts[index]
        reply = QMessageBox.question(
            self,
            "Delete Prompt",
            f"Are you sure you want to delete the prompt '{prompt.title}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.storage.delete_prompt(prompt.id, prompt.prompt_type)
            self.load_prompts()
            # Clear editor if the deleted prompt was selected
            if self.current_prompt and self.current_prompt.id == prompt.id:
                self.create_new_prompt()