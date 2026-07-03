from google import genai
from google.genai import types

from app.config import settings

_client = genai.Client(api_key=settings.gemini_api_key)

_CHUNK_SIZE = 1500
_CHUNK_OVERLAP = 200


def chunk_text(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + _CHUNK_SIZE
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - _CHUNK_OVERLAP
    return chunks


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed chunks being stored for later retrieval."""
    if not texts:
        return []
    resp = _client.models.embed_content(
        model=settings.embedding_model,
        contents=texts,
        config=types.EmbedContentConfig(output_dimensionality=settings.embedding_dim, task_type="RETRIEVAL_DOCUMENT"),
    )
    return [e.values for e in resp.embeddings]


def embed_query(text: str) -> list[float]:
    """Embed a user's natural-language question for similarity search against stored chunks."""
    resp = _client.models.embed_content(
        model=settings.embedding_model,
        contents=[text],
        config=types.EmbedContentConfig(output_dimensionality=settings.embedding_dim, task_type="RETRIEVAL_QUERY"),
    )
    return resp.embeddings[0].values
