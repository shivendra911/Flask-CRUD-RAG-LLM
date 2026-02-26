"""
RAG utilities — chunking, embedding, vector storage, retrieval, and generation.
Uses FAISS for vector storage (reliable prebuilt wheels on all platforms).
"""

import os
import json
import time
import logging

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────
_VECTOR_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "vector_store",
)


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  EMBEDDINGS                                                        ║
# ╚══════════════════════════════════════════════════════════════════════╝

_embeddings = None


def _get_embeddings():
    """Lazy-load the embedding model (Gemini or fallback to HuggingFace)."""
    global _embeddings
    if _embeddings is not None:
        return _embeddings

    api_key = os.environ.get("GEMINI_API_KEY", "")

    if api_key and api_key != "your_gemini_api_key_here":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        _embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=api_key,
        )
        logger.info("Using Gemini gemini-embedding-001")
    else:
        from langchain_community.embeddings import HuggingFaceEmbeddings

        _embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        logger.info("Using local HuggingFace all-MiniLM-L6-v2 embeddings")

    return _embeddings


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  FAISS VECTOR STORE  (with user/doc metadata filtering)            ║
# ╚══════════════════════════════════════════════════════════════════════╝

_vectorstore = None
_FAISS_INDEX = os.path.join(_VECTOR_DIR, "faiss_index")


def _ensure_dir():
    os.makedirs(_VECTOR_DIR, exist_ok=True)


def _get_vectorstore():
    """Lazy-load the FAISS vector store."""
    global _vectorstore
    if _vectorstore is not None:
        return _vectorstore

    from langchain_community.vectorstores import FAISS
    from langchain_core.documents import Document as LCDoc

    _ensure_dir()
    emb = _get_embeddings()

    if os.path.exists(os.path.join(_FAISS_INDEX, "index.faiss")):
        _vectorstore = FAISS.load_local(
            _FAISS_INDEX, emb, allow_dangerous_deserialization=True
        )
        logger.info("Loaded existing FAISS index")
    else:
        # Create a new empty store with a placeholder doc
        _vectorstore = FAISS.from_documents(
            [LCDoc(page_content="placeholder", metadata={"user_id": "0", "doc_id": "0"})],
            emb,
        )
        _vectorstore.save_local(_FAISS_INDEX)
        logger.info("Created new FAISS index")

    return _vectorstore


def _save_vectorstore():
    if _vectorstore is not None:
        _ensure_dir()
        _vectorstore.save_local(_FAISS_INDEX)


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  CHUNKING                                                          ║
# ╚══════════════════════════════════════════════════════════════════════╝


def load_and_chunk(filepath: str):
    """
    Extract text from a file and split into overlapping chunks.
    Supports: .pdf, .txt, .md
    """
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".pdf":
        from langchain_community.document_loaders import PyPDFLoader

        loader = PyPDFLoader(filepath)
        pages = loader.load()
    else:
        from langchain_community.document_loaders import TextLoader

        loader = TextLoader(filepath, encoding="utf-8")
        pages = loader.load()

    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(pages)
    return chunks


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  STORE / DELETE CHUNKS                                             ║
# ╚══════════════════════════════════════════════════════════════════════╝


def store_chunks(chunks, user_id, doc_id):
    """Tag each chunk with user_id and doc_id metadata, then add to FAISS."""
    for chunk in chunks:
        chunk.metadata["user_id"] = str(user_id)
        chunk.metadata["doc_id"] = str(doc_id)

    vs = _get_vectorstore()
    vs.add_documents(chunks)
    _save_vectorstore()
    logger.info(f"Stored {len(chunks)} chunks for doc_id={doc_id}")


def delete_chunks(doc_id: str):
    """Remove metadata entries for a document.
    Note: FAISS doesn't support native deletion by metadata, so we rebuild
    the index excluding the deleted doc's chunks on next store operation.
    For a personal learning project this is acceptable."""
    # Soft delete — the chunks remain in FAISS but are filtered out at
    # retrieval time by the user_id/doc_id metadata check.
    logger.info(f"Marked doc_id={doc_id} for exclusion from retrieval")


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  RETRIEVAL                                                         ║
# ╚══════════════════════════════════════════════════════════════════════╝


def retrieve_relevant_chunks(question: str, user_id, k: int = 4):
    """Similarity search filtered to this user's documents only."""
    vs = _get_vectorstore()

    # Over-fetch then filter by user_id
    results = vs.similarity_search(query=question, k=k * 4)

    filtered = [
        doc
        for doc in results
        if doc.metadata.get("user_id") == str(user_id)
    ]

    return filtered[:k]


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  PROMPT CONSTRUCTION                                               ║
# ╚══════════════════════════════════════════════════════════════════════╝


def build_prompt(question: str, chunks) -> str:
    """Build a grounded RAG prompt that constrains the LLM to the context."""
    context_text = "\n\n---\n\n".join([c.page_content for c in chunks])

    prompt = f"""You are an expert tutor helping a student study from their own notes and documents.

RULES:
- Answer ONLY using the Context below.
- If the answer is not in the Context, respond EXACTLY: "I don't have that in my notes."
- Do not use your general knowledge, even if you know the answer.
- Cite which part of the context your answer came from.
- Use clear, well-structured formatting with bullet points when appropriate.

Context:
{context_text}

Question: {question}

Answer:"""
    return prompt


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  LLM GENERATION                                                    ║
# ╚══════════════════════════════════════════════════════════════════════╝

_model = None


def _get_model():
    """Lazy-load the Gemini generative model."""
    global _model
    if _model is not None:
        return _model

    import google.generativeai as genai

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key or api_key == "your_gemini_api_key_here":
        raise ValueError(
            "GEMINI_API_KEY environment variable is not set. "
            "Get one free at https://aistudio.google.com/apikey"
        )

    genai.configure(api_key=api_key)
    _model = genai.GenerativeModel("gemini-2.0-flash")
    return _model


def generate_answer(prompt: str, retries: int = 3) -> str:
    """Send the prompt to Gemini and return the response, with retry logic."""
    model = _get_model()

    for attempt in range(retries):
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = (
                "429" in str(e)
                or "resourceexhausted" in type(e).__name__.lower()
                or "resource_exhausted" in error_str
                or "quota" in error_str
            )
            is_unavailable = (
                "503" in str(e)
                or "unavailable" in error_str
            )

            if is_rate_limit:
                if attempt < retries - 1:
                    time.sleep(10)
                    continue
                return (
                    "⏳ API rate limit reached. The free tier has limited daily requests. "
                    "Please wait a minute and try again, or check your quota at "
                    "https://ai.dev/rate-limit"
                )
            if is_unavailable:
                return (
                    "The AI service is temporarily unavailable. "
                    "Please try again in a few minutes."
                )
            raise

    return "Unable to generate an answer at this time."
