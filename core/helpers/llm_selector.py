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
    "gemini-2.5-pro-thinking",
}

SUPPORTED_ANTHROPIC = {
    "claude-3.5-sonnet",
    "claude-4.0-sonnet",
}


# Simple fixed tier mapping (no overrides for now)
TIER_TO_MODEL = {
    "low": "gpt-4.1",
    "med": "claude-4.0-sonnet",
    "high": "gemini-2.5-pro-thinking",
}


def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    val = os.getenv(key)
    return val if isinstance(val, str) and val.strip() else default


def _resolve_model(role: str, model: Optional[str], default_model: Optional[str]) -> str:
    # Priority: explicit argument > ROLE_MODEL env > LLM_DEFAULT_MODEL > hard default
    hard_default = "gemini-2.5-flash-lite"
    candidate = model or _env(f"{role.upper()}_MODEL") or _env("LLM_DEFAULT_MODEL") or default_model or hard_default
    return candidate


def get_chat_model(*, role: str, model: Optional[str] = None, tier: Optional[str] = None, callbacks: Optional[List[Any]] = None, temperature: float = 0.0):
    """Return a configured LangChain Chat model for the given role.

    role: one of {router, domain, synth}; used for env override lookup.
    model: optional explicit model name (ignored when tier is provided).
    tier: one of {low, med, high}; when provided, selects a fixed model with no overrides.
    callbacks: optional LangChain callback handlers.
    temperature: float temperature, defaults to 0.
    """
    # If tier provided, use tier mapping exclusively (no overrides for now)
    if isinstance(tier, str) and tier.strip():
        key = tier.strip().lower()
        if key not in TIER_TO_MODEL:
            raise ValueError(f"unknown tier '{tier}'; expected one of {list(TIER_TO_MODEL.keys())}")
        selected = TIER_TO_MODEL[key]
    else:
        selected = _resolve_model(role, model, default_model=None)
    cbs = callbacks or []

    # Heuristic: choose provider based on model identifier prefix/allowlist
    if selected in SUPPORTED_OPENAI or selected.lower().startswith("gpt"):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=selected, temperature=temperature, callbacks=cbs)

    if selected in SUPPORTED_ANTHROPIC or selected.lower().startswith("claude"):
        from langchain_anthropic import ChatAnthropic

        api_key = _env("ANTHROPIC_API_KEY")
        kwargs = {"model": selected, "temperature": temperature, "callbacks": cbs}
        if api_key:
            kwargs["anthropic_api_key"] = api_key
        return ChatAnthropic(**kwargs)

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


