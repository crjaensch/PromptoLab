import subprocess
from typing import Optional, Dict
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_llm(user_prompt: str, system_prompt: Optional[str] = None, model: str = "gpt-4o-mini",
          temperature: Optional[float] = None, max_tokens: Optional[int] = None, top_p: Optional[float] = None) -> str:
    """Execute prompt using llm CLI tool."""
    try:
        cmd = ["llm", "-m", model]
        
        # Only add optional parameters if they're provided
        if temperature is not None:
            cmd.extend(["-o", "temperature", str(temperature)])
        
        if max_tokens is not None:
            cmd.extend(["-o", "max_tokens", str(max_tokens)])
            
        if top_p is not None:
            cmd.extend(["-o", "top_p", str(top_p)])
            
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
        # Escape any single quotes in the text and wrap in single quotes for llm CLI
        escaped_text = text.replace("'", "'\"'\"'")
        cmd = ["llm", "embed", "-m", embed_model, "-c", "'" + escaped_text + "'"]
        
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

def get_llm_models() -> list[str]:
    """Get list of available LLM models by running 'llm models' command.
    
    Returns:
        list[str]: List of model names, stripped of aliases and descriptions
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
        return []
    except Exception as e:
        logger.error(f"Unexpected error getting LLM models: {e}")
        return []
