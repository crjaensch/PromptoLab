# QtModelWorkers.py
import sys
import traceback
import asyncio
import json
from PySide6.QtCore import Signal, Slot, QObject, Qt
from pathlib import Path

# Add the project root directory to Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import llm_utils_litellm
import llm_utils_llmcmd

class LLMWorker(QObject):
    """Worker that runs llm_utils_xxx.run_llm_async in its own thread + event loop."""
    finished = Signal(str)
    error = Signal(str)
    cancelled = Signal()
    
    def __init__(self, llm_api, model_name, user_prompt, system_prompt=None, model_params=None):
        super().__init__()
        self.llm_api = llm_api
        self.model_name = model_name
        self.user_prompt = user_prompt
        self.system_prompt = system_prompt
        self.model_params = model_params or {}
        
        self._loop = None
        self._task = None

    @staticmethod
    def get_models(llm_api: str) -> list[str]:
        """Return a list of available models for the specified LLM API.
        
        Args:
            llm_api: The LLM API to use ('llm-cmd' or 'litellm')
            
        Returns:
            A list of model names supported by the specified API.
        """
        if llm_api == "llm-cmd":
            return llm_utils_llmcmd.get_models()
        elif llm_api == "litellm":
            return llm_utils_litellm.get_models()
        else:
            raise ValueError(f"Unsupported LLM API: {llm_api}")

    @Slot()
    def run(self):
        """Executed in the worker thread. We'll set up our own asyncio event loop here."""
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            # Schedule the LLM request as a Task so we can cancel it later
            if self.llm_api == 'llm-cmd':
               self._task = self._loop.create_task(
                   llm_utils_llmcmd.run_llm_async(
                       self.model_name,
                       self.user_prompt,
                       self.system_prompt,
                       self.model_params
                   )
               )
            else:
                self._task = self._loop.create_task(
                   llm_utils_litellm.run_llm_async(
                       self.model_name,
                       self.user_prompt,
                       self.system_prompt,
                       self.model_params
                   )
               )            

            # Run the event loop until the task completes (or is cancelled)
            result = self._loop.run_until_complete(self._task)
            self.finished.emit(result)

        except asyncio.CancelledError:
            # This happens if we call self._task.cancel()
            self.cancelled.emit()

        except Exception as e:
            tb_str = traceback.format_exc()
            self.error.emit(f"{e}\n{tb_str}")

        finally:
            # Clean up the loop
            if self._loop is not None:
                self._loop.close()

    def cancel(self):
        """Request cancellation of the running task."""
        if self._loop and self._task and not self._task.done():
            # Schedule the cancellation inside the worker’s event loop
            # so it happens safely from the worker thread.
            self._loop.call_soon_threadsafe(self._task.cancel)

            
class EmbedWorker(QObject):
    """Worker that runs llm_utils_xxx.run_embed_async in its own thread + event loop."""
    finished = Signal(str)
    error = Signal(str)
    cancelled = Signal()
    
    def __init__(self, llm_api, embed_model, text):
        super().__init__()
        self.llm_api = llm_api
        self.embed_model = embed_model
        self.text = text
        
        self._loop = None
        self._task = None

    @Slot()
    def run(self):
        """Executed in the worker thread. We'll set up our own asyncio event loop here."""
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            # Schedule the embed model request as a Task so we can cancel it later
            if self.llm_api == 'llm-cmd':
               self._task = self._loop.create_task(
                   llm_utils_llmcmd.run_embed_async(self.embed_model, self.text)
               )
            else:
               self._task = self._loop.create_task(
                   llm_utils_litellm.run_embed_async(self.embed_model, self.text)
               )

            # Run the event loop until the task completes (or is cancelled)
            result = self._loop.run_until_complete(self._task)
            # Convert List[float] to JSON string before emitting
            json_result = json.dumps(result)
            self.finished.emit(json_result)

        except asyncio.CancelledError:
            # This happens if we call self._task.cancel()
            self.cancelled.emit()

        except Exception as e:
            tb_str = traceback.format_exc()
            self.error.emit(f"{e}\n{tb_str}")

        finally:
            # Clean up the loop
            if self._loop is not None:
                self._loop.close()

    def cancel(self):
        """Request cancellation of the running task."""
        if self._loop and self._task and not self._task.done():
            # Schedule the cancellation inside the worker’s event loop
            # so it happens safely from the worker thread.
            self._loop.call_soon_threadsafe(self._task.cancel)
