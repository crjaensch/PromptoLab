import unittest
from datetime import datetime
import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.storage.models import Prompt, PromptType, TestCase, TestSet

class TestPromptModel(unittest.TestCase):
    def setUp(self):
        self.test_datetime = datetime(2024, 12, 14, 21, 47, 5)
        self.test_prompt = Prompt(
            title="Test Prompt",
            user_prompt="Hello, world!",
            system_prompt="You are a helpful assistant.",
            prompt_type=PromptType.SIMPLE,
            created_at=self.test_datetime,
            updated_at=self.test_datetime,
            id="test_prompt_1"
        )

    def test_prompt_creation(self):
        self.assertEqual(self.test_prompt.title, "Test Prompt")
        self.assertEqual(self.test_prompt.user_prompt, "Hello, world!")
        self.assertEqual(self.test_prompt.system_prompt, "You are a helpful assistant.")
        self.assertEqual(self.test_prompt.prompt_type, PromptType.SIMPLE)
        self.assertEqual(self.test_prompt.id, "test_prompt_1")

    def test_prompt_to_dict(self):
        prompt_dict = self.test_prompt.to_dict()
        self.assertEqual(prompt_dict['title'], "Test Prompt")
        self.assertEqual(prompt_dict['prompt_type'], "Simple Prompt")
        self.assertEqual(prompt_dict['created_at'], self.test_datetime.isoformat())
        self.assertEqual(prompt_dict['updated_at'], self.test_datetime.isoformat())

    def test_prompt_from_dict(self):
        prompt_dict = {
            'title': "Test Prompt",
            'user_prompt': "Hello, world!",
            'system_prompt': "You are a helpful assistant.",
            'prompt_type': "Simple Prompt",
            'created_at': self.test_datetime.isoformat(),
            'updated_at': self.test_datetime.isoformat(),
            'id': "test_prompt_1"
        }
        prompt = Prompt.from_dict(prompt_dict)
        self.assertEqual(prompt.title, "Test Prompt")
        self.assertEqual(prompt.prompt_type, PromptType.SIMPLE)
        self.assertEqual(prompt.created_at, self.test_datetime)

class TestTestCaseModel(unittest.TestCase):
    def setUp(self):
        self.test_datetime = datetime(2024, 12, 14, 21, 47, 5)
        self.test_case = TestCase(
            input_text="Test input",
            baseline_output="Expected output",
            current_output="Current output",
            test_id="test_1",
            created_at=self.test_datetime,
            last_run=self.test_datetime
        )

    def test_test_case_creation(self):
        self.assertEqual(self.test_case.input_text, "Test input")
        self.assertEqual(self.test_case.baseline_output, "Expected output")
        self.assertEqual(self.test_case.current_output, "Current output")
        self.assertEqual(self.test_case.test_id, "test_1")

    def test_test_case_to_dict(self):
        case_dict = self.test_case.to_dict()
        self.assertEqual(case_dict['input_text'], "Test input")
        self.assertEqual(case_dict['baseline_output'], "Expected output")
        self.assertEqual(case_dict['created_at'], self.test_datetime.isoformat())
        self.assertEqual(case_dict['last_run'], self.test_datetime.isoformat())

    def test_test_case_from_dict(self):
        case_dict = {
            'input_text': "Test input",
            'baseline_output': "Expected output",
            'current_output': "Current output",
            'test_id': "test_1",
            'created_at': self.test_datetime.isoformat(),
            'last_run': self.test_datetime.isoformat()
        }
        case = TestCase.from_dict(case_dict)
        self.assertEqual(case.input_text, "Test input")
        self.assertEqual(case.baseline_output, "Expected output")
        self.assertEqual(case.created_at, self.test_datetime)

class TestTestSetModel(unittest.TestCase):
    def setUp(self):
        self.test_datetime = datetime(2024, 12, 14, 21, 47, 5)
        self.test_case = TestCase(
            input_text="Test input",
            baseline_output="Expected output",
            test_id="test_1",
            created_at=self.test_datetime
        )
        self.test_set = TestSet(
            name="Test Set 1",
            cases=[self.test_case],
            system_prompt="System prompt",
            baseline_model="gpt-4",
            baseline_frozen=True,
            created_at=self.test_datetime,
            last_modified=self.test_datetime
        )

    def test_test_set_creation(self):
        self.assertEqual(self.test_set.name, "Test Set 1")
        self.assertEqual(len(self.test_set.cases), 1)
        self.assertEqual(self.test_set.system_prompt, "System prompt")
        self.assertEqual(self.test_set.baseline_model, "gpt-4")
        self.assertTrue(self.test_set.baseline_frozen)

    def test_test_set_to_dict(self):
        set_dict = self.test_set.to_dict()
        self.assertEqual(set_dict['name'], "Test Set 1")
        self.assertEqual(len(set_dict['cases']), 1)
        self.assertEqual(set_dict['baseline_model'], "gpt-4")
        self.assertTrue(set_dict['baseline_frozen'])
        self.assertEqual(set_dict['created_at'], self.test_datetime.isoformat())

    def test_test_set_from_dict(self):
        set_dict = {
            'name': "Test Set 1",
            'cases': [self.test_case.to_dict()],
            'system_prompt': "System prompt",
            'baseline_model': "gpt-4",
            'baseline_frozen': True,
            'created_at': self.test_datetime.isoformat(),
            'last_modified': self.test_datetime.isoformat()
        }
        test_set = TestSet.from_dict(set_dict)
        self.assertEqual(test_set.name, "Test Set 1")
        self.assertEqual(len(test_set.cases), 1)
        self.assertEqual(test_set.baseline_model, "gpt-4")
        self.assertTrue(test_set.baseline_frozen)
        self.assertEqual(test_set.created_at, self.test_datetime)

if __name__ == '__main__':
    unittest.main()
