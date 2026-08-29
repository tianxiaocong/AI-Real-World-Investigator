import json
import re
import logging
import asyncio
import random
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

        self._client: Optional[httpx.AsyncClient] = None
        self._semaphore = asyncio.Semaphore(2)
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "timeouts": 0,
            "connect_errors": 0,
            "retries": 0,
            "permanent_failures": 0
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=120.0,
                limits=httpx.Limits(max_keepalive_connections=4, max_connections=8)
            )
        return self._client

    async def _invalidate_client(self):
        if self._client and not self._client.is_closed:
            try:
                await self._client.aclose()
            except Exception:
                pass
        self._client = None

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

        self.stats["total_requests"] += 1

        async with self._semaphore:
            for attempt in range(3):
                try:
                    client = await self._get_client()
                    response = await client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    msg = data["choices"][0]["message"]
                    content = msg.get("content") or msg.get("reasoning") or ""
                    return content.strip()
                except httpx.TimeoutException as e:
                    self.stats["timeouts"] += 1
                    self.stats["retries"] += 1
                    await self._invalidate_client()
                    logger.warning(f"HTTPX Timeout: {e}. Retrying {attempt+1}/3 with jitter...")
                    if attempt == 2:
                        self.stats["permanent_failures"] += 1
                        raise
                    jitter = random.uniform(1.0, 2.5)
                    await asyncio.sleep(2.0 * (1.5 ** attempt) + jitter)
                except httpx.RequestError as e:
                    self.stats["connect_errors"] += 1
                    self.stats["retries"] += 1
                    await self._invalidate_client()
                    logger.warning(f"HTTPX RequestError: {type(e).__name__} - {e}. Reconnecting & Retrying {attempt+1}/3...")
                    if attempt == 2:
                        self.stats["permanent_failures"] += 1
                        raise
                    jitter = random.uniform(1.0, 2.0)
                    await asyncio.sleep(2.0 * (1.5 ** attempt) + jitter)
                except httpx.HTTPStatusError as e:
                    if e.response.status_code in [429, 502, 503, 504]:
                        self.stats["retries"] += 1
                        logger.warning(f"HTTP Status {e.response.status_code}. Retrying {attempt+1}/3...")
                        if attempt == 2:
                            self.stats["permanent_failures"] += 1
                            raise
                        jitter = random.uniform(1.0, 3.0)
                        await asyncio.sleep(3.0 * (1.5 ** attempt) + jitter)
                    else:
                        self.stats["permanent_failures"] += 1
                        raise

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

        # Robust JSON extraction from markdown code block or plain text
        m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
        if m:
            clean_json = m.group(1).strip()
        else:
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
                f"Schema:\n{json.dumps(schema, indent=2)}\n\n"
                f"Return ONLY valid JSON."
            )
            fixed_text = await self.generate_text(prompt=repair_prompt, temperature=0.1)
            m_fix = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", fixed_text)
            fixed_json = m_fix.group(1).strip() if m_fix else fixed_text.strip().strip("`").removeprefix("json").strip()
            return response_model.model_validate(json.loads(fixed_json))

    async def get_embedding(self, text: str) -> list[float]:
        """Fetch embedding from text-embedding-3-small. Returns empty list if unavailable."""
        if not self.api_key:
            return []
            
        url = f"{self.base_url}/embeddings"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": "text-embedding-3-small", "input": text[:2048]}
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                res = await client.post(url, headers=headers, json=payload)
                res.raise_for_status()
                return res.json()["data"][0]["embedding"]
            except Exception as e:
                logger.warning(f"OpenAI embedding endpoint failed: {e}. Returning empty embedding (lexical fallback).")
                return []
