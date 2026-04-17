"""Knowledge Vector DB — ChromaDB for semantic search."""
import chromadb
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "knowledge")
os.makedirs(DATA_DIR, exist_ok=True)

_client = chromadb.PersistentClient(path=DATA_DIR)


def get_collection(gpt_id: str):
    """Get or create a ChromaDB collection for a custom GPT."""
    return _client.get_or_create_collection(name=f"gpt_{gpt_id}")


def add_chunks(gpt_id: str, chunks: list[str], ids: list[str], metadata: list[dict] = None):
    """Add text chunks to the knowledge base."""
    col = get_collection(gpt_id)
    col.add(documents=chunks, ids=ids, metadatas=metadata)


def search(gpt_id: str, query: str, n_results: int = 5) -> list[str]:
    """Search knowledge base for relevant chunks."""
    col = get_collection(gpt_id)
    if col.count() == 0:
        return []
    results = col.query(query_texts=[query], n_results=min(n_results, col.count()))
    return results.get("documents", [[]])[0]


def delete_collection(gpt_id: str):
    """Delete all knowledge for a GPT."""
    try:
        _client.delete_collection(f"gpt_{gpt_id}")
    except Exception:
        pass


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap
    return chunks
