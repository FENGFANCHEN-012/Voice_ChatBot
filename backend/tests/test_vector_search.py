import asyncio
from app.pipeline.embedder import Embedder
from app.pipeline.vector_store import create_vector_store
from app.config import settings

embedder = Embedder(settings.embedding_model_name)
vs = create_vector_store(settings)
results = vs.similarity_search("SSO lockout", embedder, k=3)
print(f"Found {len(results)} chunks")
for r in results:
    print(f"  - {r['text'][:80]}...")
