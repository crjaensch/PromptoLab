import subprocess
from typing import Optional, Dict
import json
import logging
from PySide6.QtCore import QProcess, QObject, Signal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _build_llm_command(model: str, system_prompt: Optional[str] = None,
                    temperature: Optional[float] = None, max_tokens: Optional[int] = None,
                    top_p: Optional[float] = None) -> list[str]:
    """Build the LLM command with all necessary parameters."""
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
        
    return cmd

class LLMProcessRunner(QObject):
    """Async runner for LLM commands using QProcess."""
    finished = Signal(str)  # Emits result on success
    error = Signal(str)     # Emits error message on failure
    
    def __init__(self):
        super().__init__()
        self.process = QProcess()
        self.process.finished.connect(self._handle_finished)
        self.accumulated_output = ""
        
    def _handle_finished(self, exit_code, exit_status):
        if exit_code == 0:
            self.finished.emit(self.accumulated_output.strip())
        else:
            error = self.process.readAllStandardError().data().decode()
            self.error.emit(f"LLM execution failed: {error}")
            
    def run_async(self, cmd: list, input_text: Optional[str] = None):
        """Run the LLM command asynchronously."""
        self.accumulated_output = ""
        self.process.start(cmd[0], cmd[1:])
        
        if input_text:
            self.process.write(input_text.encode())
            self.process.closeWriteChannel()
            
        # Connect to the readyReadStandardOutput signal to accumulate output
        self.process.readyReadStandardOutput.connect(
            lambda: self._accumulate_output(self.process.readAllStandardOutput().data().decode())
        )
        
    def _accumulate_output(self, output):
        self.accumulated_output += output

def run_llm_async(user_prompt: str, system_prompt: Optional[str] = None, model: str = "gpt-4o-mini",
                temperature: Optional[float] = None, max_tokens: Optional[int] = None,
                top_p: Optional[float] = None) -> LLMProcessRunner:
    """Execute prompt using llm CLI tool asynchronously.
    
    Returns:
        LLMProcessRunner: A runner object with signals for handling completion and errors
    """
    cmd = _build_llm_command(model, system_prompt, temperature, max_tokens, top_p)
    runner = LLMProcessRunner()
    
    # Log the command and input
    logger.info("Running async LLM command: %s", " ".join(cmd))
    logger.info("User prompt: %s", user_prompt)
    if system_prompt:
        logger.info("System prompt: %s", system_prompt)
        
    runner.run_async(cmd, user_prompt)
    return runner

def run_llm(user_prompt: str, system_prompt: Optional[str] = None, model: str = "gpt-4o-mini",
          temperature: Optional[float] = None, max_tokens: Optional[int] = None,
          top_p: Optional[float] = None) -> str:
    """Execute prompt using llm CLI tool synchronously."""
    try:
        cmd = _build_llm_command(model, system_prompt, temperature, max_tokens, top_p)
        
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

def _build_embed_command(text: str, embed_model: str = "3-large") -> list[str]:
    """Build the embedding command with all necessary parameters."""
    # Escape any single quotes in the text and wrap in single quotes for llm CLI
    escaped_text = text.replace("'", "'\"'\"'")
    return ["llm", "embed", "-m", embed_model, "-c", "'" + escaped_text + "'"]

def run_embedding(text: str, embed_model: str = "3-large") -> str:
    """Execute text using llm CLI tool."""
    try:
        cmd = _build_embed_command(text, embed_model)
        
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

def run_embedding_async(text: str, embed_model: str = "3-large") -> LLMProcessRunner:
    """Execute text embedding using llm CLI tool asynchronously."""
    try:
        cmd = _build_embed_command(text, embed_model)
        
        # Log the command and input
        logger.info("Running async LLM embed command: %s", " ".join(cmd))
        logger.info("Text: %s", text)
        
        runner = LLMProcessRunner()
        runner.run_async(cmd)
        return runner
        
    except Exception as e:
        error_msg = f"LLM embedding failed: {str(e)}"
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

def create_llm_runner() -> LLMProcessRunner:
    """Create a new LLM process runner instance."""
    return LLMProcessRunner()
