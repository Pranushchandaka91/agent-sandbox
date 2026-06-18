from openai import OpenAI

_chroma_client = None
_collection = None


class _EmbedUsage:
    """Adapts embedding usage to the shape TokenTracker.track() expects."""
    def __init__(self, usage):
        self.prompt_tokens = usage.prompt_tokens
        self.completion_tokens = 0
        self.total_tokens = usage.total_tokens


def _get_collection():
    global _chroma_client, _collection
    if _collection is None:
        import chromadb
        _chroma_client = chromadb.PersistentClient(path="./chroma_db")
        _collection = _chroma_client.get_or_create_collection("readme_docs")
    return _collection


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    if not text:
        return []
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        if end < text_len:
            space_pos = text.rfind(" ", start, end)
            if space_pos > start:
                end = space_pos
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        next_start = end - overlap
        if next_start <= start:
            next_start = end
        start = next_start
    return chunks


def embed_texts(texts: list[str], tracker=None, label: str = "embed") -> list[list[float]]:
    client = OpenAI()
    response = client.embeddings.create(model="text-embedding-3-small", input=texts)
    if tracker is not None:
        tracker.track(_EmbedUsage(response.usage), label)
    return [item.embedding for item in response.data]


def index_document(doc_id: str, text: str, tracker=None) -> int:
    collection = _get_collection()
    chunks = chunk_text(text)
    if not chunks:
        return 0

    try:
        existing = collection.get(where={"doc_id": doc_id})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass

    embeddings = embed_texts(chunks, tracker=tracker, label="embed_index")
    ids = [f"{doc_id}::chunk::{i}" for i in range(len(chunks))]
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=[{"doc_id": doc_id} for _ in chunks],
    )
    return len(chunks)


def retrieve(doc_id: str, question: str, k: int = 4, tracker=None) -> list[str]:
    collection = _get_collection()

    try:
        existing = collection.get(where={"doc_id": doc_id})
        actual_k = min(k, len(existing["ids"]))
    except Exception:
        actual_k = k

    if actual_k == 0:
        return []

    q_embeddings = embed_texts([question], tracker=tracker, label="embed_query")
    results = collection.query(
        query_embeddings=q_embeddings,
        n_results=actual_k,
        where={"doc_id": doc_id},
    )
    return results["documents"][0] if results["documents"] else []
