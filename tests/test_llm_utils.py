import unittest
from unittest.mock import patch, MagicMock
from PySide6.QtCore import QProcess
import json
import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from llm_utils import run_llm_async, run_embedding_async, get_llm_models, LLMProcessRunner

class TestLLMUtils(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_prompt = "Test prompt"
        self.test_system_prompt = "Test system prompt"
        self.test_model = "gpt-4o-mini"
        
    def test_get_llm_models(self):
        """Test get_llm_models function with mocked subprocess."""
        mock_output = '''openai: gpt-4o-mini (alias1)
gemini: gemini-flash-2.0 (alias2)
ollama: llama3.2'''
        
        with patch('subprocess.run') as mock_run:
            mock_process = MagicMock()
            mock_process.stdout = mock_output
            mock_run.return_value = mock_process
            
            models = get_llm_models()
            
            # Verify the function called subprocess with correct arguments
            mock_run.assert_called_once_with(['llm', 'models'], 
                                           capture_output=True, 
                                           text=True, 
                                           check=True)
            
            # Verify the returned models list
            self.assertEqual(models, ['gpt-4o-mini', 'gemini-flash-2.0', 'llama3.2'])
            
    def test_run_llm_async(self):
        """Test run_llm_async function."""
        runner = run_llm_async(
            user_prompt=self.test_prompt,
            system_prompt=self.test_system_prompt,
            model=self.test_model
        )
        
        # Verify runner is instance of LLMProcessRunner
        self.assertIsInstance(runner, LLMProcessRunner)
        self.assertIsInstance(runner.process, QProcess)
        
    def test_run_embedding_async(self):
        """Test run_embedding_async function."""
        runner = run_embedding_async(
            text=self.test_prompt,
            embed_model="3-large"
        )
        
        # Verify runner is instance of LLMProcessRunner
        self.assertIsInstance(runner, LLMProcessRunner)
        self.assertIsInstance(runner.process, QProcess)
        
    def test_llm_process_runner_success(self):
        """Test LLMProcessRunner with successful execution."""
        runner = LLMProcessRunner()
        test_output = "Test output"
        
        # Create a mock for finished signal
        finished_signal_mock = MagicMock()
        runner.finished.connect(finished_signal_mock)
        
        # Simulate successful process completion
        runner._accumulate_output(test_output)
        runner._handle_finished(0, QProcess.NormalExit)
        
        # Verify signal was emitted with correct output
        finished_signal_mock.assert_called_once_with(test_output.strip())
        
    def test_llm_process_runner_error(self):
        """Test LLMProcessRunner with error condition."""
        runner = LLMProcessRunner()
        
        # Create a mock for error signal
        error_signal_mock = MagicMock()
        runner.error.connect(error_signal_mock)
        
        # Mock process error output
        with patch.object(runner.process, 'readAllStandardError') as mock_stderr:
            mock_stderr.return_value.data.return_value = b"Test error"
            
            # Simulate process failure
            runner._handle_finished(1, QProcess.CrashExit)
            
            # Verify error signal was emitted with correct message
            error_signal_mock.assert_called_once_with("LLM execution failed: Test error")

if __name__ == '__main__':
    unittest.main()
