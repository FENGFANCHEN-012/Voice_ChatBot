import asyncio
from loguru import logger
import google.generativeai as genai
from app.pipeline.rate_limiter import gemini_rate_limiter



# agent RAG will only be used in fallback stage
class AgentRAG:
    
    # query type return for next step: simple_fact, complex_reasoning, comparison, out_of_scope, summarization
    SIMPLE = "simple_fact"
    COMPLEX = "complex_reasoning"
    COMPARISON = "comparison"
    OUT_OF_SCOPE = "out_of_scope"
    SUMMARIZE = "summarization"

    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-3.5-flash-lite")

    async def classify(self, query: str) -> str:
        prompt = f"""Classify this user query into one of these categories. Reply ONLY the category name.

- simple_fact: Short factual question, 1-5 words, seeks specific detail (e.g. "what is the deadline?", "when is the meeting?")
- complex_reasoning: Multi-part question requiring analysis across documents (e.g. "what are the requirements and how do I apply?")
- comparison: Comparing two or more things (e.g. "difference between option A and B")
- summarization: Request to summarize a document or section (e.g. "summarize the document", "give me an overview")
- out_of_scope: Greetings, chit-chat, or questions not related to documents (e.g. "hello", "what is AI?")

Query: {query}
Category:"""
        for attempt in range(3):
            try:
                await gemini_rate_limiter.acquire()
                resp = self.model.generate_content(prompt)
                category = resp.text.strip().lower()
                valid = {self.SIMPLE, self.COMPLEX, self.COMPARISON, self.OUT_OF_SCOPE, self.SUMMARIZE}
                return category if category in valid else self.COMPLEX
            
            
            except Exception as e:
                if "RESOURCE_EXHAUSTED" in str(e):
                    wait = 5 * (attempt + 1)
                    logger.warning(f"[AgentRAG] Quota hit, waiting {wait}s")
                    await asyncio.sleep(wait)
                else:
                    raise
        return self.COMPLEX
