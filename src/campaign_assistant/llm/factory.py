from __future__ import annotations

import os

from campaign_assistant.config import load_local_env
from campaign_assistant.llm.base import LLMClient
from campaign_assistant.llm.mock_client import MockLLMClient
from campaign_assistant.llm.ollama_client import OllamaConfig, OllamaLLMClient


def llm_enabled() -> bool:
    load_local_env()
    value = os.getenv("CAMPAIGN_ASSISTANT_LLM_ENABLED", "true").strip().lower()
    return value not in {"0", "false", "no", "off"}


def create_llm_client() -> LLMClient | None:
    """
    Create the configured LLM client.

    The app must work even when this returns None.
    """
    load_local_env()

    if not llm_enabled():
        return None

    provider = os.getenv("CAMPAIGN_ASSISTANT_LLM_PROVIDER", "ollama").strip().lower()

    if provider == "mock":
        return MockLLMClient(
            model=os.getenv("CAMPAIGN_ASSISTANT_LLM_MODEL", "mock-model"),
            response_text=os.getenv("CAMPAIGN_ASSISTANT_MOCK_LLM_RESPONSE", "Mock LLM response."),
        )

    if provider == "ollama":
        return OllamaLLMClient(
            OllamaConfig(
                model=os.getenv("CAMPAIGN_ASSISTANT_LLM_MODEL", "gemma3:1b"),
                host=os.getenv("CAMPAIGN_ASSISTANT_OLLAMA_HOST", "http://localhost:11434"),
                timeout_seconds=int(os.getenv("CAMPAIGN_ASSISTANT_LLM_TIMEOUT", "120")),
            )
        )

    return None
