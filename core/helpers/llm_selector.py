import os
from typing import Any, List, Optional


SUPPORTED_OPENAI = {
    "gpt-4.1-nano",
    "gpt-4.1-mini",
    "gpt-4.1",
}

SUPPORTED_GEMINI = {
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
}


def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    val = os.getenv(key)
    return val if isinstance(val, str) and val.strip() else default


def _resolve_model(role: str, model: Optional[str], default_model: Optional[str]) -> str:
    # Priority: explicit argument > ROLE_MODEL env > LLM_DEFAULT_MODEL > hard default
    hard_default = "gemini-2.5-flash-lite"
    candidate = model or _env(f"{role.upper()}_MODEL") or _env("LLM_DEFAULT_MODEL") or default_model or hard_default
    return candidate


def get_chat_model(*, role: str, model: Optional[str] = None, callbacks: Optional[List[Any]] = None, temperature: float = 0.0):
    """Return a configured LangChain Chat model for the given role.

    role: one of {router, domain, synth}; used for env override lookup.
    model: optional explicit model name; else resolved from env with default to gemini-2.5-flash-lite.
    callbacks: optional LangChain callback handlers.
    temperature: float temperature, defaults to 0.
    """
    selected = _resolve_model(role, model, default_model=None)
    cbs = callbacks or []

    # Heuristic: models starting with 'gpt' -> OpenAI; 'gemini' -> Google
    if selected in SUPPORTED_OPENAI or selected.lower().startswith("gpt"):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=selected, temperature=temperature, callbacks=cbs)

    # Default to Gemini (dynamic import to avoid linter/module resolution issues)
    import importlib
    try:
        genai_mod = importlib.import_module("langchain_google_genai")
        ChatGoogleGenerativeAI = getattr(genai_mod, "ChatGoogleGenerativeAI")
    except Exception as e:
        raise RuntimeError(
            "Gemini model selected but 'langchain_google_genai' is not installed. Please install it."
        ) from e
    # Allow explicit API key passthrough via env, but ChatGoogleGenerativeAI also reads GOOGLE_API_KEY
    api_key = _env("GOOGLE_API_KEY") or _env("GEMINI_API_KEY")
    if api_key:
        return ChatGoogleGenerativeAI(model=selected, temperature=temperature, callbacks=cbs, api_key=api_key)
    return ChatGoogleGenerativeAI(model=selected, temperature=temperature, callbacks=cbs)


