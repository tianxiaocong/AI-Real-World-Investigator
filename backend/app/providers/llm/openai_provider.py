import json
import logging
from typing import Optional, Type, TypeVar
import httpx
from pydantic import BaseModel
from app.core.config import settings
from app.providers.llm.base import LLMProvider

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

class OpenAICompatibleProvider(LLMProvider):
    """OpenAI / DeepSeek / Local compatible provider"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or settings.OPENAI_API_KEY or settings.DEEPSEEK_API_KEY
        self.base_url = (base_url or settings.OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/")
        self.model = model or "gpt-4o-mini"

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> str:
        if not self.api_key:
            raise ValueError("API key is not configured for OpenAICompatibleProvider.")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or 4096
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
    ) -> T:
        schema = response_model.model_json_schema()
        structured_prompt = (
            f"{prompt}\n\n"
            f"You MUST return ONLY a valid JSON object conforming exactly to this JSON Schema:\n"
            f"{json.dumps(schema, indent=2)}\n\n"
            f"DO NOT include markdown code blocks. Output ONLY raw JSON."
        )

        raw_text = await self.generate_text(
            prompt=structured_prompt,
            system_prompt=system_prompt,
            temperature=temperature
        )

        clean_json = raw_text.strip().strip("`").removeprefix("json").strip()
        try:
            parsed_dict = json.loads(clean_json)
            return response_model.model_validate(parsed_dict)
        except Exception as e:
            logger.warning(f"OpenAI JSON validation error: {e}. Raw: {raw_text[:200]}")
            repair_prompt = (
                f"Fix the following invalid JSON so it validates against the schema:\n"
                f"Error: {e}\n"
                f"Invalid JSON:\n{clean_json}\n"
                f"Schema:\n{json.dumps(schema, indent=2)}"
            )
            fixed_text = await self.generate_text(prompt=repair_prompt, temperature=0.0)
            fixed_json = fixed_text.strip().strip("`").removeprefix("json").strip()
            return response_model.model_validate(json.loads(fixed_json))

    async def get_embedding(self, text: str) -> list[float]:
        """Fetch embedding from text-embedding-3-small"""
        if not self.api_key:
            return [0.0] * 768
            
        url = f"{self.base_url}/embeddings"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": "text-embedding-3-small", "input": text[:2048]}
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                res = await client.post(url, headers=headers, json=payload)
                res.raise_for_status()
                return res.json()["data"][0]["embedding"]
            except Exception as e:
                logger.warning(f"OpenAI embedding failed: {e}. Fallback to zero vector.")
                return [0.0] * 768
