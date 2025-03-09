import logging
logging.debug('output_analyzer module imported.')

import sys
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from PySide6.QtCore import QObject, Signal

# Import thread management utilities
from src.utils.thread_manager import ThreadManager

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.llm.llm_utils_adapter import LLMWorker, EmbedWorker
from src.llm.special_prompts import (get_grader_system_prompt,
                            get_grader_instructions)

class AnalysisError(Exception):
    """Base class for analysis errors"""
    pass

class LLMError(AnalysisError):
    """Error during LLM operations"""
    pass

class SimilarityError(AnalysisError):
    """Error during similarity computation"""
    pass

@dataclass
class AnalysisResult:
    """Container for a single analysis result."""
    input_text: str
    baseline_output: str
    current_output: str
    similarity_score: float
    llm_grade: str
    llm_feedback: str
    key_changes: List[str]

class AsyncAnalyzer(QObject):
    """Async wrapper for OutputAnalyzer operations."""
    finished = Signal(AnalysisResult)
    error = Signal(str)
    
    def __init__(self, output_analyzer):
        super().__init__()
        self.output_analyzer = output_analyzer
        self.current_runner = None
        self.pending_embeddings = []
        self.baseline_embedding = None
        self.current_embedding = None
        self.grade = None
        self.feedback = None
        
    def start_analysis(self, input_text: str, baseline: str, current: str, model: str = "gpt-4o"):
        """Start the async analysis process."""
        self.input_text = input_text
        self.baseline = baseline
        self.current = current
        self.model = model
        
        # Start getting embeddings
        self._get_embeddings_async()
        
    def _create_embed_worker(self, text: str, on_finished):
        """Create and setup an EmbedWorker using the thread pool.
        
        Args:
            text: The text to embed
            on_finished: Callback function to handle the embedding result
        """
        # Create worker
        worker = EmbedWorker(text=text)
        
        # Keep track of worker for cleanup
        self.pending_embeddings.append(worker)

        # Connect signals
        worker.finished.connect(on_finished)
        worker.error.connect(self.error.emit)
        
        # Start the worker (which will use the thread pool internally)
        worker.run()
        
    def _get_embeddings_async(self):
        """Get embeddings for both texts asynchronously."""
        try:
            # Start baseline embedding
            self._create_embed_worker(
                self.baseline,
                lambda result: self._handle_baseline_embedding(result)
            )
            
            # Start current embedding
            self._create_embed_worker(
                self.current,
                lambda result: self._handle_current_embedding(result)
            )
            
        except Exception as e:
            self.error.emit(f"Error starting embeddings: {str(e)}")
            
    def _handle_baseline_embedding(self, result):
        """Handle completion of baseline embedding."""
        try:
            self.baseline_embedding = np.array([eval(result)])
            self._check_completion()
        except Exception as e:
            self.error.emit(f"Error processing baseline embedding: {str(e)}")
            
    def _handle_current_embedding(self, result):
        """Handle completion of current embedding."""
        try:
            self.current_embedding = np.array([eval(result)])
            self._check_completion()
        except Exception as e:
            self.error.emit(f"Error processing current embedding: {str(e)}")
            
    def _check_completion(self):
        """Check if all async operations are complete and emit result."""
        if self.baseline_embedding is not None and self.current_embedding is not None:
            # Calculate similarity
            similarity = cosine_similarity(self.baseline_embedding, self.current_embedding)[0][0]
            
            # Start LLM grading
            self._get_llm_grade(similarity)
            
    def _get_llm_grade(self, similarity):
        """Get LLM grade asynchronously."""
        grader_system_prompt = get_grader_system_prompt()
        grader_user_prompt = get_grader_instructions(
            self.input_text, 
            self.baseline, 
            self.current
        )

        try:
            # Create worker using the new LLMWorker implementation
            worker = LLMWorker(
                model_name=self.model,
                user_prompt=grader_user_prompt,
                system_prompt=grader_system_prompt
            )

            # Keep track of worker for cleanup
            self.current_runner = worker

            # Connect signals
            worker.finished.connect(lambda result: self._handle_grade_result(result, similarity))
            worker.error.connect(self.error.emit)
            
            # Start the worker (which will use the thread pool internally)
            worker.run()
            
        except Exception as e:
            self.error.emit(f"Error getting LLM evaluation: {str(e)}")
            
    def _handle_grade_result(self, result, similarity):
        """Handle completion of LLM grading."""
        try:
            # Try parsing as JSON first
            try:
                grade_dict = json.loads(result)
                grade = grade_dict.get('grade', 'ERROR')
                feedback = grade_dict.get('feedback', 'No feedback provided')
            except json.JSONDecodeError:
                # Fallback to text format parsing
                lines = result.strip().split('\n')
                if not lines:
                    raise ValueError("Empty LLM response")
                    
                # First line should contain the grade
                grade_line = lines[0]
                grade = grade_line.replace('Grade:', '').strip()
                
                # Rest is feedback
                feedback = '\n'.join(lines[1:]).strip()
            
            # Validate and normalize the grade format
            try:
                # Check if the grade is in the comparative format (-2, -1, 0, +1, +2)
                # Remove any spaces and ensure + sign is preserved
                normalized_grade = grade.replace(" ", "")
                
                # Map numerical grades to thumb emojis
                grade_to_emoji = {
                    "-2": "👎👎",  # Two thumbs down
                    "-1": "👎",    # One thumb down
                    "0": "👈",     # Thumb pointing left (horizontal)
                    "+1": "👍",    # One thumb up
                    "+2": "👍👍",  # Two thumbs up
                    "1": "👍",     # Handle without + sign
                    "2": "👍👍"    # Handle without + sign
                }
                
                # Store both the numerical grade (for sorting/filtering) and the emoji (for display)
                if normalized_grade in grade_to_emoji:
                    emoji_grade = grade_to_emoji[normalized_grade]
                    # Keep the numerical grade as part of the object for potential sorting/filtering
                    numerical_grade = normalized_grade
                    if normalized_grade == "1":
                        numerical_grade = "+1"
                    elif normalized_grade == "2":
                        numerical_grade = "+2"
                    display_grade = emoji_grade
                else:
                    # If not in expected format, use as-is with a warning
                    display_grade = f"{normalized_grade} (invalid)"
                    numerical_grade = normalized_grade
                    logging.warning(f"Unexpected grade format: {grade}")
            except Exception as e:
                display_grade = grade  # Use original if parsing fails
                numerical_grade = grade
                logging.warning(f"Error normalizing grade: {e}")
            
            # Create final result
            analysis_result = AnalysisResult(
                input_text=self.input_text,
                baseline_output=self.baseline,
                current_output=self.current,
                similarity_score=similarity,
                llm_grade=display_grade,
                llm_feedback=feedback,
                key_changes=[
                    "Using overall semantic similarity for comparison",
                    "Similarity score represents whole text comparison",
                    "Grade scale: 👎👎 (much worse) 👎 (worse) 👈 (same) 👍 (better) 👍👍 (much better)"
                ]
            )
            
            # Emit result
            self.finished.emit(analysis_result)
            
        except Exception as e:
            self.error.emit(f"Error processing LLM grade result: {str(e)}")
            
    def cleanup(self):
        logging.debug("AsyncAnalyzer.cleanup() started.")
        
        # Cancel any pending workers
        logging.debug('Canceling pending workers.')
        for worker in self.pending_embeddings:
            worker.cancel()
        if self.current_runner:
            self.current_runner.cancel()
        
        # Clear our references to workers
        self.pending_embeddings.clear()
        self.current_runner = None
        
        # Note: We don't need to manually clean up threads anymore
        # as the ThreadManager handles thread lifecycle management
        
        logging.debug("AsyncAnalyzer.cleanup() completed.")

class OutputAnalyzer:
    """Class for analyzing and comparing outputs."""
    def __init__(self):
        # Initialize history
        self.analysis_results: List[AnalysisResult] = []
        
    def create_async_analyzer(self) -> AsyncAnalyzer:
        """Create an async analyzer instance."""
        analyzer = AsyncAnalyzer(self)
        analyzer.finished.connect(self.analysis_results.append)
        return analyzer
        
    def clear_history(self):
        """Clear the analysis history."""
        self.analysis_results = []
        
    def get_analysis_text(self, index: int) -> str:
        """Get formatted analysis text for the given result index."""
        if not self.analysis_results or index >= len(self.analysis_results):
            return "No analysis available"
            
        result = self.analysis_results[index]
        return (
            f"Semantic Similarity Analysis:\n"
            f"• Overall Similarity Score: {result.similarity_score:.2f}\n\n"
            "Note: Using overall semantic similarity for comparison"
        )
        
    def get_feedback_text(self, index: int) -> str:
        """Get formatted feedback text for the given result index."""
        if not self.analysis_results or index >= len(self.analysis_results):
            return "No feedback available"
            
        result = self.analysis_results[index]
        return f"Grade: {result.llm_grade}\n---\n{result.llm_feedback}"