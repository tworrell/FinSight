from unittest.mock import MagicMock, patch

from app.ingest.embeddings import _EMBED_BATCH_SIZE, embed_documents


def _fake_response(batch: list[str]):
    resp = MagicMock()
    resp.embeddings = [MagicMock(values=[float(len(text))]) for text in batch]
    return resp


def test_embed_documents_empty_input_makes_no_api_call():
    with patch("app.ingest.embeddings._client") as mock_client:
        result = embed_documents([])
    assert result == []
    mock_client.models.embed_content.assert_not_called()


def test_embed_documents_single_batch_under_limit():
    texts = [f"chunk {i}" for i in range(10)]
    with patch("app.ingest.embeddings._client") as mock_client:
        mock_client.models.embed_content.side_effect = lambda **kwargs: _fake_response(kwargs["contents"])
        result = embed_documents(texts)
    assert mock_client.models.embed_content.call_count == 1
    assert len(result) == 10


def test_embed_documents_splits_into_batches_of_at_most_100():
    # Real-world Drive documents are long enough to chunk past 100 pieces, and Gemini's
    # batchEmbedContents endpoint rejects more than 100 inputs in a single request.
    texts = [f"chunk {i}" for i in range(230)]
    with patch("app.ingest.embeddings._client") as mock_client:
        mock_client.models.embed_content.side_effect = lambda **kwargs: _fake_response(kwargs["contents"])
        result = embed_documents(texts)

    call_sizes = [len(call.kwargs["contents"]) for call in mock_client.models.embed_content.call_args_list]
    assert call_sizes == [100, 100, 30]
    assert all(size <= _EMBED_BATCH_SIZE for size in call_sizes)
    assert len(result) == 230


def test_embed_documents_preserves_order_across_batches():
    texts = [f"chunk-{i}" for i in range(120)]
    with patch("app.ingest.embeddings._client") as mock_client:
        mock_client.models.embed_content.side_effect = lambda **kwargs: _fake_response(kwargs["contents"])
        result = embed_documents(texts)

    # our fake embedding is just [len(text)] — confirms results line up with their source chunk
    expected = [[float(len(t))] for t in texts]
    assert result == expected
