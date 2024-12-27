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

    async def test_start_analysis(self):
        """Test the start_analysis method of AsyncAnalyzer."""
        # Create async analyzer instance
        async_analyzer = self.analyzer.create_async_analyzer()
        
        # Mock the _get_embeddings_async method to verify it's called
        async_analyzer._get_embeddings_async = MagicMock()
        
        # Test data
        input_text = "test input"
        baseline = "baseline output"
        current = "current output"
        model = "gpt-4"
        
        # Call start_analysis
        async_analyzer.start_analysis(input_text, baseline, current, model)
        
        # Verify instance variables are set correctly
        self.assertEqual(async_analyzer.input_text, input_text)
        self.assertEqual(async_analyzer.baseline, baseline)
        self.assertEqual(async_analyzer.current, current)
        self.assertEqual(async_analyzer.model, model)
        
        # Verify _get_embeddings_async was called
        async_analyzer._get_embeddings_async.assert_called_once()
        
        # Test with default model parameter
        async_analyzer._get_embeddings_async.reset_mock()
        async_analyzer.start_analysis(input_text, baseline, current)
        self.assertEqual(async_analyzer.model, "gpt-4o")  # Check default model value
        async_analyzer._get_embeddings_async.assert_called_once()
        
        # Test error handling
        async_analyzer._get_embeddings_async.side_effect = Exception("Test error")
        async_analyzer.error = MagicMock()  # Mock error signal
        with self.assertRaises(Exception):
            async_analyzer.start_analysis(input_text, baseline, current)

    async def test_handle_baseline_embedding(self):
        """Test the _handle_baseline_embedding method of AsyncAnalyzer."""
        async_analyzer = self.analyzer.create_async_analyzer()
        
        # Mock the _check_completion method
        async_analyzer._check_completion = MagicMock()
        
        # Test successful embedding processing
        test_embedding = [0.1, 0.2, 0.3]
        async_analyzer._handle_baseline_embedding(str(test_embedding))
        
        # Verify embedding was properly converted to numpy array
        self.assertTrue(isinstance(async_analyzer.baseline_embedding, np.ndarray))
        np.testing.assert_array_equal(
            async_analyzer.baseline_embedding,
            np.array([test_embedding])
        )
        
        # Verify _check_completion was called
        async_analyzer._check_completion.assert_called_once()
        
        # Test error handling with invalid embedding format
        async_analyzer.error = MagicMock()  # Mock error signal
        async_analyzer._handle_baseline_embedding("invalid_embedding")
        
        # Verify error signal was emitted with correct message
        async_analyzer.error.emit.assert_called_once()
        error_msg = async_analyzer.error.emit.call_args[0][0]
        self.assertTrue("Error processing baseline embedding" in error_msg)

    async def test_check_completion(self):
        """Test the _check_completion method of AsyncAnalyzer."""
        async_analyzer = self.analyzer.create_async_analyzer()
        
        # Mock cosine_similarity and _get_llm_grade
        with patch('output_analyzer.cosine_similarity') as mock_cosine, \
             patch.object(async_analyzer, '_get_llm_grade') as mock_llm_grade:
            
            # Setup mock similarity result
            mock_cosine.return_value = np.array([[0.975]])
            
            # Test when no embeddings are ready
            async_analyzer._check_completion()
            mock_cosine.assert_not_called()
            mock_llm_grade.assert_not_called()
            
            # Test when only baseline embedding is ready
            async_analyzer.baseline_embedding = np.array([[0.1, 0.2, 0.3]])
            async_analyzer._check_completion()
            mock_cosine.assert_not_called()
            mock_llm_grade.assert_not_called()
            
            # Test when only current embedding is ready
            async_analyzer.baseline_embedding = None
            async_analyzer.current_embedding = np.array([[0.4, 0.5, 0.6]])
            async_analyzer._check_completion()
            mock_cosine.assert_not_called()
            mock_llm_grade.assert_not_called()
            
            # Test when both embeddings are ready
            async_analyzer.baseline_embedding = np.array([[0.1, 0.2, 0.3]])
            async_analyzer.current_embedding = np.array([[0.4, 0.5, 0.6]])
            async_analyzer._check_completion()
            
            # Verify similarity was calculated
            mock_cosine.assert_called_once_with(
                async_analyzer.baseline_embedding,
                async_analyzer.current_embedding
            )
            
            # Verify LLM grading was started with correct similarity score
            mock_llm_grade.assert_called_once_with(0.975)

    async def test_handle_grade_result(self):
        """Test the _handle_grade_result method of AsyncAnalyzer."""
        async_analyzer = self.analyzer.create_async_analyzer()
        
        # Set up test data
        async_analyzer.input_text = "test input"
        async_analyzer.baseline = "baseline output"
        async_analyzer.current = "current output"
        similarity = 0.975
        
        # Mock the finished signal
        async_analyzer.finished = MagicMock()
        
        # Test successful grade processing
        test_result = "Grade: A\nGreat job!\nExcellent performance"
        async_analyzer._handle_grade_result(test_result, similarity)
        
        # Verify analysis result was created correctly
        self.assertEqual(len(self.analyzer.analysis_results), 1)
        result = self.analyzer.analysis_results[0]
        
        # Verify all fields
        self.assertEqual(result.input_text, "test input")
        self.assertEqual(result.baseline_output, "baseline output")
        self.assertEqual(result.current_output, "current output")
        self.assertEqual(result.similarity_score, similarity)
        self.assertEqual(result.llm_grade, "A")
        self.assertEqual(result.llm_feedback, "Great job!\nExcellent performance")
        self.assertEqual(len(result.key_changes), 2)
        self.assertTrue("semantic similarity" in result.key_changes[0])
        
        # Verify finished signal was emitted with correct result
        async_analyzer.finished.emit.assert_called_once_with(result)
        
        # Test error handling with invalid grade format
        async_analyzer.error = MagicMock()  # Mock error signal
        async_analyzer._handle_grade_result(None, similarity)
        async_analyzer.error.emit.assert_called_once()
        error_msg = async_analyzer.error.emit.call_args[0][0]
        self.assertTrue("Error processing grade result" in error_msg)

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