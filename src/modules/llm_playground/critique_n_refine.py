import re
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import sys
from PySide6.QtCore import Signal, Slot, QObject

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.llm.llm_utils_adapter import LLMWorker

class CritiqueNRefineWorker(QObject):
    """Worker that implements the critique and refine prompt optimization technique.
    
    This worker performs iterative prompt improvement using the following steps:
    1. Generate a critique of the current prompt
    2. Use the critique to refine the prompt
    3. Return the refined prompt
    """
    finished = Signal(str)  # Emits the refined prompt
    progress = Signal(str)  # Emits progress updates
    error = Signal(str)     # Emits error messages
    cancelled = Signal()    # Emits when cancelled
    
    def __init__(self, model_name: str, user_prompt: str, system_prompt: Optional[str] = None, 
                 iterations: int = 1, model_params: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.model_name = model_name
        self.user_prompt = user_prompt
        self.system_prompt = system_prompt
        self.iterations = iterations
        self.model_params = model_params or {}
        self.cancelled_flag = False
        
        # Store references to workers to prevent premature garbage collection
        self.critique_worker = None
        self.refine_worker = None
        
    def cancel(self):
        """Request cancellation of the running task."""
        self.cancelled_flag = True
        
    @Slot()
    def run(self):
        """Execute the critique and refine process."""
        try:
            self.current_prompt = self.user_prompt
            self.system_prompt = self.system_prompt
            
            # Extract the actual prompt content if wrapped in tags
            self.prompt_content = self._extract_prompt_content(self.current_prompt)
            self.current_iteration = 0
            self.critique = None
            
            # Start the first iteration
            self._start_next_iteration()
            
        except Exception as e:
            logging.error(f"Error in critique and refine process: {str(e)}")
            self.error.emit(f"Error in critique and refine process: {str(e)}")
    
    def _start_next_iteration(self):
        """Start the next iteration of the critique and refine process."""
        if self.cancelled_flag:
            self.cancelled.emit()
            return
            
        if self.current_iteration >= self.iterations:
            # All iterations completed, format and emit the result
            result = self._format_result(self.prompt_content, self.critique)
            self.finished.emit(result)
            return
            
        # Start the critique step
        self.progress.emit(f"Iteration {self.current_iteration+1}/{self.iterations}: Generating critique...")
        self._start_critique()
    
    def _start_critique(self):
        """Start the critique step."""
        critique_system_prompt = (
            "You are an expert prompt engineer tasked with analyzing and critiquing prompts. "
            "Your goal is to identify strengths and weaknesses in the prompt and suggest specific improvements. "
            "Focus on clarity, specificity, structure, and potential ambiguities."
        )
        
        critique_user_prompt = (
            "Please analyze and critique the following prompt. Identify its strengths and weaknesses, "
            "focusing on clarity, specificity, structure, and potential ambiguities. "
            "Provide specific suggestions for improvement.\n\n"
            f"PROMPT TO CRITIQUE:\n{self.prompt_content}\n\n"
            "Your critique should cover:\n"
            "1. Overall assessment\n"
            "2. Specific strengths\n"
            "3. Areas for improvement\n"
            "4. Specific suggestions for enhancement"
        )
        
        # Create worker using the new LLMWorker implementation
        self.critique_worker = LLMWorker(
            model_name=self.model_name,
            user_prompt=critique_user_prompt,
            system_prompt=critique_system_prompt,
            model_params=self.model_params
        )
        
        # Connect signals
        self.critique_worker.finished.connect(self._on_critique_finished)
        self.critique_worker.error.connect(self._on_critique_error)
        
        # Run the worker
        self.critique_worker.run()
    
    def _extract_prompt_content(self, prompt: str) -> str:
        """Extract the actual prompt content from the input.
        
        If the prompt is wrapped in <original_prompt> tags, extract the content.
        Otherwise, return the prompt as is.
        """
        # Check if the prompt is wrapped in tags
        if "<original_prompt>" in prompt and "</original_prompt>" in prompt:
            pattern = r"<original_prompt>\s*(.+?)\s*</original_prompt>"
            match = re.search(pattern, prompt, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        return prompt
    
    def _on_critique_finished(self, critique):
        """Handle the completion of the critique step."""
        if self.cancelled_flag:
            self.cancelled.emit()
            return
            
        # Store the critique for later use
        self.critique = critique
        
        # Start the refine step
        self.progress.emit(f"Iteration {self.current_iteration+1}/{self.iterations}: Refining prompt...")
        self._start_refine()
    
    def _on_critique_error(self, error_msg):
        """Handle errors in the critique step."""
        self.error.emit(f"Error generating critique: {error_msg}")
    
    def _start_refine(self):
        """Start the refine step."""
        refine_system_prompt = (
            "You are an expert prompt engineer tasked with refining and improving prompts "
            "based on critique and analysis. Your goal is to create a clearer, more effective prompt "
            "that addresses the weaknesses identified in the critique while maintaining the original intent."
        )
        
        refine_user_prompt = (
            "Based on the critique provided, please refine and improve the original prompt. "
            "Create a new version that addresses the weaknesses identified while maintaining the original intent.\n\n"
            f"ORIGINAL PROMPT:\n{self.prompt_content}\n\n"
            f"CRITIQUE:\n{self.critique}\n\n"
            "Please provide only the refined prompt without any additional explanations or commentary."
        )
        
        # Create worker using the new LLMWorker implementation
        self.refine_worker = LLMWorker(
            model_name=self.model_name,
            user_prompt=refine_user_prompt,
            system_prompt=refine_system_prompt,
            model_params=self.model_params
        )
        
        # Connect signals
        self.refine_worker.finished.connect(self._on_refine_finished)
        self.refine_worker.error.connect(self._on_refine_error)
        
        # Run the worker
        self.refine_worker.run()
    
    def _on_refine_finished(self, refined_prompt):
        """Handle the completion of the refine step."""
        if self.cancelled_flag:
            self.cancelled.emit()
            return
            
        # Update the prompt content with the refined version
        self.prompt_content = refined_prompt
        
        # Increment the iteration counter
        self.current_iteration += 1
        
        # Start the next iteration
        self._start_next_iteration()
    
    def _on_refine_error(self, error_msg):
        """Handle errors in the refine step."""
        self.error.emit(f"Error refining prompt: {error_msg}")
    
    def cancel(self):
        """Cancel the critique and refine process."""
        self.cancelled_flag = True
    
    def _format_result(self, refined_prompt: str, critique: str) -> str:
        """Format the final result with the critique and refinement process."""
        return (
            "# Prompt Optimization: Critique & Refine\n\n"
            "## Critique of Original Prompt\n\n"
            f"{critique}\n\n"
            "## Refined Prompt\n\n"
            f"{refined_prompt}"
        )
