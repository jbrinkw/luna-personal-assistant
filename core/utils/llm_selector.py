"""LLM selector module for Luna.

Provides a simple interface to get chat models with default gpt-4.1 configuration.
Future versions will support multiple models and tiers.
"""
import os
from typing import Optional, Any

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def get_chat_model(
    role: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.0,
    callbacks: Optional[list] = None,
    **kwargs: Any
) -> Any:
    """Get a chat model instance.
    
    Args:
        role: Role hint (domain, router, synth) - currently unused
        model: Model name override, defaults to gpt-4.1
        temperature: Model temperature
        callbacks: List of callbacks
        **kwargs: Additional arguments passed to the model
        
    Returns:
        LangChain chat model instance
    """
    # Default to gpt-4.1 as specified
    model_name = model or os.getenv('LLM_DEFAULT_MODEL', 'gpt-4.1')
    
    # Import based on model provider
    if 'gpt' in model_name.lower() or 'o1' in model_name.lower():
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            callbacks=callbacks,
            **kwargs
        )
    elif 'claude' in model_name.lower():
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model_name,
            temperature=temperature,
            callbacks=callbacks,
            **kwargs
        )
    else:
        # Default to OpenAI
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            callbacks=callbacks,
            **kwargs
        )


def get_default_model() -> str:
    """Get the default model name."""
    return os.getenv('LLM_DEFAULT_MODEL', 'gpt-4.1')

