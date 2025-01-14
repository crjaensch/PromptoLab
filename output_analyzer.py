from dataclasses import dataclass
from pathlib import Path
import sys
import os
from typing import Optional, Dict, List, Tuple, NamedTuple
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import nltk
import json
from PySide6.QtCore import QObject, Signal, QThread

# Add the project root directory to Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from llm_utils_adapter import LLMWorker, EmbedWorker
from special_prompts import (get_grader_system_prompt,
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
        self.active_threads = []   # Keep track of active threads
        
    def start_analysis(self, input_text: str, baseline: str, current: str, model: str = "gpt-4o"):
        """Start the async analysis process."""
        self.input_text = input_text
        self.baseline = baseline
        self.current = current
        self.model = model
        
        # Start getting embeddings
        self._get_embeddings_async()
        
    def _create_embed_worker(self, text: str, on_finished) -> QThread:
        """Create and setup a thread with an EmbedWorker.
        
        Args:
            text: The text to embed
            on_finished: Callback function to handle the embedding result
            
        Returns:
            QThread ready to be started
        """
        # Create worker in new thread
        worker_thread = QThread()
        worker = EmbedWorker(text=text)
        worker.moveToThread(worker_thread)
        
        # Keep track of thread for cleanup
        # -- may be not needed: worker.thread = thread
        self.active_threads.append(worker_thread)
        self.pending_embeddings.append(worker)

        # Connect signals
        worker.finished.connect(on_finished)
        worker.error.connect(self.error.emit)
        worker_thread.started.connect(worker.run)
        worker_thread.finished.connect(worker_thread.deleteLater)

        return worker_thread
        
    def _get_embeddings_async(self):
        """Get embeddings for both texts asynchronously."""
        try:
            # Start baseline embedding
            self._create_embed_worker(
                self.baseline,
                lambda result: self._handle_baseline_embedding(result)
            ).start()
            
            # Start current embedding
            self._create_embed_worker(
                self.current,
                lambda result: self._handle_current_embedding(result)
            ).start()
            
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
            # Create worker in new thread
            worker_thread = QThread()
            worker = LLMWorker(
                model_name=self.model,
                user_prompt=grader_user_prompt,
                system_prompt=grader_system_prompt
            )
            worker.moveToThread(worker_thread)

            # Keep track of thread for cleanup
            # -- may be not needed: worker.thread = worker_thread
            self.active_threads.append(worker_thread)
            self.current_runner = worker

            # Connect signals
            worker.finished.connect(lambda result: self._handle_grade_result(result, similarity))
            worker.error.connect(self.error.emit)
            worker_thread.started.connect(worker.run)
            worker_thread.finished.connect(worker_thread.deleteLater)
          
            # Start thread
            worker_thread.start()
            
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
            
            # Create final result
            analysis_result = AnalysisResult(
                input_text=self.input_text,
                baseline_output=self.baseline,
                current_output=self.current,
                similarity_score=similarity,
                llm_grade=grade,
                llm_feedback=feedback,
                key_changes=[
                    "Using overall semantic similarity for comparison",
                    "Similarity score represents whole text comparison"
                ]
            )
            
            # Emit result
            self.finished.emit(analysis_result)
            
        except Exception as e:
            self.error.emit(f"Error processing LLM grade result: {str(e)}")

    def cleanup(self):
        """Clean up any running workers."""
        # Cancel any pending workers
        for worker in self.pending_embeddings:
            worker.cancel()
        if self.current_runner:
            self.current_runner.cancel()
        
        # Clean up threads safely
        for thread in self.active_threads:
            try:
                thread.quit()
                # Wait for the thread to exit its event loop
                if not thread.wait(1000):  # for example, 1s
                    print("Warning: thread did not exit in time!")
            except Exception:
                pass  # Ignore cleanup errors
        
        self.active_threads.clear()
        self.pending_embeddings.clear()
        self.current_runner = None

class OutputAnalyzer:
    """Class for analyzing and comparing outputs."""
    def __init__(self):
        # Ensure NLTK resources are available
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)
            
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