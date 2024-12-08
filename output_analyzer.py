from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple, NamedTuple
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import nltk
import json
from .llm_utils import run_llm, run_embedding

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

class OutputAnalyzer:
    def __init__(self):
        # Ensure NLTK resources are available
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)
            
        # Initialize history
        self.analysis_results: List[AnalysisResult] = []

    def _get_text_embedding(self, text: str) -> np.ndarray:
        """Get embedding for the entire text."""
        try:
            embedding_str = run_embedding(text, embed_model="3-large")
            embedding = eval(embedding_str)  # Safe here since we know the format is a list of numbers
            return np.array([embedding])  # Return as 2D array for cosine_similarity
        except Exception as e:
            raise SimilarityError(f"Error getting text embedding: {str(e)}")

    def _compute_semantic_similarity(self, baseline: str, current: str) -> float:
        """Compute semantic similarity between baseline and current outputs."""
        try:
            baseline_embedding = self._get_text_embedding(baseline)
            current_embedding = self._get_text_embedding(current)
            
            similarity = cosine_similarity(baseline_embedding, current_embedding)[0][0]
            return similarity
            
        except Exception as e:
            raise SimilarityError(f"Error computing semantic similarity: {str(e)}")

    def _get_llm_grade(self, user_prompt: str, baseline: str, current: str, model: str = "gpt-4o") -> tuple[str, str]:
        """Get LLM-based grade and feedback comparing baseline and current outputs."""
        system_prompt = """You are an expert evaluator of language model outputs. Your task is to:
1. Compare the quality and correctness of two outputs (baseline and current) for the same user prompt
2. Assess how well each output addresses the user's needs
3. Identify key differences in approach, style, or content
4. Provide a letter grade (A, B, C, D, F) for the current output relative to the baseline
5. Give detailed feedback explaining your grade and assessment

Format your response as:
Grade: [letter grade]
---
[detailed feedback]"""

        evaluation_prompt = f"""User Prompt: {user_prompt}

Baseline Output:
{baseline}

Current Output:
{current}

Please evaluate the current output compared to the baseline."""

        try:
            result = run_llm(
                user_prompt=evaluation_prompt,
                system_prompt=system_prompt,
                model=model
            )
            
            grade_line, *feedback_lines = result.split('\n')
            grade = grade_line.replace('Grade:', '').strip()
            feedback = '\n'.join(feedback_lines).strip()
            
            return grade, feedback
            
        except Exception as e:
            raise LLMError(f"Error getting LLM evaluation: {str(e)}")

    def analyze_differences(self, baseline: str, current: str) -> dict:
        """Analyze differences between baseline and current outputs."""
        try:
            similarity = self._compute_semantic_similarity(baseline, current)
            
            return {
                'similarity': {'Overall': similarity},
                'changes': [
                    "Detailed sentence-level comparison removed in favor of overall semantic similarity"
                ]
            }
            
        except Exception as e:
            raise AnalysisError(f"Error analyzing differences: {str(e)}")

    def analyze_test_case(self, input_text: str, baseline: str, current: str, model: str = "gpt-4o") -> AnalysisResult:
        """Analyze a single test case and store the result."""
        try:
            # Compute similarity
            similarity = self._compute_semantic_similarity(baseline, current)
            
            # Get LLM grade and feedback
            grade, feedback = self._get_llm_grade(input_text, baseline, current, model)
            
            # Create result
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
        if not (0 <= index < len(self.analysis_results)):
            return "No analysis available"
            
        result = self.analysis_results[index]
        return f"""Semantic Similarity Analysis:
• Overall Similarity Score: {result.similarity_score:.2f}

Note: Using dense vector embeddings to compare entire text outputs."""

    def get_feedback_text(self, index: int) -> str:
        """Get formatted feedback text for the given result index."""
        if not (0 <= index < len(self.analysis_results)):
            return "No feedback available"
            
        result = self.analysis_results[index]
        return f"""Grade: {result.llm_grade}
---
{result.llm_feedback}"""