import google.generativeai as genai


class QueryExpander:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-3.5-flash-lite")

    def expand(self, query: str) -> str:
        if len(query.split()) <= 3:
            return self._expand_simple(query)
        return self._simplify_complex(query)

    def _expand_simple(self, query: str) -> str:
        prompt = f"""Given the user's short search query: "{query}"

Return ONLY a comma-separated list of 4-6 alternative search terms/phrases that capture the same intent. Do NOT include the original query. Do NOT add explanations.

Example - Input: "deadline"
Output: due date, submission deadline, closing date, cutoff time, final date, last day
"""
        resp = self.model.generate_content(prompt)
        expanded = resp.text.strip()
        return f"{query}, {expanded}"

    def _simplify_complex(self, query: str) -> str:
        prompt = f"""Given the user's question: "{query}"

Extract ONLY the core search query (3-8 words) that would best find relevant documents. Remove conversational fluff. Output ONLY the simplified query.

Example - Input: "What is the process for submitting the annual report and who needs to approve it?"
Output: annual report submission approval process
"""
        resp = self.model.generate_content(prompt)
        return resp.text.strip()
