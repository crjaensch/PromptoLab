import os
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Add the project root directory to Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from main_window import MainWindow
from storage import FileStorage
from test_storage import TestSetStorage

# Define the base directory for prompts and test_sets
try:
    base_dir = Path.home() / ".promptolab"
    
    # Define paths for prompts and test_sets
    prompts_dir = base_dir / "prompts"
    test_sets_dir = base_dir / "test_sets"
    
    # Ensure directories exist
    for directory in (prompts_dir, test_sets_dir):
        directory.mkdir(parents=True, exist_ok=True)
        if not os.access(directory, os.W_OK):
            raise PermissionError(f"No write access to directory: {directory}")
except Exception as e:
    print(f"Error setting up directories: {e}", file=sys.stderr)
    sys.exit(1)

def setup_storage():    
    # Initialize storage systems with the correct paths
    prompt_storage = FileStorage(str(prompts_dir))
    test_set_storage = TestSetStorage(str(test_sets_dir))
    return prompt_storage, test_set_storage

def main():
    app = QApplication(sys.argv)
    prompt_storage, test_set_storage = setup_storage()
    window = MainWindow(prompt_storage, test_set_storage)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()