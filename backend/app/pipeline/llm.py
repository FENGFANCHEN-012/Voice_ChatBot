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


class LLMClient:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model_name = "gemini-3.5-flash-lite"
        self.model = genai.GenerativeModel(self.model_name, system_instruction=STATIC_PROMPT)
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

    async def _get_model(self):
        return self.model

    async def generate(self, query: str, context: list[str], history: list[dict] | None = None) -> str:
        model = await self._get_model()
        dynamic = self._build_dynamic_prompt(query, context, history)
        self.last_rate_limit_wait = 0.0
        for attempt in range(3):
            try:
                waited = await gemini_rate_limiter.acquire()
                self.last_rate_limit_wait += waited
                response = await asyncio.to_thread(model.generate_content, dynamic)
                return response.text
            except Exception as e:
                if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                    wait = 5 * (attempt + 1)
                    self.last_rate_limit_wait += wait
                    logger.warning(f"[LLM] Quota hit, waiting {wait}s (attempt {attempt+1}/3)")
                    await asyncio.sleep(wait)
                else:
                    raise
        logger.error("[LLM] Quota exceeded after 3 retries")
        return "I'm experiencing high demand. Please try again in a minute."

    async def generate_stream(self, query: str, context: list[str], history: list[dict] | None = None):
        model = await self._get_model()
        dynamic = self._build_dynamic_prompt(query, context, history)
        for attempt in range(3):
            try:
                await gemini_rate_limiter.acquire()
                response = await asyncio.to_thread(model.generate_content, dynamic, stream=True)
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
                return
            except Exception as e:
                if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                    wait = 5 * (attempt + 1)
                    logger.warning(f"[LLM] Quota hit, waiting {wait}s (attempt {attempt+1}/3)")
                    await asyncio.sleep(wait)
                else:
                    raise
        logger.error("[LLM] Quota exceeded after 3 retries")
        yield "I'm experiencing high demand. Please try again in a minute."
