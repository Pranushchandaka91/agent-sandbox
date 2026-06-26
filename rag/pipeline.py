import base64
import re
import requests
from openai import OpenAI

_chroma_client = None
_collection = None

_GITHUB_HEADERS = {"Accept": "application/vnd.github+json", "User-Agent": "agent-sandbox"}
_SKIP_PREFIXES = ("node_modules/", ".git/", "dist/", "build/", "__pycache__/")
_MAX_FILE_BYTES = 100_000


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


def chunk_python(text: str, max_chunk: int = 1500) -> list[str]:
    """Split Python source on def/class boundaries; fall back to char chunks if oversized."""
    lines = text.splitlines(keepends=True)
    boundary = re.compile(r'^[ \t]*(def |class )')

    segments: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if boundary.match(line) and current:
            segments.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        segments.append(current)

    result = []
    for seg_lines in segments:
        seg = "".join(seg_lines).strip()
        if not seg:
            continue
        if len(seg) > max_chunk:
            result.extend(chunk_text(seg, chunk_size=max_chunk, overlap=100))
        else:
            result.append(seg)
    return result


def embed_texts(texts: list[str], tracker=None, label: str = "embed") -> list[list[float]]:
    client = OpenAI()
    response = client.embeddings.create(model="text-embedding-3-small", input=texts)
    if tracker is not None:
        tracker.track(_EmbedUsage(response.usage), label)
    return [item.embedding for item in response.data]


def _clear_repo_index(doc_id: str) -> None:
    collection = _get_collection()
    try:
        existing = collection.get(where={"doc_id": doc_id})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass


def index_document(doc_id: str, text: str, tracker=None) -> int:
    """Index a single text blob (backward-compatible, md chunking)."""
    collection = _get_collection()
    chunks = chunk_text(text)
    if not chunks:
        return 0

    _clear_repo_index(doc_id)

    embeddings = embed_texts(chunks, tracker=tracker, label="embed_index")
    ids = [f"{doc_id}::chunk::{i}" for i in range(len(chunks))]
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=[{"doc_id": doc_id, "file_path": "", "type": "md"} for _ in chunks],
    )
    return len(chunks)


def index_repo(repo: str, tracker=None) -> int:
    """Fetch every .md and .py file from the repo and index them all."""
    # Resolve default branch
    try:
        r = requests.get(f"https://api.github.com/repos/{repo}", headers=_GITHUB_HEADERS, timeout=10)
        r.raise_for_status()
        default_branch = r.json().get("default_branch", "main")
    except Exception as e:
        raise RuntimeError(f"Failed to fetch repo info for '{repo}': {e}")

    # Fetch recursive file tree
    try:
        r = requests.get(
            f"https://api.github.com/repos/{repo}/git/trees/{default_branch}?recursive=1",
            headers=_GITHUB_HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        tree = r.json().get("tree", [])
    except Exception as e:
        raise RuntimeError(f"Failed to fetch file tree for '{repo}': {e}")

    # Filter to eligible .md / .py files
    selected = [
        item["path"]
        for item in tree
        if item.get("type") == "blob"
        and not any(item["path"].startswith(p) for p in _SKIP_PREFIXES)
        and (item["path"].endswith(".md") or item["path"].endswith(".py"))
        and item.get("size", 0) <= _MAX_FILE_BYTES
    ]

    # Clear previous index for this repo
    _clear_repo_index(repo)

    all_ids: list[str] = []
    all_documents: list[str] = []
    all_metadatas: list[dict] = []

    for path in selected:
        try:
            r = requests.get(
                f"https://api.github.com/repos/{repo}/contents/{path}",
                headers=_GITHUB_HEADERS,
                timeout=10,
            )
            if not r.ok:
                continue
            content_b64 = r.json().get("content", "")
            text = base64.b64decode(content_b64).decode("utf-8", errors="replace")
        except Exception:
            continue

        file_type = "py" if path.endswith(".py") else "md"
        chunks = chunk_python(text) if file_type == "py" else chunk_text(text)

        for i, chunk in enumerate(chunks):
            all_ids.append(f"{repo}::{path}::chunk::{i}")
            all_documents.append(chunk)
            all_metadatas.append({"doc_id": repo, "file_path": path, "type": file_type})

    if not all_ids:
        return 0

    all_embeddings = embed_texts(all_documents, tracker=tracker, label="embed_index")
    _get_collection().add(
        ids=all_ids,
        embeddings=all_embeddings,
        documents=all_documents,
        metadatas=all_metadatas,
    )
    return len(all_ids)


def retrieve(doc_id: str, question: str, k: int = 5, tracker=None) -> list[dict]:
    """Return top-k chunks as [{"text": str, "file_path": str}, ...]."""
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
        include=["documents", "metadatas"],
    )

    docs = results["documents"][0] if results["documents"] else []
    metas = results["metadatas"][0] if results["metadatas"] else []
    return [
        {"text": doc, "file_path": meta.get("file_path", "")}
        for doc, meta in zip(docs, metas)
    ]
