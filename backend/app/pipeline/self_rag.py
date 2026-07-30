import google.generativeai as genai


class SelfRAG:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-3.5-flash-lite")

    def verify_relevance(self, query: str, chunks: list[dict]) -> tuple[list[dict], bool]:
        relevant = []
        for c in chunks:
            text = c["text"][:300]
            prompt = f"""Query: {query}
Chunk: {text}

Is this chunk relevant to answering the query? Answer ONLY: YES or NO"""
            resp = self.model.generate_content(prompt)
            if resp.text.strip().startswith("YES"):
                relevant.append(c)

        passed = len(relevant) >= len(chunks) // 2 if chunks else False
        return relevant if relevant else chunks, passed

    def verify_answer(self, query: str, answer: str, context: list[str]) -> str:
        prompt = f"""Query: {query}
Answer: {answer}

Context used: {" ".join(c[:500] for c in context)}

Is this answer fully supported by the context? If not, what part is unsupported? Reply: FULLY_SUPPORTED, PARTIALLY_SUPPORTED, or NOT_SUPPORTED"""
        resp = self.model.generate_content(prompt)
        status = resp.text.strip()

        if "NOT_SUPPORTED" in status:
            return f"{answer}\n\n(Note: I'm not fully confident about this answer based on the available documents.)"
        if "PARTIALLY" in status:
            return f"{answer}\n\n(Note: Part of this answer may not be fully supported by the documents.)"
        return answer
