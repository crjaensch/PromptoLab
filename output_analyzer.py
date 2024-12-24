from dataclasses import dataclass
from pathlib import Path
import sys
import os
from typing import Optional, Dict, List, Tuple, NamedTuple
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import nltk
import json
from PySide6.QtCore import QObject, Signal

# Add the project root directory to Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from llm_utils import run_llm_async, run_embedding_async
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
        
    def start_analysis(self, input_text: str, baseline: str, current: str, model: str = "gpt-4o"):
        """Start the async analysis process."""
        self.input_text = input_text
        self.baseline = baseline
        self.current = current
        self.model = model
        
        # Start getting embeddings
        self._get_embeddings_async()
        
    def _get_embeddings_async(self):
        """Get embeddings for both texts asynchronously."""
        try:
            # Start baseline embedding
            baseline_runner = run_embedding_async(self.baseline)
            baseline_runner.finished.connect(lambda result: self._handle_baseline_embedding(result))
            baseline_runner.error.connect(self.error.emit)
            self.pending_embeddings.append(baseline_runner)
            
            # Start current embedding
            current_runner = run_embedding_async(self.current)
            current_runner.finished.connect(lambda result: self._handle_current_embedding(result))
            current_runner.error.connect(self.error.emit)
            self.pending_embeddings.append(current_runner)
            
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
        system_prompt = get_grader_system_prompt()
        evaluation_prompt = get_grader_instructions(
            self.input_text, 
            self.baseline, 
            self.current
        )

        try:
            runner = run_llm_async(
                user_prompt=evaluation_prompt,
                system_prompt=system_prompt,
                model=self.model
            )
            runner.finished.connect(lambda result: self._handle_grade_result(result, similarity))
            runner.error.connect(self.error.emit)
            self.current_runner = runner
            
        except Exception as e:
            self.error.emit(f"Error getting LLM evaluation: {str(e)}")
            
    def _handle_grade_result(self, result, similarity):
        """Handle completion of LLM grading."""
        try:
            grade_line, *feedback_lines = result.split('\n')
            grade = grade_line.replace('Grade:', '').strip()
            feedback = '\n'.join(feedback_lines).strip()
            
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
            
            # Store result in analyzer
            self.output_analyzer.analysis_results.append(analysis_result)
            
            # Emit result
            self.finished.emit(analysis_result)
            
        except Exception as e:
            self.error.emit(f"Error processing grade result: {str(e)}")

class OutputAnalyzer:
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
        return AsyncAnalyzer(self)

    async def _get_text_embedding(self, text: str) -> np.ndarray:
        """Get embedding for the entire text."""
        try:
            runner = run_embedding_async(text, embed_model="3-large")
            embedding_str = await runner.wait_for_output()
            embedding = eval(embedding_str)  # Safe here since we know the format is a list of numbers
            return np.array([embedding])  # Return as 2D array for cosine_similarity
        except Exception as e:
            raise SimilarityError(f"Error getting text embedding: {str(e)}")

    async def _compute_semantic_similarity(self, baseline: str, current: str) -> float:
        """Compute semantic similarity between baseline and current outputs."""
        try:
            baseline_embedding = await self._get_text_embedding(baseline)
            current_embedding = await self._get_text_embedding(current)
            
            similarity = cosine_similarity(baseline_embedding, current_embedding)[0][0]
            return similarity
            
        except Exception as e:
            raise SimilarityError(f"Error computing semantic similarity: {str(e)}")

    async def _get_llm_grade(self, user_prompt: str, baseline: str, current: str, model: str = "gpt-4o") -> tuple[str, str]:
        """Get LLM-based grade and feedback comparing baseline and current outputs."""
        system_prompt = get_grader_system_prompt()
        evaluation_prompt = get_grader_instructions(user_prompt, baseline, current)

        try:
            runner = run_llm_async(
                user_prompt=evaluation_prompt,
                system_prompt=system_prompt,
                model=model
            )
            result = await runner.wait_for_output()
            
            grade_line, *feedback_lines = result.split('\n')
            grade = grade_line.replace('Grade:', '').strip()
            feedback = '\n'.join(feedback_lines).strip()
            
            return grade, feedback
            
        except Exception as e:
            raise LLMError(f"Error getting LLM grade: {str(e)}")

    async def analyze_differences(self, baseline: str, current: str) -> dict:
        """Analyze differences between baseline and current outputs."""
        try:
            similarity = await self._compute_semantic_similarity(baseline, current)
            
            return {
                'similarity': {'Overall': similarity},
                'changes': [
                    "Detailed sentence-level comparison removed in favor of overall semantic similarity"
                ]
            }
            
        except Exception as e:
            raise AnalysisError(f"Error analyzing differences: {str(e)}")

    async def analyze_test_case(self, input_text: str, baseline: str, current: str, model: str = "gpt-4o") -> AnalysisResult:
        """Analyze a single test case and store the result."""
        try:
            # Get semantic similarity
            similarity = await self._compute_semantic_similarity(baseline, current)
            
            # Get LLM grade and feedback
            grade, feedback = await self._get_llm_grade(input_text, baseline, current, model)
            
            # Create result object
            result = AnalysisResult(
                input_text=input_text,
                baseline_output=baseline,
                current_output=current,
                similarity_score=similarity,
                llm_grade=grade,
                llm_feedback=feedback,
                key_changes=[
                    "Using overall semantic similarity for comparison",
                    "Similarity score represents whole text comparison"
                ]
            )
            
            # Store result
            self.analysis_results.append(result)
            return result
            
        except Exception as e:
            raise AnalysisError(f"Error analyzing test case: {str(e)}")

    def clear_history(self):
        """Clear the analysis history."""
        self.analysis_results = []

    def get_analysis_text(self, index: int) -> str:
        """Get formatted analysis text for the given result index."""
        if not self.analysis_results or index >= len(self.analysis_results):
            return "No analysis available"
            
        result = self.analysis_results[index]
        return """Semantic Similarity Analysis
------------------------
Overall Similarity Score: {:.2f}

Key Changes:
{}""".format(
            result.similarity_score,
            "".join("- {}{}".format(change, os.linesep) for change in result.key_changes)
        )

    def get_feedback_text(self, index: int) -> str:
        """Get formatted feedback text for the given result index."""
        if not self.analysis_results or index >= len(self.analysis_results):
            return "No feedback available"
            
        result = self.analysis_results[index]
        return """LLM Evaluation
-------------
Grade: {}

Detailed Feedback:
{}""".format(result.llm_grade, result.llm_feedback)