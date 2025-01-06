from dataclasses import dataclass
from itertools import zip_longest
from typing import List
import json
import logging
import nltk
import numpy as np
from PySide6.QtCore import QObject, Signal, QThread, QTimer
from sklearn.metrics.pairwise import cosine_similarity

from llm_utils_adapter import LLMWorker, EmbedWorker
from special_prompts import get_grader_system_prompt, get_grader_instructions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

class AnalysisError(Exception):
    """Base class for analysis errors"""
    pass

class SimilarityError(AnalysisError):
    """Error computing similarity"""
    pass

class LLMError(AnalysisError):
    """Error getting LLM grade"""
    pass

class OutputAnalyzer(QObject):
    """Handles analysis of output text comparisons with UI integration."""
    finished = Signal(AnalysisResult)
    error = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Initialize NLTK resources
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)
            
        # Worker-related variables
        self.worker_thread = None
        self.worker = None
        self.embed_thread = None
        self.embed_worker = None
        self.progress_dialog = None
        
        # Analysis state
        self.input_text = None
        self.baseline = None
        self.current = None
        self.model = None
        self.baseline_embedding = None
        self.current_embedding = None
        self.grade = None
        self.feedback = None
        
        # Analysis history
        self.analysis_results: List[AnalysisResult] = []

    def start_analysis(self, input_text: str, baseline: str, current: str, model: str = "gpt-4o"):
        """Start the async analysis process."""
        self.input_text = input_text
        self.baseline = baseline
        self.current = current
        self.model = model
        
        # Start with embeddings
        self._get_embeddings_async()
    
    def clear_history(self):
        """Clear the analysis history."""
        self.analysis_results.clear()
    
    def get_analysis_text(self, index: int) -> str:
        """Get formatted analysis text for the given result index."""
        if 0 <= index < len(self.analysis_results):
            result = self.analysis_results[index]
            return (
                f"Similarity Score: {result.similarity_score:.2f}\n"
                f"LLM Grade: {result.llm_grade}\n\n"
                f"LLM Feedback:\n{result.llm_feedback}\n\n"
                "Key Changes:\n" + "\n".join(f"- {change}" for change in result.key_changes)
            )
        return ""

    def get_feedback_text(self, index: int) -> str:
        """Get formatted feedback text for the given result index."""
        if 0 <= index < len(self.analysis_results):
            return self.analysis_results[index].llm_feedback
        return ""

    def analyze_differences(self, baseline: str, current: str) -> List[str]:
        """Analyze differences between baseline and current outputs."""
        changes = []
        
        # Split into sentences
        baseline_sents = nltk.sent_tokenize(baseline)
        current_sents = nltk.sent_tokenize(current)
        
        # Compare sentence counts
        if len(baseline_sents) != len(current_sents):
            changes.append(f"Sentence count changed: {len(baseline_sents)} -> {len(current_sents)}")
        
        # Compare sentence by sentence
        for i, (base_sent, curr_sent) in enumerate(zip_longest(baseline_sents, current_sents)):
            if base_sent != curr_sent:
                if base_sent and curr_sent:
                    changes.append(f"Sentence {i+1} modified")
                elif base_sent:
                    changes.append(f"Sentence {i+1} removed")
                else:
                    changes.append(f"New sentence added at position {i+1}")
        
        return changes

    def cleanup(self):
        """Clean up all worker threads."""
        self.cleanup_llm_worker()
        self.cleanup_embed_worker()
        self.cleanup_progress()

    def cleanup_llm_worker(self):
        """Clean up LLM worker thread."""
        if self.worker_thread and self.worker_thread != QThread.currentThread():
            if self.worker:
                self.worker.cancel()  # Request cancellation first
            self.worker_thread.quit()
            self.worker_thread.wait(1000)  # Wait up to 1 second
            self.worker_thread = None
            self.worker = None

    def cleanup_embed_worker(self):
        """Clean up embedding worker thread."""
        if self.embed_thread and self.embed_thread != QThread.currentThread():
            if self.embed_worker:
                self.embed_worker.cancel()  # Request cancellation first
            self.embed_thread.quit()
            self.embed_thread.wait(1000)  # Wait up to 1 second
            self.embed_thread = None
            self.embed_worker = None

    def cleanup_progress(self):
        """Clean up progress dialog."""
        if self.progress_dialog:
            self.progress_dialog.reset()
            self.progress_dialog = None

    def _get_embeddings_async(self):
        """Get embeddings for both texts asynchronously."""
        self.embed_thread = QThread()
        self.embed_worker = EmbedWorker(
            llm_api="llm-cmd",  # TODO: Get from config
            embed_model="3-large",
            text=self.baseline
        )
        self.embed_worker.moveToThread(self.embed_thread)
        
        # Connect signals
        self.embed_thread.started.connect(self.embed_worker.run)
        self.embed_worker.finished.connect(self._handle_baseline_embedding)
        self.embed_worker.error.connect(lambda e: self.error.emit(f"Embedding error: {e}"))
        
        # Start thread
        self.embed_thread.start()

    def _handle_baseline_embedding(self, result: str):
        """Handle completion of baseline embedding."""
        try:
            # Debug log the raw result
            logger.info("Raw baseline embedding result type: %s", type(result))
            logger.info("Raw baseline embedding result: %s", result)
            
            if not result:
                raise ValueError("Empty embedding result received")
            
            # Convert string representation of list back to list using json
            embedding = json.loads(result)
            self.baseline_embedding = np.array([embedding])
            
            # Clean up baseline embedding worker
            self.cleanup_embed_worker()
            
            # Start current embedding
            self.embed_thread = QThread()
            self.embed_worker = EmbedWorker(
                llm_api="llm-cmd",  # TODO: Get from config
                embed_model="3-large",
                text=self.current
            )
            self.embed_worker.moveToThread(self.embed_thread)
            
            # Connect signals
            self.embed_thread.started.connect(self.embed_worker.run)
            self.embed_worker.finished.connect(self._handle_current_embedding)
            self.embed_worker.error.connect(lambda e: self.error.emit(f"Embedding error: {e}"))
            
            # Start thread
            self.embed_thread.start()
            
        except Exception as e:
            self.error.emit(f"Error processing baseline embedding: {str(e)}")
            self.cleanup()

    def _handle_current_embedding(self, result: str):
        """Handle completion of current embedding."""
        try:
            # Debug log the raw result
            logger.info("Raw current embedding result type: %s", type(result))
            logger.info("Raw current embedding result: %s", result)
            
            if not result:
                raise ValueError("Empty embedding result received")
            
            # Convert string representation of list back to list using json
            embedding = json.loads(result)
            self.current_embedding = np.array([embedding])
            
            # Clean up current embedding worker
            self.cleanup_embed_worker()
            
            # Compute similarity
            similarity = cosine_similarity(self.baseline_embedding, self.current_embedding)[0][0]
            
            # Start LLM grading
            self._get_llm_grade(similarity)
            
        except Exception as e:
            self.error.emit(f"Error processing current embedding: {str(e)}")
            self.cleanup()

    def _get_llm_grade(self, similarity: float):
        """Get LLM grade asynchronously."""
        # Get prompts from special_prompts
        system_prompt = get_grader_system_prompt()
        evaluation_prompt = get_grader_instructions(self.input_text, self.baseline, self.current)
        
        # Create and setup worker
        self.worker_thread = QThread()
        self.worker = LLMWorker(
            llm_api="llm-cmd",  # TODO: Get from config
            model_name=self.model,
            user_prompt=evaluation_prompt,
            system_prompt=system_prompt
        )
        self.worker.moveToThread(self.worker_thread)
        
        # Connect signals
        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(lambda result: self._handle_grade_result(result, similarity))
        self.worker.error.connect(lambda e: self.error.emit(f"LLM error: {e}"))
        
        # Start thread
        self.worker_thread.start()

    def _handle_grade_result(self, result: str, similarity: float):
        """Handle completion of LLM grading."""
        try:
            # Parse grade and feedback
            grade_line, *feedback_lines = result.split('\n')
            grade = grade_line.replace('Grade:', '').strip()
            feedback = '\n'.join(feedback_lines).strip()
            
            # Create analysis result
            analysis_result = AnalysisResult(
                input_text=self.input_text,
                baseline_output=self.baseline,
                current_output=self.current,
                similarity_score=similarity,
                llm_grade=grade,
                llm_feedback=feedback,
                key_changes=self.analyze_differences(self.baseline, self.current)
            )
            
            # Store result in history
            self.analysis_results.append(analysis_result)
            
            # Emit result before cleanup
            self.finished.emit(analysis_result)
            
            # Let the signal be processed before cleanup
            QTimer.singleShot(100, self.cleanup)
            
        except Exception as e:
            self.error.emit(f"Error processing grade result: {str(e)}")
            self.cleanup()