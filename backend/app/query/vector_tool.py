from sqlalchemy.orm import Session

from app.ingest.embeddings import embed_query
from app.models import Chunk, Document


def semantic_search(db: Session, query: str, k: int = 5) -> list[dict]:
    """Cosine-similarity search over chunked document text — for qualitative/narrative
    questions (strategy, positioning, commentary) where there's no single numeric answer
    to compute via SQL."""
    query_vector = embed_query(query)
    rows = (
        db.query(Chunk, Document.filename, Chunk.embedding.cosine_distance(query_vector).label("distance"))
        .join(Document, Document.id == Chunk.document_id)
        .order_by("distance")
        .limit(max(1, min(k, 20)))
        .all()
    )
    return [
        {
            "document": filename,
            "chunk_text": chunk.chunk_text,
            "similarity": round(1 - float(distance), 4),
        }
        for chunk, filename, distance in rows
    ]
