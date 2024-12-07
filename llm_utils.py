# prompt_nanny/llm_utils.py
import subprocess
from typing import Optional, Dict
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_llm(user_prompt: str, system_prompt: Optional[str] = None, model: str = "gpt-4o-mini") -> str:
    """Execute prompt using llm CLI tool."""
    try:
        cmd = ["llm", "-m", model]
        if system_prompt is not None:
            # Escape any single quotes in the system prompt
            escaped_system_prompt = system_prompt.replace("'", "'\"'\"'")
            cmd.extend(["-s", "'" + escaped_system_prompt + "'"])
        
        # Log the command and input
        logger.info("Running LLM command: %s", " ".join(cmd))
        logger.info("User prompt: %s", user_prompt)
        if system_prompt:
            logger.info("System prompt: %s", system_prompt)
            
        result = subprocess.run(
            cmd,
            input=user_prompt,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        error_msg = f"LLM execution failed: {e.stderr}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

def run_embedding(text: str, embed_model: str = "3-large") -> str:
    """Execute text using llm CLI tool."""
    try:
        cmd = ["llm", "embed", "-m", embed_model, "-c", text]
        
        # Log the command and input
        logger.info("Running LLM command: %s", " ".join(cmd))
        logger.info("Text: %s", text)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        error_msg = f"LLM execution failed: {e.stderr}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)    
