# QtModelWorkers.py
import sys
import traceback
import json
import logging
from PySide6.QtCore import Signal, Slot, QObject, Qt
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
        """Executed in the worker thread."""
        try:
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

            self.finished.emit(result)

        except (llm_utils_llmcmd.LLMQuotaError,
                llm_utils_llmcmd.LLMCapabilityError,
                llm_utils_llmcmd.LLMConnectionError) as e:
            # Pass through the user-friendly error messages
            self.error.emit(str(e))

        except Exception as e:
            tb_str = traceback.format_exc()
            self.error.emit(f"{e}\n{tb_str}")

    def cancel(self):
        """Request cancellation of the running task."""
        # Note: Since we're using synchronous calls, cancellation is not supported
        pass

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
        
    @Slot()
    def run(self):
        """Executed in the worker thread."""
        try:
            # Run the embed model request
            if config.llm_api == 'llm-cmd':
                result = llm_utils_llmcmd.run_embed(self.llm_cmd_embed_model, self.text)
            else:
                result = llm_utils_litellm.run_embed(self.litellm_embed_model, self.text)            

            # Convert List[float] to JSON string before emitting
            json_result = json.dumps(result)
            self.finished.emit(json_result)

        except (llm_utils_llmcmd.LLMQuotaError,
                llm_utils_llmcmd.LLMCapabilityError,
                llm_utils_llmcmd.LLMConnectionError) as e:
            # Pass through the user-friendly error messages
            self.error.emit(str(e))

        except Exception as e:
            tb_str = traceback.format_exc()
            self.error.emit(f"{e}\n{tb_str}")

    def cancel(self):
        """Request cancellation of the running task."""
        # Note: Since we're using synchronous calls, cancellation is not supported
        pass
