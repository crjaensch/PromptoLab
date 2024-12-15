import unittest
from unittest.mock import patch, MagicMock
import numpy as np
from output_analyzer import OutputAnalyzer, AnalysisResult, AnalysisError, LLMError, SimilarityError

class TestOutputAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = OutputAnalyzer()
        # Mock embedding result that would normally come from run_embedding
        self.mock_embedding = [0.1, 0.2, 0.3, 0.4]
        
    @patch('output_analyzer.nltk')
    def test_init(self, mock_nltk):
        # Test that NLTK resources are checked/downloaded during initialization
        analyzer = OutputAnalyzer()
        mock_nltk.data.find.assert_called_once_with('tokenizers/punkt')
        self.assertEqual(analyzer.analysis_results, [])

    @patch('output_analyzer.run_embedding')
    def test_get_text_embedding(self, mock_run_embedding):
        # Setup mock
        mock_run_embedding.return_value = str(self.mock_embedding)
        
        # Test successful embedding
        result = self.analyzer._get_text_embedding("test text")
        self.assertTrue(isinstance(result, np.ndarray))
        self.assertEqual(result.shape, (1, 4))  # 1 row, 4 features
        
        # Test error handling
        mock_run_embedding.side_effect = Exception("API Error")
        with self.assertRaises(SimilarityError):
            self.analyzer._get_text_embedding("test text")

    @patch('output_analyzer.run_embedding')
    @patch('output_analyzer.cosine_similarity')
    def test_compute_semantic_similarity(self, mock_cosine_similarity, mock_run_embedding):
        # Setup mocks
        mock_run_embedding.return_value = str(self.mock_embedding)
        mock_cosine_similarity.return_value = np.array([[0.85]])
        
        # Test successful similarity computation
        similarity = self.analyzer._compute_semantic_similarity("baseline text", "current text")
        self.assertEqual(similarity, 0.85)
        
        # Test error handling
        mock_cosine_similarity.side_effect = Exception("Computation Error")
        with self.assertRaises(SimilarityError):
            self.analyzer._compute_semantic_similarity("baseline text", "current text")

    @patch('output_analyzer.run_llm')
    def test_get_llm_grade(self, mock_run_llm):
        # Setup mock
        mock_response = "Grade: A\n---\nExcellent output"
        mock_run_llm.return_value = mock_response
        
        # Test successful grading
        grade, feedback = self.analyzer._get_llm_grade(
            "user prompt", "baseline text", "current text"
        )
        self.assertEqual(grade, "A")
        self.assertEqual(feedback, "---\nExcellent output")
        
        # Test error handling
        mock_run_llm.side_effect = Exception("LLM Error")
        with self.assertRaises(LLMError):
            self.analyzer._get_llm_grade("user prompt", "baseline text", "current text")

    @patch('output_analyzer.OutputAnalyzer._compute_semantic_similarity')
    @patch('output_analyzer.OutputAnalyzer._get_llm_grade')
    def test_analyze_test_case(self, mock_get_llm_grade, mock_compute_similarity):
        # Setup mocks
        mock_compute_similarity.return_value = 0.85
        mock_get_llm_grade.return_value = ("A", "Excellent output")
        
        # Test successful analysis
        result = self.analyzer.analyze_test_case(
            "input text", "baseline text", "current text"
        )
        
        self.assertIsInstance(result, AnalysisResult)
        self.assertEqual(result.similarity_score, 0.85)
        self.assertEqual(result.llm_grade, "A")
        self.assertEqual(result.llm_feedback, "Excellent output")
        self.assertEqual(len(self.analyzer.analysis_results), 1)
        
        # Test error handling
        mock_compute_similarity.side_effect = Exception("Analysis Error")
        with self.assertRaises(AnalysisError):
            self.analyzer.analyze_test_case("input text", "baseline text", "current text")

    def test_clear_history(self):
        # Add a mock result
        self.analyzer.analysis_results.append(
            AnalysisResult(
                input_text="test",
                baseline_output="baseline",
                current_output="current",
                similarity_score=0.85,
                llm_grade="A",
                llm_feedback="Good",
                key_changes=[]
            )
        )
        
        # Test clearing history
        self.analyzer.clear_history()
        self.assertEqual(len(self.analyzer.analysis_results), 0)

    def test_get_analysis_text(self):
        # Test with no results
        self.assertEqual(self.analyzer.get_analysis_text(0), "No analysis available")
        
        # Add a mock result and test
        result = AnalysisResult(
            input_text="test",
            baseline_output="baseline",
            current_output="current",
            similarity_score=0.85,
            llm_grade="A",
            llm_feedback="Good",
            key_changes=[]
        )
        self.analyzer.analysis_results.append(result)
        
        analysis_text = self.analyzer.get_analysis_text(0)
        self.assertIn("0.85", analysis_text)
        self.assertIn("Semantic Similarity Analysis", analysis_text)

if __name__ == '__main__':
    unittest.main()