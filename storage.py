# prompt_nanny/storage.py
import json
from pathlib import Path
import sys
from typing import List, Optional
from datetime import datetime
import uuid
import re
import logging

# Add the project root directory to Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from models import Prompt, PromptType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileStorage:
    def __init__(self, base_dir: str = "prompts"):
        self.base_dir = Path(base_dir)
        self._init_storage()

    def _init_storage(self):
        for prompt_type in PromptType:
            (self.base_dir / prompt_type.name.lower()).mkdir(parents=True, exist_ok=True)

    def _sanitize_title(self, title: str) -> str:
        # Remove special characters and spaces, replace with underscores
        sanitized = re.sub(r'[^\w\s-]', '', title)
        sanitized = re.sub(r'[-\s]+', '_', sanitized)
        return sanitized[:12].strip('_')  # Limit to 12 chars and remove trailing underscores

    def _get_prompt_path(self, prompt: Prompt) -> Path:
        title_prefix = self._sanitize_title(prompt.title) if prompt.title else "untitled"
        return self.base_dir / prompt.prompt_type.name.lower() / f"{title_prefix}_{prompt.id}.json"

    def save_prompt(self, prompt: Prompt, old_type: Optional[PromptType] = None) -> str:
        if not prompt.id:
            prompt.id = str(uuid.uuid4())
            logger.info("Generated new UUID for prompt: %s", prompt.id)
        
        # If we have an old type and it's different from current type, delete the old file
        if old_type and old_type != prompt.prompt_type:
            logger.info("Prompt type changed from %s to %s. Deleting old file.", 
                       old_type.value, prompt.prompt_type.value)
            self.delete_prompt(prompt.id, old_type)
        
        prompt_path = self._get_prompt_path(prompt)
        prompt_dict = prompt.to_dict()
        
        # Log the JSON data being saved
        logger.info("Saving prompt to %s with data:\n%s", 
                   prompt_path, 
                   json.dumps(prompt_dict, indent=2))
        
        with prompt_path.open('w') as f:
            json.dump(prompt_dict, f, indent=2)
        return prompt.id

    def get_prompt(self, prompt_id: str, prompt_type: PromptType) -> Optional[Prompt]:
        type_dir = self.base_dir / prompt_type.name.lower()
        # Look for any file ending with the prompt_id
        matching_files = list(type_dir.glob(f"*_{prompt_id}.json"))
        if not matching_files:
            return None
        
        with matching_files[0].open('r') as f:
            return Prompt.from_dict(json.load(f))

    def get_all_prompts(self) -> List[Prompt]:
        prompts = []
        for prompt_type in PromptType:
            type_dir = self.base_dir / prompt_type.name.lower()
            for prompt_file in type_dir.glob("*.json"):
                with prompt_file.open('r') as f:
                    prompts.append(Prompt.from_dict(json.load(f)))
        return sorted(prompts, key=lambda p: p.title.lower())  # Sort case-insensitive by title

    def delete_prompt(self, prompt_id: str, prompt_type: PromptType):
        type_dir = self.base_dir / prompt_type.name.lower()
        # Look for any file ending with the prompt_id
        matching_files = list(type_dir.glob(f"*_{prompt_id}.json"))
        if matching_files:
            matching_files[0].unlink()