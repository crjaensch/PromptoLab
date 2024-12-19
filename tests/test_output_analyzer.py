import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import numpy as np
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication
import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from output_analyzer import OutputAnalyzer, AnalysisResult, AnalysisError, LLMError, SimilarityError

class TestOutputAnalyzer(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        # Create QApplication instance for the test
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def setUp(self):
        self.analyzer = OutputAnalyzer()
        # Mock embedding result that would normally come from run_embedding
        self.mock_embedding = [0.1, 0.2, 0.3, 0.4]
        
    @patch('output_analyzer.nltk')
    async def test_init(self, mock_nltk):
        # Test that NLTK resources are checked/downloaded during initialization
        analyzer = OutputAnalyzer()
        mock_nltk.data.find.assert_called_once_with('tokenizers/punkt')
        self.assertEqual(analyzer.analysis_results, [])

    @patch('output_analyzer.run_embedding_async')
    async def test_get_text_embedding(self, mock_run_embedding_async):
        # Setup mock runner
        mock_runner = AsyncMock()
        mock_runner.wait_for_output.return_value = str(self.mock_embedding)
        mock_run_embedding_async.return_value = mock_runner
        
        # Test successful embedding
        result = await self.analyzer._get_text_embedding("test text")
        self.assertTrue(np.array_equal(result, np.array([self.mock_embedding])))
        
        # Test error handling
        mock_runner.wait_for_output.side_effect = Exception("API Error")
        with self.assertRaises(SimilarityError):
            await self.analyzer._get_text_embedding("test text")

    @patch('output_analyzer.run_embedding_async')
    @patch('output_analyzer.cosine_similarity')
    async def test_compute_semantic_similarity(self, mock_cosine_similarity, mock_run_embedding_async):
        # Setup mock runner
        mock_runner = AsyncMock()
        mock_runner.wait_for_output.return_value = str(self.mock_embedding)
        mock_run_embedding_async.return_value = mock_runner
        mock_cosine_similarity.return_value = np.array([[0.85]])
        
        # Test successful similarity computation
        similarity = await self.analyzer._compute_semantic_similarity("baseline text", "current text")
        self.assertEqual(similarity, 0.85)
        
        # Test error handling
        mock_cosine_similarity.side_effect = Exception("Computation Error")
        with self.assertRaises(SimilarityError):
            await self.analyzer._compute_semantic_similarity("baseline text", "current text")

    @patch('output_analyzer.run_llm_async')
    async def test_get_llm_grade(self, mock_run_llm_async):
        # Setup mock runner
        mock_runner = AsyncMock()
        mock_response = "Grade: A\n---\nExcellent output"
        mock_runner.wait_for_output.return_value = mock_response
        mock_run_llm_async.return_value = mock_runner
        
        # Test successful grading
        grade, feedback = await self.analyzer._get_llm_grade(
            "user prompt", "baseline text", "current text"
        )
        self.assertEqual(grade, "A")
        self.assertEqual(feedback, "---\nExcellent output")
        
        # Test error handling
        mock_runner.wait_for_output.side_effect = Exception("LLM Error")
        with self.assertRaises(LLMError):
            await self.analyzer._get_llm_grade("user prompt", "baseline text", "current text")

    @patch('output_analyzer.OutputAnalyzer._compute_semantic_similarity')
    @patch('output_analyzer.OutputAnalyzer._get_llm_grade')
    async def test_analyze_test_case(self, mock_get_llm_grade, mock_compute_similarity):
        # Setup mocks
        mock_compute_similarity.return_value = 0.85
        mock_get_llm_grade.return_value = ("A", "Excellent output")
        
        # Test successful analysis
        result = await self.analyzer.analyze_test_case(
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
            await self.analyzer.analyze_test_case("input text", "baseline text", "current text")

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
            key_changes=["Change 1", "Change 2"]
        )
        self.analyzer.analysis_results.append(result)
        
        expected_text = """Semantic Similarity Analysis
------------------------
Overall Similarity Score: 0.85

Key Changes:
- Change 1
- Change 2"""
        
        actual_text = self.analyzer.get_analysis_text(0)
        self.assertEqual(actual_text.rstrip(), expected_text.rstrip())

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

if __name__ == '__main__':
    unittest.main()