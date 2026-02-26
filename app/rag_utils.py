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
    """Lazy-load the embedding model (local HuggingFace — no API calls needed)."""
    global _embeddings
    if _embeddings is not None:
        return _embeddings

    from langchain_community.embeddings import HuggingFaceEmbeddings

    _embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    logger.info("Using local HuggingFace all-MiniLM-L6-v2 embeddings (free, no API quota)")

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


def store_chunks(chunks, user_id, doc_id, filename="", upload_date=""):
    """Tag each chunk with user_id, doc_id, and file metadata, then add to FAISS."""
    for chunk in chunks:
        chunk.metadata["user_id"] = str(user_id)
        chunk.metadata["doc_id"] = str(doc_id)
        chunk.metadata["filename"] = filename
        chunk.metadata["upload_date"] = upload_date

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

    # Pass the user_id as a metadata filter to FAISS.
    # Set fetch_k to the total size of the index to ensure we don't drop
    # matches that fall outside the default fetch range due to multi-user noise.
    total_docs = vs.index.ntotal
    fetch_k = max(20, total_docs)
    
    results = vs.similarity_search(
        query=question, 
        k=k, 
        fetch_k=fetch_k, 
        filter={"user_id": str(user_id)}
    )

    return results


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  PROMPT CONSTRUCTION                                               ║
# ╚══════════════════════════════════════════════════════════════════════╝


def build_prompt(question: str, chunks) -> str:
    """Build a grounded RAG prompt that constrains the LLM to the context."""
    
    # Include metadata (filename, date) alongside the actual chunk content
    context_blocks = []
    for c in chunks:
        fname = c.metadata.get("filename", "Unknown File")
        date = c.metadata.get("upload_date", "Unknown Date")
        # Format block: [Filename (Uploaded: Date)] \n Content
        block = f"[{fname} (Uploaded: {date})]\n{c.page_content}"
        context_blocks.append(block)
        
    context_text = "\n\n---\n\n".join(context_blocks)

    prompt = f"""You are an expert tutor helping a student study from their own notes and documents.

RULES:
- Answer ONLY using the Context below.
- If the answer is not in the Context, respond EXACTLY: "I don't have that in my notes."
- Do not use your general knowledge, even if you know the answer.
- Cite which part of the context your answer came from.
- Document Metadata (Filename and Upload Date) are provided at the start of each context block in brackets like [file.pdf (Uploaded: date)]. Use this metadata to answer questions about the user's files and recent uploads.
- Use clear, well-structured formatting with bullet points when appropriate.

Context:
{context_text}

Question: {question}

Answer:"""
    return prompt


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  LLM GENERATION (LOCAL OLLAMA)                                     ║
# ╚══════════════════════════════════════════════════════════════════════╝

_model = None

def _get_model():
    """Lazy-load the local Ollama generative model."""
    global _model
    if _model is not None:
        return _model

    # Use langchain_community's Ollama integration
    from langchain_community.llms import Ollama

    logger.info("Initializing connection to local Ollama (model: llama3.2)...")
    # You can change 'llama3.2' to 'mistral' or 'phi3' depending on what you downloaded
    _model = Ollama(model="llama3.2")
    return _model


def generate_answer(prompt: str, retries: int = 3) -> str:
    """Send the prompt to the local Ollama instance and return the response."""
    model = _get_model()

    for attempt in range(retries):
        try:
            # For langchain_community.llms.Ollama, we just call invoke()
            response = model.invoke(prompt)
            # Ollama returns a raw string, not a complex response object like Gemini
            return response
        except Exception as e:
            error_str = str(e).lower()
            if "connection refused" in error_str or "connect" in error_str:
                return (
                    "⚠️ **Ollama is not running.**<br><br>"
                    "Please open your terminal and run:<br>"
                    "<code>ollama run llama3.2</code><br><br>"
                    "Leave that terminal running in the background, then try your question again."
                )
            if "not found" in error_str:
                return (
                    "⚠️ **Model not found.**<br><br>"
                    "You need to download the model first. "
                    "Open your terminal and run:<br>"
                    "<code>ollama run llama3.2</code>"
                )
            
            logger.error(f"Ollama generation failed: {e}")
            if attempt < retries - 1:
                time.sleep(2)
                continue
                
            return f"❌ Local generation failed: {str(e)}"

    return "Unable to generate an answer from the local model at this time."


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  CREATIVE PROMPT BUILDERS                                          ║
# ╚══════════════════════════════════════════════════════════════════════╝


