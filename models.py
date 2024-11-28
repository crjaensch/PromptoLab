# prompt_nanny/models.py
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
    content: str
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
    input_text: str
    baseline_output: Optional[str] = None
    current_output: Optional[str] = None

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

@dataclass
class TestSet:
    name: str
    cases: List[TestCase]
    baseline_model: Optional[str] = None
    baseline_frozen: bool = False
    created_at: datetime = datetime.now()

    def to_dict(self):
        return {
            "name": self.name,
            "cases": [case.to_dict() for case in self.cases],
            "baseline_model": self.baseline_model,
            "baseline_frozen": self.baseline_frozen,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict):
        data["cases"] = [TestCase.from_dict(case) for case in data["cases"]]
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)