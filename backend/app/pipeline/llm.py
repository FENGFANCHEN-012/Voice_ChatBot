import google.generativeai as genai



# LLMClient is a wrapper around the Gemini 2.5 Flash model for generating answers based on user queries and context.
class LLMClient:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        
        # use genai.GenerativeModel to create a model instance for Gemini 2.5 Flash
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

        prompt = f"""You are a helpful assistant. Answer the user's question based ONLY on the provided context.

Conversation history:
{history_block}Context:
{docs}

Question: {query}

Answer concisely and accurately. If the context does not contain the answer, say "I cannot find this information in the uploaded documents."
"""
        response = self.model.generate_content(prompt)
        return response.text
