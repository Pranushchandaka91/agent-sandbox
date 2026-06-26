from openai import OpenAI
from rag.pipeline import index_repo, retrieve
from agent.context import current_tracker

_indexed_this_run: set[str] = set()


def query_document(repo: str, question: str) -> dict:
    if not repo or "/" not in repo:
        return {"status": "error", "data": None, "error": "repo must be in 'owner/name' format."}
    if not question or not question.strip():
        return {"status": "error", "data": None, "error": "question parameter is required."}

    tracker = current_tracker.get()

    # Phase 1 — fetch and index all .md/.py files (once per repo per run)
    if repo not in _indexed_this_run:
        try:
            index_repo(repo, tracker=tracker)
        except RuntimeError as e:
            return {"status": "error", "data": None, "error": str(e)}
        _indexed_this_run.add(repo)

    # Phase 2 — retrieve top 5 relevant chunks
    chunks = retrieve(repo, question, k=8, tracker=tracker)
    if not chunks:
        return {
            "status": "error",
            "data":   None,
            "error":  f"No indexed content found for '{repo}'. The repo may be empty or inaccessible.",
        }

    # Phase 3 — generate answer from retrieved context
    context = "\n\n---\n\n".join(c["text"] for c in chunks)
    prompt = (
        "Answer the question using ONLY the context below. "
        "If the answer isn't in the context, say so.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}"
    )
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    if tracker is not None:
        tracker.track(response.usage, "rag_generate")

    answer = response.choices[0].message.content or ""
    return {
        "status": "success",
        "data": {
            "repo":          repo,
            "question":      question,
            "answer":        answer,
            "chunks_used":   len(chunks),
            "chunk_preview": [
                {"file_path": c["file_path"], "preview": c["text"][:100]}
                for c in chunks
            ],
        },
        "error": None,
    }
