from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path
import json

class PromptType(Enum):
    SIMPLE = "Simple Prompt"
    STRUCTURED = "Structured Prompt"
    TEMPLATE = "Prompt Template"

@dataclass
class Prompt:
    title: str
    user_prompt: str
    system_prompt: Optional[str]
    prompt_type: PromptType
    created_at: datetime
    updated_at: datetime
    id: str  # Using filename as ID

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['prompt_type'] = self.prompt_type.value
        d['created_at'] = self.created_at.isoformat()
        d['updated_at'] = self.updated_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> 'Prompt':
        data['prompt_type'] = PromptType(data['prompt_type'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)

@dataclass
class TestCase:
    input_text: str  # The user prompt/input for this test case
    baseline_output: Optional[str] = None  # Expected/baseline output
    current_output: Optional[str] = None  # Current/test output
    test_id: Optional[str] = None  # Unique identifier for the test case
    created_at: datetime = datetime.now()  # When the test case was created
    last_run: Optional[datetime] = None  # When the test was last executed

    def to_dict(self) -> dict:
        return {
            "input_text": self.input_text,
            "baseline_output": self.baseline_output,
            "current_output": self.current_output,
            "test_id": self.test_id,
            "created_at": self.created_at.isoformat(),
            "last_run": self.last_run.isoformat() if self.last_run else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TestCase':
        if "created_at" in data:
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "last_run" in data and data["last_run"]:
            data["last_run"] = datetime.fromisoformat(data["last_run"])
        return cls(**data)

@dataclass
class TestSet:
    name: str  # Name of the test set
    cases: List[TestCase]  # List of test cases
    system_prompt: Optional[str] = None  # System prompt used for all test cases
    baseline_model: Optional[str] = None  # Model used to generate baseline outputs
    baseline_frozen: bool = False  # Whether baseline outputs are frozen/locked
    created_at: datetime = datetime.now()  # When the test set was created
    last_modified: datetime = datetime.now()  # When the test set was last modified

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "cases": [case.to_dict() for case in self.cases],
            "system_prompt": self.system_prompt,
            "baseline_model": self.baseline_model,
            "baseline_frozen": self.baseline_frozen,
            "created_at": self.created_at.isoformat(),
            "last_modified": self.last_modified.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TestSet':
        data["cases"] = [TestCase.from_dict(case) for case in data["cases"]]
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["last_modified"] = datetime.fromisoformat(data["last_modified"])
        return cls(**data)