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

    def _get_sentence_embeddings(self, text: str) -> tuple[np.ndarray, List[str]]:
        """Get embeddings for each sentence in the text."""
        try:
            sentences = nltk.sent_tokenize(text)
        except Exception:
            # Fallback to simple splitting if NLTK fails
            sentences = text.split('. ')
        
        embeddings = []
        for sentence in sentences:
            embedding_str = run_embedding(sentence, embed_model="3-small")
            embedding = eval(embedding_str)  # Safe here since we know the format is a list of numbers
            embeddings.append(embedding)
        
        return np.array(embeddings), sentences

    def _compute_semantic_similarity(self, baseline: str, current: str) -> tuple[float, Dict[str, float]]:
        """Compute semantic similarity between baseline and current outputs."""
        try:
            baseline_embeddings, baseline_sentences = self._get_sentence_embeddings(baseline)
            current_embeddings, current_sentences = self._get_sentence_embeddings(current)
            
            similarity_matrix = cosine_similarity(baseline_embeddings, current_embeddings)
            overall_similarity = np.mean(np.max(similarity_matrix, axis=1))
            
            sentence_similarities = {}
            for i, base_sent in enumerate(baseline_sentences):
                best_match_idx = np.argmax(similarity_matrix[i])
                sentence_similarities[base_sent] = similarity_matrix[i][best_match_idx]
            
            return overall_similarity, sentence_similarities
            
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

    def analyze_test_case(self, input_text: str, baseline: str, current: str, model: str = "gpt-4o") -> AnalysisResult:
        """Analyze a single test case and store the result."""
        try:
            # Compute similarity
            similarity, _ = self._compute_semantic_similarity(baseline, current)
            
            # Get LLM grade and feedback
            grade, feedback = self._get_llm_grade(input_text, baseline, current, model)
            
            # Compute key changes
            baseline_sents = nltk.sent_tokenize(baseline)
            current_sents = nltk.sent_tokenize(current)
            key_changes = []
            
            # Simple diff for now - could be enhanced with more sophisticated comparison
            if len(baseline_sents) != len(current_sents):
                key_changes.append("Number of sentences changed")
            for b_sent, c_sent in zip(baseline_sents, current_sents):
                if b_sent != c_sent:
                    key_changes.append(f"Changed: '{b_sent}' → '{c_sent}'")
            
            # Create and store result
            result = AnalysisResult(
                input_text=input_text,
                baseline_output=baseline,
                current_output=current,
                similarity_score=similarity,
                llm_grade=grade,
                llm_feedback=feedback,
                key_changes=key_changes
            )
            self.analysis_results.append(result)
            return result
            
        except Exception as e:
            raise AnalysisError(f"Error analyzing test case: {str(e)}")

    def get_analysis_text(self, index: int) -> str:
        """Get formatted analysis text for a specific result."""
        if not 0 <= index < len(self.analysis_results):
            return "No analysis available for this test case."
            
        result = self.analysis_results[index]
        analysis_text = [
            f"Overall Similarity: {result.similarity_score:.2f}",
            "\nKey Changes:"
        ]
        
        if result.key_changes:
            for change in result.key_changes:
                analysis_text.append(f"• {change}")
        else:
            analysis_text.append("No significant changes detected.")
            
        return "\n".join(analysis_text)

    def get_feedback_text(self, index: int) -> str:
        """Get feedback text for a specific result."""
        if not 0 <= index < len(self.analysis_results):
            return "No feedback available for this test case."
        
        return self.analysis_results[index].llm_feedback

    def clear_history(self):
        """Clear analysis history."""
        self.analysis_results.clear()