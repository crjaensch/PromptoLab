from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple, NamedTuple
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import nltk
import json
from .llm_utils import run_llm, run_embedding

class DifferenceAnalysis(NamedTuple):
    """Container for difference analysis results."""
    diff_segments: List[Tuple[str, str, float]]  # (baseline, proposed, similarity)
    key_changes: List[str]
    similarity_breakdown: Dict[str, float]

@dataclass
class OutputAnalysis:
    semantic_similarity: float
    llm_grade: str
    detailed_feedback: str
    sentence_similarities: Dict[str, float]

class OutputAnalyzer:
    def __init__(self):
        # Ensure NLTK resources are available
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)

    def _get_sentence_embeddings(self, text: str) -> tuple[np.ndarray, List[str]]:
        """Get embeddings for each sentence in the text."""
        try:
            sentences = nltk.sent_tokenize(text)
        except Exception:
            # Fallback to simple splitting if NLTK fails
            sentences = text.split('. ')
        
        embeddings = []
        for sentence in sentences:
            # Get embedding for each sentence
            embedding_str = run_embedding(sentence, embed_model="3-small")
            # The output is already in the format "[num1, num2, ...]", so we can eval it directly
            embedding = eval(embedding_str)  # Safe here since we know the format is a list of numbers
            embeddings.append(embedding)
        
        return np.array(embeddings), sentences

    def _compute_semantic_similarity(self, baseline: str, current: str) -> tuple[float, Dict[str, float]]:
        """Compute semantic similarity between baseline and current outputs."""
        try:
            # Get embeddings for both texts
            baseline_embeddings, baseline_sentences = self._get_sentence_embeddings(baseline)
            current_embeddings, current_sentences = self._get_sentence_embeddings(current)
            
            # Compute similarity matrix
            similarity_matrix = cosine_similarity(baseline_embeddings, current_embeddings)
            
            # Overall similarity is the mean of the best matches
            overall_similarity = np.mean(np.max(similarity_matrix, axis=1))
            
            # Create sentence-level similarity breakdown
            sentence_similarities = {}
            for i, base_sent in enumerate(baseline_sentences):
                best_match_idx = np.argmax(similarity_matrix[i])
                sentence_similarities[base_sent] = similarity_matrix[i][best_match_idx]
            
            return overall_similarity, sentence_similarities
            
        except Exception as e:
            print(f"Error computing semantic similarity: {str(e)}")
            return 0.0, {}

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
            
            # Parse the result
            grade_line, *feedback_lines = result.split('\n')
            grade = grade_line.replace('Grade:', '').strip()
            feedback = '\n'.join(feedback_lines).strip()
            
            return grade, feedback
            
        except Exception as e:
            print(f"Error getting LLM grade: {str(e)}")
            return "N/A", f"Failed to get LLM evaluation: {str(e)}"

    def analyze_differences(self, baseline: str, proposed: str) -> DifferenceAnalysis:
        """Analyze differences between baseline and proposed outputs."""
        if not baseline and not proposed:
            return DifferenceAnalysis([], [], {"Overall": 0.0})

        try:
            baseline_embeddings, baseline_sents = self._get_sentence_embeddings(baseline)
            proposed_embeddings, proposed_sents = self._get_sentence_embeddings(proposed)

            # Compute similarity matrix
            similarity_matrix = cosine_similarity(baseline_embeddings, proposed_embeddings)
            
            # Overall similarity is the mean of the best matches
            overall_similarity = float(np.mean(np.max(similarity_matrix, axis=1)))
            
            # Create sentence-level similarity breakdown
            similarity_breakdown = {
                "Overall": overall_similarity
            }
            
            diff_segments = []
            key_changes = []
            
            # For each baseline sentence, find the best matching proposed sentence
            for i, (base_sent, similarities) in enumerate(zip(baseline_sents, similarity_matrix)):
                best_match_idx = np.argmax(similarities)
                best_similarity = similarities[best_match_idx]
                prop_sent = proposed_sents[best_match_idx]
                
                similarity_breakdown[f"Segment {i+1}"] = float(best_similarity)
                diff_segments.append((base_sent, prop_sent, best_similarity))
                
                if best_similarity < 0.8:  # Threshold for significant changes
                    key_changes.append(f"Changed: '{base_sent}' → '{prop_sent}' (similarity: {best_similarity:.2f})")
            
            return DifferenceAnalysis(diff_segments, key_changes, similarity_breakdown)
            
        except Exception as e:
            print(f"Error analyzing differences: {str(e)}")
            return DifferenceAnalysis([], [], {"Overall": 0.0})

    def analyze_output(self, user_prompt: str, baseline: str, current: str, model: str = "gpt-4o") -> OutputAnalysis:
        """Analyze the difference between baseline and current outputs using multiple metrics."""
        # Get semantic similarity
        semantic_similarity, sentence_similarities = self._compute_semantic_similarity(baseline, current)
        
        # Get LLM-based grade
        grade, feedback = self._get_llm_grade(user_prompt, baseline, current, model)
        
        return OutputAnalysis(
            semantic_similarity=semantic_similarity,
            llm_grade=grade,
            detailed_feedback=feedback,
            sentence_similarities=sentence_similarities
        )
