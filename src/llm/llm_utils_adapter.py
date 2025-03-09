# QtModelWorkers.py
import sys
import traceback
import json
import logging
from PySide6.QtCore import Signal, Slot, QObject, Qt, QRunnable
from pathlib import Path
from typing import Optional, Dict, Any

logging.debug('llm_utils_adapter module imported.')

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.llm import llm_utils_litellm
from src.llm import llm_utils_llmcmd
from src.config import config
from src.utils.thread_manager import BaseRunnable, ThreadManager

# Legacy QObject-based worker for backward compatibility
class LLMWorker(QObject):
    """Worker that runs llm_utils_xxx.run_llm depending on the configured LLM API."""
    finished = Signal(str)
    error = Signal(str)
    cancelled = Signal()
    
    def __init__(self, model_name: str, user_prompt: str, system_prompt: Optional[str] = None, model_params: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.model_name = model_name
        self.user_prompt = user_prompt
        self.system_prompt = system_prompt
        self.model_params = model_params or {}
        self._runnable = None

    @staticmethod
    def get_models() -> list[str]:
        """Return a list of available models for the configured LLM API.
        
        Returns:
            A list of model names supported by the configured API.
        """
        if config.llm_api == "llm-cmd":
            return llm_utils_llmcmd.get_models()
        elif config.llm_api == "litellm":
            return llm_utils_litellm.get_models()
        else:
            raise ValueError(f"Unsupported LLM API: {config.llm_api}")

    @Slot()
    def run(self):
        """Start the LLM task in a thread pool."""
        # Create a runnable and submit it to the thread pool
        self._runnable = LLMRunnable(
            model_name=self.model_name,
            user_prompt=self.user_prompt,
            system_prompt=self.system_prompt,
            model_params=self.model_params
        )
        
        # Connect signals
        self._runnable.signals.finished.connect(self.finished.emit)
        self._runnable.signals.error.connect(self.error.emit)
        self._runnable.signals.cancelled.connect(self.cancelled.emit)
        
        # Start the runnable in the thread pool
        ThreadManager.instance().start_runnable(self._runnable)

    def cancel(self):
        """Request cancellation of the running task."""
        if self._runnable:
            self._runnable.cancel()

# QRunnable implementation for LLM tasks
class LLMRunnable(BaseRunnable):
    """Runnable that executes LLM requests in a thread pool."""
    
    def __init__(self, model_name: str, user_prompt: str, system_prompt: Optional[str] = None, model_params: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.model_name = model_name
        self.user_prompt = user_prompt
        self.system_prompt = system_prompt
        self.model_params = model_params or {}
    
    def run(self):
        """Executed in the worker thread."""
        try:
            # Check if cancelled before starting
            if self.is_cancelled():
                self.signals.cancelled.emit()
                return
                
            # Run the LLM request
            if config.llm_api == 'llm-cmd':
                result = llm_utils_llmcmd.run_llm(
                    self.model_name,
                    self.user_prompt,
                    self.system_prompt,
                    self.model_params
                )
            else:
                result = llm_utils_litellm.run_llm(
                    self.model_name,
                    self.user_prompt,
                    self.system_prompt,
                    self.model_params
                )
                
            # Check if cancelled before emitting result
            if self.is_cancelled():
                self.signals.cancelled.emit()
                return
                
            self.signals.finished.emit(result)

        except (llm_utils_llmcmd.LLMQuotaError,
                llm_utils_llmcmd.LLMCapabilityError,
                llm_utils_llmcmd.LLMConnectionError) as e:
            # Pass through the user-friendly error messages
            if not self.is_cancelled():
                self.signals.error.emit(str(e))

        except Exception as e:
            if not self.is_cancelled():
                tb_str = traceback.format_exc()
                self.signals.error.emit(f"{e}\n{tb_str}")

# QRunnable implementation for embedding tasks
class EmbedRunnable(BaseRunnable):
    """Runnable that executes embedding requests in a thread pool."""
    
    def __init__(self, text: str, llm_cmd_embed_model: str = "3-large", litellm_embed_model: str = "text-embedding-3-large"):
        super().__init__()
        self.text = text
        self.llm_cmd_embed_model = llm_cmd_embed_model
        self.litellm_embed_model = litellm_embed_model
    
    def run(self):
        """Executed in the worker thread."""
        try:
            # Check if cancelled before starting
            if self.is_cancelled():
                self.signals.cancelled.emit()
                return
                
            # Run the embed model request
            if config.llm_api == 'llm-cmd':
                result = llm_utils_llmcmd.run_embed(self.llm_cmd_embed_model, self.text)
            else:
                result = llm_utils_litellm.run_embed(self.litellm_embed_model, self.text)
                
            # Check if cancelled before emitting result
            if self.is_cancelled():
                self.signals.cancelled.emit()
                return
                
            # Convert List[float] to JSON string before emitting
            json_result = json.dumps(result)
            self.signals.finished.emit(json_result)

        except (llm_utils_llmcmd.LLMQuotaError,
                llm_utils_llmcmd.LLMCapabilityError,
                llm_utils_llmcmd.LLMConnectionError) as e:
            # Pass through the user-friendly error messages
            if not self.is_cancelled():
                self.signals.error.emit(str(e))

        except Exception as e:
            if not self.is_cancelled():
                tb_str = traceback.format_exc()
                self.signals.error.emit(f"{e}\n{tb_str}")

# Legacy QObject-based worker for backward compatibility
class EmbedWorker(QObject):
    """Worker that runs llm_utils_xxx.run_embed depending on the configured LLM API."""
    finished = Signal(str)
    error = Signal(str)
    cancelled = Signal()
    
    def __init__(self, text: str):
        super().__init__()
        self.llm_cmd_embed_model = "3-large"
        self.litellm_embed_model = "text-embedding-3-large"
        self.text = text
        self._runnable = None
        
    @Slot()
    def run(self):
        """Start the embedding task in a thread pool."""
        # Create a runnable and submit it to the thread pool
        self._runnable = EmbedRunnable(
            text=self.text,
            llm_cmd_embed_model=self.llm_cmd_embed_model,
            litellm_embed_model=self.litellm_embed_model
        )
        
        # Connect signals
        self._runnable.signals.finished.connect(self.finished.emit)
        self._runnable.signals.error.connect(self.error.emit)
        self._runnable.signals.cancelled.connect(self.cancelled.emit)
        
        # Start the runnable in the thread pool
        ThreadManager.instance().start_runnable(self._runnable)

    def cancel(self):
        """Request cancellation of the running task."""
        if self._runnable:
            self._runnable.cancel()