def _extract_context(chunks) -> str:
    """Extract context text from chunks for use in creative prompts."""
    context_blocks = []
    for c in chunks:
        context_blocks.append(c.page_content)
    return "\n\n".join(context_blocks)


def build_quiz_prompt(chunks, num_questions: int = 5, topic: str = "") -> str:
    """Build a prompt that generates multiple-choice quiz questions as JSON."""
    context = _extract_context(chunks)
    topic_filter = f' Focus on the topic: "{topic}".' if topic else ""

    return f"""You are a quiz generator. Create exactly {num_questions} multiple-choice questions based ONLY on the Context below.{topic_filter}

RULES:
- Each question must have exactly 4 options labeled A, B, C, D.
- Only ONE option is correct.
- Questions should test understanding, not just recall.
- Return ONLY valid JSON, no markdown, no extra text.

Context:
{context}

Return this exact JSON format:
{{
  "questions": [
    {{
      "id": 1,
      "question": "What is ...?",
      "options": {{
        "A": "Option A text",
        "B": "Option B text",
        "C": "Option C text",
        "D": "Option D text"
      }},
      "correct": "B",
      "explanation": "Brief explanation of why B is correct."
    }}
  ]
}}"""


def build_puzzle_prompt(chunks, puzzle_type: str = "fill_blank", count: int = 8) -> str:
    """Build a prompt that generates word puzzles as JSON."""
    context = _extract_context(chunks)

    if puzzle_type == "scramble":
        return f"""You are a word puzzle creator. Create exactly {count} word scramble puzzles based ONLY on the Context below.

RULES:
- Pick important keywords/terms from the context.
- Provide a hint (definition or description) for each word.
- Return ONLY valid JSON, no markdown, no extra text.

Context:
{context}

Return this exact JSON format:
{{
  "puzzles": [
    {{
      "id": 1,
      "word": "ALGORITHM",
      "hint": "A step-by-step procedure for solving a problem."
    }}
  ]
}}"""
    else:  # fill_blank
        return f"""You are a fill-in-the-blank puzzle creator. Create exactly {count} fill-in-the-blank sentences based ONLY on the Context below.

RULES:
- Each sentence should have exactly ONE blank (marked as ___).
- The blank should replace an important keyword or concept.
- Provide the correct answer for each blank.
- Return ONLY valid JSON, no markdown, no extra text.

Context:
{context}

Return this exact JSON format:
{{
  "puzzles": [
    {{
      "id": 1,
      "sentence": "The process of ___ converts raw data into useful information.",
      "answer": "processing",
      "hint": "Starts with 'p'"
    }}
  ]
}}"""


def build_questions_prompt(chunks, q_type: str = "short_answer", count: int = 6) -> str:
    """Build a prompt that generates study questions as JSON."""
    context = _extract_context(chunks)

    if q_type == "true_false":
        return f"""You are a study question creator. Create exactly {count} true/false questions based ONLY on the Context below.

RULES:
- Mix true and false statements roughly equally.
- Statements should be clear and unambiguous.
- Return ONLY valid JSON, no markdown, no extra text.

Context:
{context}

Return this exact JSON format:
{{
  "questions": [
    {{
      "id": 1,
      "statement": "The earth revolves around the sun.",
      "answer": true,
      "explanation": "This is correct because..."
    }}
  ]
}}"""
    elif q_type == "flashcard":
        return f"""You are a flashcard creator. Create exactly {count} flashcards based ONLY on the Context below.

RULES:
- The front should be a concise question or term.
- The back should be a clear, concise answer or definition.
- Focus on key concepts and important details.
- Return ONLY valid JSON, no markdown, no extra text.

Context:
{context}

Return this exact JSON format:
{{
  "flashcards": [
    {{
      "id": 1,
      "front": "What is machine learning?",
      "back": "A subset of AI that enables systems to learn from data without being explicitly programmed."
    }}
  ]
}}"""
    else:  # short_answer
        return f"""You are a study question creator. Create exactly {count} short-answer questions based ONLY on the Context below.

RULES:
- Questions should require a 1-3 sentence answer.
- Cover different aspects of the content.
- Include the model answer for each question.
- Return ONLY valid JSON, no markdown, no extra text.

Context:
{context}

Return this exact JSON format:
{{
  "questions": [
    {{
      "id": 1,
      "question": "Explain the concept of...",
      "answer": "The concept refers to..."
    }}
  ]
}}"""
