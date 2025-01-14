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

from output_analyzer import OutputAnalyzer, AnalysisResult, AnalysisError, LLMError, SimilarityError, AsyncAnalyzer

class TestOutputAnalyzer(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        # Create QApplication instance for the test
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def setUp(self):
        self.analyzer = OutputAnalyzer()
        
    @patch('output_analyzer.nltk')
    async def test_init(self, mock_nltk):
        # Test that NLTK resources are checked/downloaded during initialization
        analyzer = OutputAnalyzer()
        mock_nltk.data.find.assert_called_once_with('tokenizers/punkt')
        self.assertEqual(analyzer.analysis_results, [])

    async def test_create_async_analyzer(self):
        """Test that create_async_analyzer returns a properly initialized AsyncAnalyzer instance."""
        async_analyzer = self.analyzer.create_async_analyzer()
        
        # Check instance type
        self.assertIsInstance(async_analyzer, AsyncAnalyzer)
        self.assertIsInstance(async_analyzer, QObject)
        
        # Check initial state
        self.assertEqual(async_analyzer.output_analyzer, self.analyzer)
        self.assertIsNone(async_analyzer.current_runner)
        self.assertEqual(async_analyzer.pending_embeddings, [])
        self.assertIsNone(async_analyzer.baseline_embedding)
        self.assertIsNone(async_analyzer.current_embedding)
        self.assertIsNone(async_analyzer.grade)
        self.assertIsNone(async_analyzer.feedback)

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
        
        expected_text = """Semantic Similarity Analysis:
• Overall Similarity Score: 0.85

Note: Using overall semantic similarity for comparison"""
        
        actual_text = self.analyzer.get_analysis_text(0)
        self.assertEqual(actual_text.rstrip(), expected_text.rstrip())

    def test_get_feedback_text(self):
        # Test with no results
        self.assertEqual(self.analyzer.get_feedback_text(0), "No feedback available")
        
        # Add a mock result and test
        result = AnalysisResult(
            input_text="test",
            baseline_output="baseline",
            current_output="current",
            similarity_score=0.85,
            llm_grade="A",
            llm_feedback="Good feedback",
            key_changes=[]
        )
        self.analyzer.analysis_results.append(result)
        
        expected_text = "Grade: A\n---\nGood feedback"
        actual_text = self.analyzer.get_feedback_text(0)
        self.assertEqual(actual_text.rstrip(), expected_text.rstrip())

    def test_clear_history(self):
        # Add a mock result
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
        
        # Clear history
        self.analyzer.clear_history()
        
        # Verify history is empty
        self.assertEqual(len(self.analyzer.analysis_results), 0)

if __name__ == '__main__':
    unittest.main()