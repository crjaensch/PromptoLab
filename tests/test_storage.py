import unittest
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from models import Prompt, PromptType, TestCase, TestSet
from storage import FileStorage

class TestFileStorage(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.storage = FileStorage(base_dir=self.temp_dir)
        
        # Create a sample prompt
        self.test_datetime = datetime(2024, 12, 14, 21, 47, 5)
        self.test_prompt = Prompt(
            title="Test Prompt",
            user_prompt="Hello, world!",
            system_prompt="Be helpful",
            prompt_type=PromptType.SIMPLE,
            created_at=self.test_datetime,
            updated_at=self.test_datetime,
            id="test1"
        )

    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.temp_dir)

    def test_save_prompt(self):
        # Save the prompt
        saved_id = self.storage.save_prompt(self.test_prompt)
        self.assertEqual(saved_id, "test1")
        
        # Check if file exists in the correct directory
        prompt_path = self.storage._get_prompt_path(self.test_prompt)
        self.assertTrue(prompt_path.exists())

    def test_get_prompt(self):
        # Save and then load the prompt
        self.storage.save_prompt(self.test_prompt)
        loaded_prompt = self.storage.get_prompt("test1", PromptType.SIMPLE)
        
        # Verify loaded data
        self.assertIsNotNone(loaded_prompt)
        self.assertEqual(loaded_prompt.title, "Test Prompt")
        self.assertEqual(loaded_prompt.user_prompt, "Hello, world!")
        self.assertEqual(loaded_prompt.system_prompt, "Be helpful")
        self.assertEqual(loaded_prompt.prompt_type, PromptType.SIMPLE)

    def test_get_nonexistent_prompt(self):
        # Try to load a non-existent prompt
        loaded_prompt = self.storage.get_prompt("nonexistent", PromptType.SIMPLE)
        self.assertIsNone(loaded_prompt)

    def test_get_all_prompts(self):
        # Save multiple prompts
        self.storage.save_prompt(self.test_prompt)
        
        test_prompt2 = Prompt(
            title="Test Prompt 2",
            user_prompt="Another test",
            system_prompt=None,
            prompt_type=PromptType.SIMPLE,
            created_at=self.test_datetime,
            updated_at=self.test_datetime,
            id="test2"
        )
        self.storage.save_prompt(test_prompt2)
        
        # Get all prompts
        prompts = self.storage.get_all_prompts()
        self.assertEqual(len(prompts), 2)
        titles = [p.title for p in prompts]
        self.assertIn("Test Prompt", titles)
        self.assertIn("Test Prompt 2", titles)

    def test_delete_prompt(self):
        # Save and then delete a prompt
        self.storage.save_prompt(self.test_prompt)
        prompt_path = self.storage._get_prompt_path(self.test_prompt)
        self.assertTrue(prompt_path.exists())
        
        self.storage.delete_prompt("test1", PromptType.SIMPLE)
        self.assertFalse(prompt_path.exists())
        
        # Verify prompt is no longer retrievable
        self.assertIsNone(self.storage.get_prompt("test1", PromptType.SIMPLE))

    def test_prompt_type_change(self):
        # Save prompt with one type
        self.test_prompt.prompt_type = PromptType.SIMPLE
        self.storage.save_prompt(self.test_prompt)
        
        # Change type and save again
        old_type = self.test_prompt.prompt_type
        self.test_prompt.prompt_type = PromptType.TEMPLATE
        self.storage.save_prompt(self.test_prompt, old_type)
        
        # Verify prompt is saved in new location and removed from old
        old_path = self.storage._get_prompt_path(Prompt(**{**self.test_prompt.to_dict(), 'prompt_type': old_type}))
        new_path = self.storage._get_prompt_path(self.test_prompt)
        
        self.assertFalse(old_path.exists())
        self.assertTrue(new_path.exists())
        
        # Verify prompt can be loaded from new location
        loaded_prompt = self.storage.get_prompt("test1", PromptType.TEMPLATE)
        self.assertIsNotNone(loaded_prompt)
        self.assertEqual(loaded_prompt.prompt_type, PromptType.TEMPLATE)

if __name__ == '__main__':
    unittest.main()
