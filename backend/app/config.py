from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str = ""
    
    # LLM Provider: "gemini" (default), "deepseek", or "auto"
    llm_provider: str = "deepseek"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model_name: str = "deepseek-chat"
    
    Qdrant_api_key: str = ""
    
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:5173"
    whisper_model_size: str = "base"
    whisper_use_gpu: bool = True
    tts_voice: str = "en-US-AndrewMultilingualNeural"
    tts_rate: str = "+0%"
    tts_pitch: str = "+0Hz"
    
    # ------------------------------------------
    
    # fast embedding model
    embedding_model_name: str = "BAAI/bge-m3"
    
    
    reranker_model_name: str = "BAAI/bge-reranker-v2-m3"

    # Vector store — "chroma" (default) or "faiss"
    vector_store_type: str = "chroma"
    chroma_db_path: str = "chroma_db"
    faiss_index_path: str = "faiss_index/index.faiss"
    faiss_metadata_path: str = "faiss_index/metadata.pkl"

    upload_dir: str = "uploads"
    max_file_size_mb: int = 40
    chunk_size: int = 512
    chunk_overlap: int = 64
    retrieval_top_k: int = 10
    retrieval_fetch_k: int = 15
    reranker_top_k: int = 5

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
