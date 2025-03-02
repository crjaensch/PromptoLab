"""
A module that provides methods for usage with the llm command line tool.
Requires Python 3.10 or above and the 'llm' command line tool installed.

Public methods:
1. run_llm(model_name: str, user_prompt: str, 
   system_prompt: Optional[str] = None,
   model_params: Optional[Dict[str, Any]] = None) -> str

2. run_embed(embed_model: str, text: str) -> List[float]

3. get_models() -> List[str]
"""

import json
import logging
import subprocess
from typing import Optional, List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default models, if the command "llm models" fails to run successfully.
DEFAULT_MODELS = [
    "Undefined",
]

class LLMError(Exception):
    """Base class for LLM-related errors."""
    pass

class LLMQuotaError(LLMError):
    """Raised when the LLM API quota is exhausted."""
    pass

class LLMCapabilityError(LLMError):
    """Raised when the model doesn't support requested features."""
    pass

class LLMConnectionError(LLMError):
    """Raised when there are connection/network issues."""
    pass

def _build_llm_command(model: str, system_prompt: Optional[str] = None,
                    model_params: Optional[Dict[str, Any]] = None) -> list[str]:
    """Build the LLM command with all necessary parameters."""
    cmd = ["llm", "-m", model]
    
    if model_params:
        for key, value in model_params.items():
            if value is not None:
                cmd.extend(["-o", key, str(value)])
        
    if system_prompt is not None:
        # Escape any single quotes in the system prompt
        escaped_system_prompt = system_prompt.replace("'", "'\"'\"'")
        cmd.extend(["-s", "'" + escaped_system_prompt + "'"])
        
    return cmd

def run_llm(
    model_name: str,
    user_prompt: str,
    system_prompt: Optional[str] = None,
    model_params: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Run a completion call using the llm command line tool.
    
    Args:
        model_name: The name of the model to use (e.g. 'gpt-4o-mini')
        user_prompt: The user prompt text
        system_prompt: Optional system prompt / context
        model_params: Optional dictionary of additional model parameters
        
    Returns:
        The generated text from the model
        
    Raises:
        LLMQuotaError: When API quota is exhausted
        LLMCapabilityError: When model doesn't support requested features
        LLMConnectionError: When there are connection issues
        LLMError: For other LLM-related errors
    """
    cmd = _build_llm_command(model_name, system_prompt, model_params)
    
    # Log the command and input
    logger.info("Running LLM command: %s", " ".join(cmd))
    logger.info("User prompt: %s", user_prompt)
    if system_prompt:
        logger.info("System prompt: %s", system_prompt)

    # Create subprocess and pipe the user prompt to it
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    stdout, stderr = process.communicate(user_prompt.encode())
    
    if process.returncode != 0:
        error_msg = stderr.decode().strip()
        
        if "Resource has been exhausted" in error_msg:
            raise LLMQuotaError("API quota exceeded. Please try again later or check your subscription limits.")
        elif "Model does not support system prompts" in error_msg:
            raise LLMCapabilityError(f"Model '{model_name}' doesn't support system prompts. Try a different model or remove the system prompt.")
        elif any(term in error_msg.lower() for term in ["connection", "timeout", "network"]):
            raise LLMConnectionError("Connection error. Please check your internet connection and try again.")
        else:
            raise LLMError(f"LLM command failed: {error_msg}")
    
    return stdout.decode().strip()

def run_embed(embed_model: str, text: str) -> List[float]:
    """
    Get an embedding vector for the given text using the llm command line tool.

    :param embed_model: The name of the embedding model.
    :param text: The text to be embedded.
    :return: A list of floats representing the embedding vector.
    """
    # Escape any single quotes in the text
    escaped_text = text.replace("'", "'\"'\"'")
    cmd = ["llm", "embed", "-m", embed_model, "-c", "'" + escaped_text + "'"]
    
    # Log the command and input
    logger.info("Running LLM embed command: %s", " ".join(cmd))
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    stdout, stderr = process.communicate()
    
    # Log raw output for debugging (truncate to 70 chars)
    logger.info("Embed command stdout: %s", (stdout.decode()[:70] + "...") if stdout else "None")
    logger.info("Embed command stderr: %s", (stderr.decode()[:70] + "...") if stderr else "None")
    
    if process.returncode != 0:
        error_msg = stderr.decode().strip()
        raise RuntimeError(f"LLM embedding failed: {error_msg}")
    
    # Parse the embedding output (assuming it's JSON formatted)
    try:
        stdout_str = stdout.decode().strip()
        # Show first 40 and last 40 chars if string is longer than 80 chars
        if len(stdout_str) > 80:
            truncated = f"{stdout_str[:40]}...{stdout_str[-40:]}"
        else:
            truncated = stdout_str
        logger.info("Trying to parse JSON: %s", truncated)
        embedding_data = json.loads(stdout_str)
        return embedding_data  # Return raw list
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse embedding output: {e}")

def get_models() -> List[str]:
    """
    Return a list of models supported by this module.

    :return: A list of model names.
    """
    try:
        result = subprocess.run(['llm', 'models'], 
                              capture_output=True, 
                              text=True, 
                              check=True)
        
        models = []
        for line in result.stdout.splitlines():
            if ':' in line:  # Only process lines that have a colon
                # Get the part after the first colon
                model_part = line.split(':', 1)[1].strip()
                # If there are aliases (indicated by parentheses), only take the part before them
                if '(' in model_part:
                    model_part = model_part.split('(')[0].strip()
                models.append(model_part)
                
        return models
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running 'llm models': {e}")
        return DEFAULT_MODELS
    except Exception as e:
        logger.error(f"Unexpected error getting LLM models: {e}")
        return DEFAULT_MODELS
