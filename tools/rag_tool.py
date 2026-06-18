from openai import OpenAI
from tools.github import github_readme
from rag.pipeline import index_document, retrieve
from agent.context import current_tracker

_indexed_this_run: set[str] = set()


def query_document(repo: str, question: str) -> dict:
    if not repo or "/" not in repo:
        return {"status": "error", "data": None, "error": "repo must be in 'owner/name' format."}
    if not question or not question.strip():
        return {"status": "error", "data": None, "error": "question parameter is required."}

    tracker = current_tracker.get()

    # Phase 1 — fetch and index (once per repo per run)
    if repo not in _indexed_this_run:
        readme_result = github_readme(repo)
        if readme_result["status"] != "success":
            return readme_result
        readme_text = readme_result["data"]["readme_text"]
        index_document(repo, readme_text, tracker=tracker)
        _indexed_this_run.add(repo)

    # Phase 2 — retrieve relevant chunks
    chunks = retrieve(repo, question, k=4, tracker=tracker)
    if not chunks:
        return {
            "status": "error",
            "data":   None,
            "error":  f"No indexed content found for '{repo}'. The README may be empty.",
        }

    # Phase 3 — generate answer from retrieved context
    context = "\n\n---\n\n".join(chunks)
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
            "chunk_preview": [c[:100] for c in chunks],
        },
        "error": None,
    }
