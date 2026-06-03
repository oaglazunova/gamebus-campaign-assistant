from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from campaign_assistant.llm.base import LLMResponse


@dataclass
class OllamaConfig:
    model: str = "gemma3:1b"
    host: str = "http://localhost:11434"
    timeout_seconds: int = 120


class OllamaLLMClient:
    provider = "ollama"

    def __init__(self, config: OllamaConfig | None = None):
        self.config = config or OllamaConfig()
        self.model = self.config.model

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> LLMResponse:
        url = self.config.host.rstrip("/") + "/api/chat"

        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.config.timeout_seconds,
            ) as response:
                raw = response.read().decode("utf-8")
                data = json.loads(raw)


        except urllib.error.HTTPError as exc:
            error_body = ""
            try:
                error_body = exc.read().decode("utf-8")
            except Exception:
                pass

            guidance = ""
            if exc.code == 404 and "not found" in error_body.lower():
                guidance = (
                    f" The configured model `{self.config.model}` is not available locally. "
                    f"Run `ollama pull {self.config.model}` or set "
                    "`CAMPAIGN_ASSISTANT_LLM_MODEL` to a model you already have."
                )

            return LLMResponse(
                text="",
                provider=self.provider,
                model=self.config.model,
                available=False,
                error=f"Ollama HTTP error {exc.code}: {error_body or exc.reason}.{guidance}",
            )

        except urllib.error.URLError as exc:
            return LLMResponse(
                text="",
                provider=self.provider,
                model=self.config.model,
                available=False,
                error=(
                    "Could not connect to Ollama. Make sure Ollama is running "
                    f"at {self.config.host}. Details: {exc.reason}"
                ),
            )

        except TimeoutError:
            return LLMResponse(
                text="",
                provider=self.provider,
                model=self.config.model,
                available=False,
                error="Ollama request timed out.",
            )

        except Exception as exc:
            return LLMResponse(
                text="",
                provider=self.provider,
                model=self.config.model,
                available=False,
                error=f"Ollama request failed: {exc}",
            )

        text = ""
        message = data.get("message")
        if isinstance(message, dict):
            text = str(message.get("content") or "").strip()

        if not text:
            text = str(data.get("response") or "").strip()

        return LLMResponse(
            text=text,
            provider=self.provider,
            model=self.config.model,
            available=True,
            error=None,
        )
