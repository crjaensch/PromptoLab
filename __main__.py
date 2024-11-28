# prompt_nanny/__main__.py
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from .main_window import MainWindow
from .storage import FileStorage
from .test_storage import TestSetStorage

def setup_storage():
    # Ensure storage directories exist
    Path("prompts").mkdir(exist_ok=True)
    Path("test_sets").mkdir(exist_ok=True)
    
    # Initialize storage systems
    prompt_storage = FileStorage()
    test_storage = TestSetStorage()
    return prompt_storage, test_storage

def main():
    app = QApplication(sys.argv)
    prompt_storage, test_storage = setup_storage()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()