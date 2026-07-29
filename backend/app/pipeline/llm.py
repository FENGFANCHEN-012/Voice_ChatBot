import google.generativeai as genai


class LLMClient:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def generate(self, query: str, context: list[str]) -> str:
        """
        Generates an answer using Gemini 2.5 Flash given the user query and retrieved chunks.

        Args:
            query:   the user's question (from voice or text input)
            context: list of relevant text chunks retrieved from the vector store

        Returns:
            answer text as a string
        """
        docs = "\n\n".join(f"---\n{c}" for c in context)

        prompt = f"""You are a helpful assistant. Answer the user's question based ONLY on the provided context.

Context:
{docs}

Question: {query}

Answer concisely and accurately. If the context does not contain the answer, say "I cannot find this information in the uploaded documents."
"""
        response = self.model.generate_content(prompt)
        return response.text
