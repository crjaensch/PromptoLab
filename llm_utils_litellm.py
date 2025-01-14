# llm_utils_litellm.py
"""
A module that provides asynchronous methods for usage with litellm.
Requires Python 3.10 or above and the 'litellm' library installed.

Public methods:
1. run_llm_async(model_name: str, user_prompt: str, 
   system_prompt: Optional[str] = None,
   model_params: Optional[Dict[str, Any]] = None) -> str

2. run_embed_async(embed_model: str, text: str) -> List[float]

3. get_models() -> List[str]
"""

import asyncio
from functools import partial
from typing import Optional, List, Dict, Any
import litellm
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# You can customize or dynamically generate the supported models below.
SUPPORTED_MODELS = [
    "gpt-4o-mini",
    "gpt-4o",
    "o1-mini",
    "o1-preview",
    "groq/llama-3.1-8b-instant",
    "groq/llama-3.1-70b-versatile",
    "gemini/gemini-2.0-flash-exp",
    "gemini/gemini-1.5-pro",
    "ollama/llama3.2",
    "ollama/llama3.1:8b",
    "ollama/phi4",
    "ollama/olmo2:7b",
    "ollama/falcon3:10b",
    # ... add or remove models as needed
]


async def run_llm_async(
    model_name: str,
    user_prompt: str,
    system_prompt: Optional[str] = None,
    model_params: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Asynchronously run a completion call on the specified LLM model.

    :param model_name: The name of the model to use (e.g. 'gpt-4o-mini').
    :param user_prompt: The user prompt text.
    :param system_prompt: (Optional) A system prompt / context to guide the model.
    :param model_params: (Optional) Dictionary of additional model parameters, if any.
    :return: The generated text from the model.
    """
    messages = []
    if system_prompt is not None:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    if model_params is None:
        model_params = {}

    # Log the request details
    logger.info("Running LiteLLM completion with model: %s", model_name)
    logger.info("User prompt: %s", user_prompt)
    if system_prompt:
        logger.info("System prompt: %s", system_prompt)
    if model_params:
        logger.info("Model parameters: %s", model_params)

    # Because litellm.completion might be blocking,
    # run it in a background thread using run_in_executor.
    loop = asyncio.get_running_loop()
    completion_func = partial(
        litellm.completion,
        model=model_name,
        messages=messages,
        **model_params
    )
    result = await loop.run_in_executor(None, completion_func)

    # Extract the actual response text from the completion result
    if hasattr(result, 'choices') and len(result.choices) > 0:
        response = result.choices[0].message.content
    else:
        logger.error("Unexpected response format from LiteLLM: %s", result)
        raise ValueError("Unexpected response format from LiteLLM")

    return response


async def run_embed_async(embed_model: str, text: str) -> List[float]:
    """
    Asynchronously get an embedding vector for the given text using the specified embed model.

    :param embed_model: The name of the embedding model (e.g. 'text-embedding-ada-002').
    :param text: The text to be embedded.
    :return: A list of floats representing the embedding vector.
    """
    # Log the request details
    logger.info("Running LiteLLM embedding with model: %s", embed_model)
    logger.info("Text to embed: %s", (text[:70] + "...") if text else "None")

    loop = asyncio.get_running_loop()
    embed_func = partial(litellm.embedding, model=embed_model, input=text)
    result = await loop.run_in_executor(None, embed_func)

    # Parse the embedding result (assuming it's an OpenAI EmbeddingResponse object)
    try:
        embedding_vector = result['data'][0]['embedding']
        logger.info(f"Embedding result: {embedding_vector[:3]} ... {embedding_vector[-3:]}")
        return embedding_vector
    except AttributeError as e:
        raise ValueError(f"Unexpected embedding response format from LiteLLM: {e}")


def get_models() -> List[str]:
    """
    Return a list of models supported by this module.

    :return: A list of model names.
    """
    logger.info("Returning supported LiteLLM models")
    return SUPPORTED_MODELS