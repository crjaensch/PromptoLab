import re
import logging
from typing import Dict, Any, Optional, List, Tuple
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
        
    def cancel(self):
        """Request cancellation of the running task."""
        self.cancelled_flag = True
        
    @Slot()
    def run(self):
        """Execute the critique and refine process."""
        try:
            current_prompt = self.user_prompt
            system_prompt = self.system_prompt
            
            # Extract the actual prompt content if wrapped in tags
            prompt_content = self._extract_prompt_content(current_prompt)
            
            for i in range(self.iterations):
                if self.cancelled_flag:
                    self.cancelled.emit()
                    return
                    
                # Step 1: Generate critique
                self.progress.emit(f"Iteration {i+1}/{self.iterations}: Generating critique...")
                critique = self._generate_critique(prompt_content)
                
                if self.cancelled_flag:
                    self.cancelled.emit()
                    return
                    
                # Step 2: Refine the prompt based on critique
                self.progress.emit(f"Iteration {i+1}/{self.iterations}: Refining prompt...")
                refined_prompt = self._refine_prompt(prompt_content, critique)
                
                # Update for next iteration
                prompt_content = refined_prompt
            
            # Format the final result with the critique and refinement process
            result = self._format_result(prompt_content, critique)
            self.finished.emit(result)
            
        except Exception as e:
            logging.error(f"Error in critique and refine process: {str(e)}")
            self.error.emit(f"Error in critique and refine process: {str(e)}")
    
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
    
    def _generate_critique(self, prompt: str) -> str:
        """Generate a critique of the current prompt."""
        critique_system_prompt = (
            "You are an expert prompt engineer tasked with analyzing and critiquing prompts. "
            "Your goal is to identify strengths and weaknesses in the prompt and suggest specific improvements. "
            "Focus on clarity, specificity, structure, and potential ambiguities."
        )
        
        critique_user_prompt = (
            "Please analyze and critique the following prompt. Identify its strengths and weaknesses, "
            "focusing on clarity, specificity, structure, and potential ambiguities. "
            "Provide specific suggestions for improvement.\n\n"
            f"PROMPT TO CRITIQUE:\n{prompt}\n\n"
            "Your critique should cover:\n"
            "1. Overall assessment\n"
            "2. Specific strengths\n"
            "3. Areas for improvement\n"
            "4. Specific suggestions for enhancement"
        )
        
        # Run LLM to generate critique
        worker = LLMWorker(
            model_name=self.model_name,
            user_prompt=critique_user_prompt,
            system_prompt=critique_system_prompt,
            model_params=self.model_params
        )
        
        # Since we're in a worker thread already, we can call run directly
        # but we need to capture the result
        result = None
        error = None
        
        def on_finished(res):
            nonlocal result
            result = res
            
        def on_error(err):
            nonlocal error
            error = err
            
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        worker.run()
        
        if error:
            raise Exception(f"Error generating critique: {error}")
            
        return result
    
    def _refine_prompt(self, original_prompt: str, critique: str) -> str:
        """Refine the prompt based on the critique."""
        refine_system_prompt = (
            "You are an expert prompt engineer tasked with refining and improving prompts "
            "based on critique and analysis. Your goal is to create a clearer, more effective prompt "
            "that addresses the weaknesses identified in the critique while maintaining the original intent."
        )
        
        refine_user_prompt = (
            "Based on the critique provided, please refine and improve the original prompt. "
            "Create a new version that addresses the weaknesses identified while maintaining the original intent.\n\n"
            f"ORIGINAL PROMPT:\n{original_prompt}\n\n"
            f"CRITIQUE:\n{critique}\n\n"
            "Please provide only the refined prompt without any additional explanations or commentary."
        )
        
        # Run LLM to refine prompt
        worker = LLMWorker(
            model_name=self.model_name,
            user_prompt=refine_user_prompt,
            system_prompt=refine_system_prompt,
            model_params=self.model_params
        )
        
        # Since we're in a worker thread already, we can call run directly
        # but we need to capture the result
        result = None
        error = None
        
        def on_finished(res):
            nonlocal result
            result = res
            
        def on_error(err):
            nonlocal error
            error = err
            
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        worker.run()
        
        if error:
            raise Exception(f"Error refining prompt: {error}")
            
        return result
    
    def _format_result(self, refined_prompt: str, critique: str) -> str:
        """Format the final result with the critique and refinement process."""
        return (
            "# Prompt Optimization: Critique & Refine\n\n"
            "## Critique of Original Prompt\n\n"
            f"{critique}\n\n"
            "## Refined Prompt\n\n"
            f"{refined_prompt}"
        )
