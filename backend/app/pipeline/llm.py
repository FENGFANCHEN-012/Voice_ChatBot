import asyncio
from loguru import logger
import google.generativeai as genai
from app.pipeline.rate_limiter import gemini_rate_limiter


STATIC_PROMPT = """You are an enterprise policy assistant. Answer the user's question based ONLY on the provided context and conversation history.

Rules:
1. Cite specific references from the context: chapter numbers, error codes (e.g. ERR-SSO-4039), form numbers (e.g. Form HR-PAY-102), directive names, and policy codes.
2. When a cross-domain dependency exists (e.g. "See Chapter 3"), mention it explicitly.
3. For step-by-step procedures, list them in order.
4. If the question is a follow-up from conversation history (e.g. "explain more", "what do you mean"), answer from history context.
5. If the question clearly requires document context that isn't available, state: "I cannot find this information in the uploaded documents."
6. Do NOT hallucinate or make up information not present in the context.
7. Keep answers concise but complete — include specific numbers, time limits, and thresholds when mentioned in context.

Below is the conversation history, document context, and the question."""


import json
import httpx
from app.config import settings


class LLMClient:
    def __init__(self, api_key: str):
        if api_key:
            genai.configure(api_key=api_key)
        self.fallback_models = ["gemini-2.0-flash-lite", "gemini-1.5-flash", "gemini-2.0-flash"]
        self.model_name = self.fallback_models[0]
        self.last_rate_limit_wait: float = 0.0

    def _build_dynamic_prompt(self, query: str, context: list[str], history: list[dict] | None = None) -> str:
        docs = "\n\n".join(f"---\n{c}" for c in context)

        history_block = ""
        if history:
            lines = []
            for msg in history[-6:]:
                role = "User" if msg["role"] == "user" else "Assistant"
                lines.append(f"{role}: {msg['content']}")
            history_block = "\n".join(lines) + "\n\n"

        return f"""Conversation History:
{history_block}
Context:
{docs}

Question: {query}"""

    async def _generate_deepseek(self, dynamic: str) -> str:
        api_key = settings.deepseek_api_key or settings.gemini_api_key
        url = f"{settings.deepseek_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": settings.deepseek_model_name,
            "messages": [
                {"role": "system", "content": STATIC_PROMPT},
                {"role": "user", "content": dynamic}
            ],
            "temperature": 0.3
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _generate_deepseek_stream(self, dynamic: str):
        api_key = settings.deepseek_api_key or settings.gemini_api_key
        url = f"{settings.deepseek_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": settings.deepseek_model_name,
            "messages": [
                {"role": "system", "content": STATIC_PROMPT},
                {"role": "user", "content": dynamic}
            ],
            "stream": True,
            "temperature": 0.3
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0]["delta"].get("content", "")
                            if delta:
                                yield delta
                        except Exception:
                            continue

    async def generate(self, query: str, context: list[str], history: list[dict] | None = None) -> str:
        dynamic = self._build_dynamic_prompt(query, context, history)
        self.last_rate_limit_wait = 0.0

        provider = settings.llm_provider.lower()
        if provider == "deepseek" or (provider == "auto" and settings.deepseek_api_key):
            try:
                logger.info("[LLM] Generating answer using DeepSeek V3...")
                return await self._generate_deepseek(dynamic)
            except Exception as e:
                logger.error(f"[LLM] DeepSeek failed ({e})")
                if not settings.gemini_api_key:
                    return f"DeepSeek API Error: {e}"
                logger.warning("[LLM] Falling back to Gemini...")

        if not settings.gemini_api_key:
            return "Error: No valid LLM API key configured (neither DeepSeek nor Gemini)."

        for model_name in self.fallback_models:
            model = genai.GenerativeModel(model_name, system_instruction=STATIC_PROMPT)
            for attempt in range(2):
                try:
                    waited = await gemini_rate_limiter.acquire()
                    self.last_rate_limit_wait += waited
                    response = await asyncio.to_thread(model.generate_content, dynamic)
                    return response.text
                except Exception as e:
                    if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                        logger.warning(f"[LLM] Quota hit on {model_name}, trying fallback model...")
                        break
                    else:
                        raise
        logger.error("[LLM] Quota exceeded on all fallback models")
        return "I'm experiencing high demand. Please try again in a minute."

    async def generate_stream(self, query: str, context: list[str], history: list[dict] | None = None):
        dynamic = self._build_dynamic_prompt(query, context, history)

        provider = settings.llm_provider.lower()
        if provider == "deepseek" or (provider == "auto" and settings.deepseek_api_key):
            try:
                logger.info("[LLM] Streaming answer using DeepSeek V3...")
                async for chunk in self._generate_deepseek_stream(dynamic):
                    yield chunk
                return
            except Exception as e:
                logger.error(f"[LLM] DeepSeek streaming failed ({e})")
                if not settings.gemini_api_key:
                    yield f"DeepSeek API Error: {e}"
                    return
                logger.warning("[LLM] Falling back to Gemini...")

        if not settings.gemini_api_key:
            yield "Error: No valid LLM API key configured (neither DeepSeek nor Gemini)."
            return

        for model_name in self.fallback_models:
            model = genai.GenerativeModel(model_name, system_instruction=STATIC_PROMPT)
            for attempt in range(2):
                try:
                    await gemini_rate_limiter.acquire()
                    response = await asyncio.to_thread(model.generate_content, dynamic, stream=True)
                    for chunk in response:
                        if chunk.text:
                            yield chunk.text
                    return
                except Exception as e:
                    if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                        logger.warning(f"[LLM] Quota hit on {model_name}, trying fallback model...")
                        break
                    else:
                        raise
        logger.error("[LLM] Quota exceeded on all fallback models")
        yield "I'm experiencing high demand. Please try again in a minute."
