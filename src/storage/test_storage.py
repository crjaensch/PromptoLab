from pathlib import Path
import sys
import json
from typing import Optional, List

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.storage.models import TestSet

class TestSetStorage:
    def __init__(self, base_dir: str = "test_sets"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

    def save_test_set(self, test_set: TestSet):
        file_path = self.base_dir / f"{test_set.name}.jsonl"
        with file_path.open('w') as f:
            json.dump(test_set.to_dict(), f, indent=2)

    def load_test_set(self, name: str) -> Optional[TestSet]:
        file_path = self.base_dir / f"{name}.jsonl"
        if not file_path.exists():
            return None
        with file_path.open('r') as f:
            data = json.load(f)
            return TestSet.from_dict(data)

    def get_all_test_sets(self) -> List[str]:
        return [f.stem for f in self.base_dir.glob("*.jsonl")]