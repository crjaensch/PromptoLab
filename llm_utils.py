# prompt_nanny/llm_utils.py
import subprocess
from typing import Optional, Dict
import json

def run_llm(prompt: str, model: str = "gpt-4o-mini") -> str:
    """Execute prompt using llm CLI tool."""
    try:
        result = subprocess.run(
            ["llm", "-m", model],
            input=prompt,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"LLM execution failed: {e.stderr}")
