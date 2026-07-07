from google import genai
from google.genai import types

from app.config import settings

_client = genai.Client(api_key=settings.gemini_api_key)

_CHUNK_SIZE = 1500
_CHUNK_OVERLAP = 200
_EMBED_BATCH_SIZE = 100  # Gemini's batchEmbedContents caps at 100 inputs per request


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
    """Embed chunks being stored for later retrieval.

    Batched at _EMBED_BATCH_SIZE — a long real-world document (unlike the shorter synthetic
    samples) can chunk into well over 100 pieces, and Gemini's batch embedding endpoint rejects
    anything past 100 inputs in a single request.
    """
    if not texts:
        return []
    embeddings: list[list[float]] = []
    for i in range(0, len(texts), _EMBED_BATCH_SIZE):
        batch = texts[i : i + _EMBED_BATCH_SIZE]
        resp = _client.models.embed_content(
            model=settings.embedding_model,
            contents=batch,
            config=types.EmbedContentConfig(output_dimensionality=settings.embedding_dim, task_type="RETRIEVAL_DOCUMENT"),
        )
        embeddings.extend(e.values for e in resp.embeddings)
    return embeddings


def embed_query(text: str) -> list[float]:
    """Embed a user's natural-language question for similarity search against stored chunks."""
    resp = _client.models.embed_content(
        model=settings.embedding_model,
        contents=[text],
        config=types.EmbedContentConfig(output_dimensionality=settings.embedding_dim, task_type="RETRIEVAL_QUERY"),
    )
    return resp.embeddings[0].values
