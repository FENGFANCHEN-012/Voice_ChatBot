import asyncio
from loguru import logger
import google.generativeai as genai
from app.pipeline.rate_limiter import gemini_rate_limiter


class QueryExpander:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-3.5-flash-lite")

    async def _call(self, prompt: str) -> str:
        for attempt in range(3):
            try:
                await gemini_rate_limiter.acquire()
                return self.model.generate_content(prompt).text
            except Exception as e:
                if "RESOURCE_EXHAUSTED" in str(e):
                    wait = 5 * (attempt + 1)
                    logger.warning(f"[QueryExpander] Quota hit, waiting {wait}s")
                    await asyncio.sleep(wait)
                else:
                    raise
        return ""

    async def expand(self, query: str) -> str:
        if len(query.split()) <= 3:
            return await self._expand_simple(query)
        return await self._simplify_complex(query)

    async def _expand_simple(self, query: str) -> str:
        prompt = f"""Given the user's short search query: "{query}"

Return ONLY a comma-separated list of 4-6 alternative search terms/phrases that capture the same intent. Do NOT include the original query. Do NOT add explanations.

Example - Input: "deadline"
Output: due date, submission deadline, closing date, cutoff time, final date, last day
"""
        resp = await self._call(prompt)
        return f"{query}, {resp}" if resp else query

    async def _simplify_complex(self, query: str) -> str:
        prompt = f"""Given the user's question: "{query}"

Extract ONLY the core search query (3-8 words) that would best find relevant documents. Remove conversational fluff. Output ONLY the simplified query.

Example - Input: "What is the process for submitting the annual report and who needs to approve it?"
Output: annual report submission approval process
"""
        resp = await self._call(prompt)
        return resp if resp else query
