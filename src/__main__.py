import os
import sys
from pathlib import Path
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.main_window import MainWindow
from src.storage.storage import FileStorage
from src.storage.test_storage import TestSetStorage
from src.config import config  # Import the config module

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

def setup_logging():
    """Initialize logging with the configured level and both file and console handlers."""
    try:
        # Get the configured logging level
        level_map = {"Info": logging.INFO, "Warning": logging.WARNING, "Error": logging.ERROR}
        configured_level = level_map[config.log_level]
        
        # Set up log file
        log_file = os.path.join(base_dir, "promptolab.log")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(configured_level)
        
        # Remove any existing handlers to avoid duplicates
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Create and configure handlers
        file_handler = logging.FileHandler(log_file, mode='w')
        file_handler.setLevel(configured_level)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(configured_level)
        
        # Create and set formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers to root logger
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        logger = logging.getLogger(__name__)
        logger.info("Logging initialized successfully with file handler: %s", log_file)
        logger.info("Logging level set to: %s", config.log_level)
        
    except Exception as e:
        # Fallback to basic console logging if file logging setup fails
        logging.basicConfig(
            level=configured_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            force=True
        )
        logger = logging.getLogger(__name__)
        logger.error("Failed to initialize file logging: %s", str(e))
        logger.info("Falling back to console logging only")

# Custom PATH configuration because of macOS .app bundle limitations
def configure_path():
    logger = logging.getLogger(__name__)
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

def log_environment():
    """Log environment information for debugging purposes."""
    logger = logging.getLogger(__name__)
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
    logger = logging.getLogger(__name__)
    logger.info(f"Using LLM API: {config.llm_api}")
    
    return prompt_storage, test_set_storage

def main():
    """Main entry point of the application."""
    setup_logging()  # Initialize logging first
    configure_path()  # Now configure_path will use the correct logging level
    
    app = QApplication(sys.argv)
    prompt_storage, test_set_storage = setup_storage()
    window = MainWindow(prompt_storage, test_set_storage)
    window.show()
    
    # Log environment info before starting the event loop
    log_environment()
    
    # Connect cleanup handlers
    app.aboutToQuit.connect(window.cleanup)
    
    # Run the application
    exit_code = app.exec()
    
    # Force cleanup before exiting
    window.cleanup()
    
    # Ensure all logs are written and cleanup
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.flush()
        
    # Close and remove the file handler
    for handler in root_logger.handlers:
        if isinstance(handler, logging.FileHandler):
            handler.close()
            root_logger.removeHandler(handler)
            
    # Final flush of the root logger
    logging.shutdown()
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()