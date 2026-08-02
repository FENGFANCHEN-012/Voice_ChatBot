import time
from loguru import logger
import google.generativeai as genai



class LLMClient:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-3.5-flash-lite")

    def generate(self, query: str, context: list[str], history: list[dict] | None = None) -> str:
        docs = "\n\n".join(f"---\n{c}" for c in context)

        history_block = ""
        if history:
            lines = []
            for msg in history[-6:]:
                role = "User" if msg["role"] == "user" else "Assistant"
                lines.append(f"{role}: {msg['content']}")
            history_block = "\n".join(lines) + "\n\n"

        prompt = f"""You are a helpful assistant. Answer the user's question based on the provided context and conversation history.

Conversation history:
{history_block}Context:
{docs}

Question: {query}

Rules:
- If the question is about something from the conversation history, answer from that.
- If the question needs document context, use the provided context.
- If the question is a general follow-up (like "explain more", "what do you mean"), answer from conversation history.
- Only say "I cannot find this information in the uploaded documents" if the question clearly requires document context that isn't available."""
        for attempt in range(3):
            try:
                response = self.model.generate_content(prompt)
                return response.text
            except Exception as e:
                if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                    wait = 30 * (attempt + 1)
                    logger.warning(f"[LLM] Quota hit, waiting {wait}s (attempt {attempt+1}/3)")
                    time.sleep(wait)
                else:
                    raise
        logger.error("[LLM] Quota exceeded after 3 retries")
        return "I'm experiencing high demand. Please try again in a minute."
