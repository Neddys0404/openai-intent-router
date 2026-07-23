from __future__ import annotations

import re
from pathlib import Path

from llm.client import UpstreamClient


class ImagePromptRefiner:
    """Refines image prompts through a configured chat model."""

    def __init__(self, config: dict[str, object], client: UpstreamClient | None = None):
        self.config = config
        self.client = client or UpstreamClient()

    def _system_prompt(self) -> str:
        prompt_file = self.config.get("system_prompt_file")
        if not isinstance(prompt_file, str) or not prompt_file:
            raise ValueError("prompt_refiner.system_prompt_file must be configured.")
        path = Path(prompt_file).expanduser()
        if not path.is_absolute():
            path = Path(__file__).parents[1] / path
        try:
            return path.read_text(encoding="utf-8")
        except OSError as error:
            raise RuntimeError(f"Unable to read prompt refiner system prompt: {path}") from error

    async def refine(self, endpoint: str, prompt: str, timeout: float, model_name: str | None = None) -> str:
        payload = {
            "model": model_name or self.config.get("model", "chat"),
            "messages": [
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "stream": False,
        }
        response = await self.client.completion(endpoint, payload, timeout)
        try:
            refined = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError("Prompt refiner returned an invalid response.") from error
        if not isinstance(refined, str) or not refined.strip():
            raise RuntimeError("Prompt refiner returned an empty prompt.")
        refined = refined.strip().strip("\"'")
        refined = re.sub(r"^```(?:\w+)?\s*|\s*```$", "", refined, flags=re.IGNORECASE).strip()
        return re.sub(r"^(?:prompt|final prompt)\s*:\s*", "", refined, flags=re.IGNORECASE).strip()
