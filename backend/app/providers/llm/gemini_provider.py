import json
import logging
from typing import Optional, Type, TypeVar
import httpx
from pydantic import BaseModel
from app.core.config import settings
from app.providers.llm.base import LLMProvider

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

class GeminiProvider(LLMProvider):
    """Google Gemini Provider using standard REST API endpoint"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.FAST_LLM_MODEL
        # Normalize model names
        if not self.model.startswith("gemini-"):
            self.model = "gemini-1.5-flash"
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> str:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set.")

        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        
        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"System Instructions: {system_prompt}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I will follow these instructions."}]})
        
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens or 4096,
            }
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            try:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text.strip()
            except (KeyError, IndexError) as e:
                logger.error(f"Failed to parse Gemini response: {data}")
                raise ValueError(f"Invalid Gemini response: {e}")

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
            f"DO NOT include markdown formatting like ```json or ```. Return ONLY the raw JSON string."
        )

        raw_text = await self.generate_text(
            prompt=structured_prompt,
            system_prompt=system_prompt,
            temperature=temperature
        )

        clean_json = raw_text.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:]
        if clean_json.startswith("```"):
            clean_json = clean_json[3:]
        if clean_json.endswith("```"):
            clean_json = clean_json[:-3]
        clean_json = clean_json.strip()

        try:
            parsed_dict = json.loads(clean_json)
            return response_model.model_validate(parsed_dict)
        except Exception as e:
            logger.warning(f"JSON validation failed, attempting repair: {e}. Raw: {raw_text[:200]}")
            # Self-healing attempt with explicit fix prompt
            repair_prompt = (
                f"The following JSON text produced a validation error:\n"
                f"Error: {e}\n"
                f"Invalid JSON Text:\n{clean_json}\n\n"
                f"Fix the JSON so it strictly matches this JSON Schema:\n{json.dumps(schema, indent=2)}\n"
                f"Return ONLY valid raw JSON."
            )
            repaired_text = await self.generate_text(prompt=repair_prompt, temperature=0.0)
            clean_repaired = repaired_text.strip().strip("`").removeprefix("json").strip()
            parsed_dict = json.loads(clean_repaired)
            return response_model.model_validate(parsed_dict)

    async def get_embedding(self, text: str) -> list[float]:
        """Fetch embedding from text-embedding-004"""
        if not self.api_key:
            return [0.0] * 768
        
        url = f"{self.base_url}/models/text-embedding-004:embedContent?key={self.api_key}"
        payload = {
            "model": "models/text-embedding-004",
            "content": {"parts": [{"text": text[:2048]}]}
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                res = await client.post(url, json=payload)
                res.raise_for_status()
                return res.json()["embedding"]["values"]
            except Exception as e:
                logger.warning(f"Gemini embedding failed: {e}. Fallback to mock vector.")
                return [0.0] * 768
