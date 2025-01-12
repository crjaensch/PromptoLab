import os
import sys
from pathlib import Path
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Add the project root directory to Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from main_window import MainWindow
from storage import FileStorage
from test_storage import TestSetStorage
from config import config  # Import the config module

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

# Configure logging
try:
    base_dir = Path.home() / ".promptolab"
    log_file = os.path.join(base_dir, "promptolab.log")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Create handlers with immediate flush
    file_handler = logging.FileHandler(log_file, mode='w')  # Open in write mode to start fresh
    file_handler.setLevel(logging.INFO)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Get root logger and configure it
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    logger = logging.getLogger(__name__)
    logger.info("Logging initialized successfully with file handler: %s", log_file)
except Exception as e:
    # Fallback to basic console logging if file logging setup fails
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        force=True  # Force reconfiguration of the root logger
    )
    logger = logging.getLogger(__name__)
    logger.error("Failed to initialize file logging: %s", str(e))
    logger.info("Falling back to console logging only")
    file_handler = None

# Custom PATH configuration because of macOS .app bundle limitations
def configure_path():
    # Get the directory of the current executable
    if getattr(sys, 'frozen', False):  # Check if app is running in a PyInstaller bundle
        app_dir = os.path.dirname(sys.executable)
        logger.info("Application directory (pyinstaller bundle): %s", app_dir)
    else:
        app_dir = os.getcwd()
        logger.info("Application directory (Python script): %s", app_dir)

    # Add the MacOS directory to PATH
    macos_path = os.path.join(app_dir)
    current_path = os.environ.get('PATH', '')
    updated_path = f"{macos_path}:{current_path}"
    logger.info("Updated PATH: %s", updated_path)
    os.environ['PATH'] = updated_path

# Call this function early in your app
configure_path()

def log_environment():
    """Log environment information for debugging purposes."""
    logger.info("=== Environment Information ===")
    logger.info(f"sys.executable: {sys.executable}")
    logger.info(f"sys._MEIPASS: {getattr(sys, '_MEIPASS', 'None')}")
    logger.info(f"sys.path: {sys.path}")
    logger.info(f"PATH environment variable: {os.environ.get('PATH', 'Not set')}")

def setup_storage():    
    # Initialize storage systems with the correct paths
    prompt_storage = FileStorage(str(prompts_dir))
    test_set_storage = TestSetStorage(str(test_sets_dir))
    
    # Log the current LLM API configuration
    logger.info(f"Using LLM API: {config.llm_api}")
    
    return prompt_storage, test_set_storage

def main():
    app = QApplication(sys.argv)
    prompt_storage, test_set_storage = setup_storage()
    window = MainWindow(prompt_storage, test_set_storage)
    window.show()
    
    # Log environment info before starting the event loop
    log_environment()
    
    # Run the application
    exit_code = app.exec()
    
    # Ensure all logs are written and cleanup
    if 'file_handler' in globals():
        # Force a flush of all handlers
        for handler in logging.getLogger().handlers:
            handler.flush()
        
        # Close and remove the file handler
        file_handler.close()
        logging.getLogger().removeHandler(file_handler)
        
        # Final flush of the root logger
        logging.shutdown()
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()