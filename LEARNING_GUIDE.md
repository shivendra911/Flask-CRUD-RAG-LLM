# 📚 RAG Tutor — Learning Guide

Everything you need to understand the technologies, concepts, and architecture behind this project.

---

## Table of Contents

1. [Python & Flask (Backend)](#1-python--flask-backend)
2. [Database & ORM](#2-database--orm)
3. [Authentication & Security](#3-authentication--security)
4. [RAG Pipeline](#4-rag-pipeline)
5. [LLM Integration](#5-llm-integration)
6. [Frontend (HTML/CSS/JS)](#6-frontend-htmlcssjs)
7. [Docker & Deployment](#7-docker--deployment)
8. [Project Architecture](#8-project-architecture)
9. [Recommended Learning Path](#9-recommended-learning-path)

---

## 1. Python & Flask (Backend)

### What to Learn
| Topic | Why It Matters | Where It's Used |
|-------|---------------|-----------------|
| **Flask** | Micro web framework — handles routes, templates, requests | `routes.py`, `admin_routes.py`, `__init__.py` |
| **Blueprints** | Modular route organization | `main` blueprint in `routes.py`, `admin_bp` in `admin_routes.py` |
| **App Factory Pattern** | `create_app()` function for flexible app initialization | `__init__.py` |
| **Jinja2 Templating** | Server-side HTML rendering with `{% %}` and `{{ }}` | All `.html` files in `templates/` |
| **Decorators** | `@login_required`, `@admin_required`, `@limiter.limit` | `routes.py`, `decorators.py` |
| **Error Handlers** | Custom 403/404/500 pages | `__init__.py` |
| **CLI Commands** | `flask create-admin` via Click | `__init__.py` |

### Resources
- [Flask Mega-Tutorial](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world) — Best free Flask course
- [Flask Official Docs](https://flask.palletsprojects.com/) — Reference
- [Real Python Flask Guide](https://realpython.com/tutorials/flask/)

---

## 2. Database & ORM

### What to Learn
| Topic | Why It Matters | Where It's Used |
|-------|---------------|-----------------|
| **SQLAlchemy ORM** | Python objects → database rows | `models.py` |
| **Flask-SQLAlchemy** | Flask integration for SQLAlchemy | `__init__.py`, `models.py` |
| **Model Relationships** | `User` → has many `Documents` (one-to-many) | `models.py` |
| **Cascade Deletes** | Deleting a user auto-deletes their documents | `models.py` (`cascade="all, delete-orphan"`) |
| **Migrations** | Schema changes over time (we use `db.create_all()` for simplicity) | `__init__.py` |

### Key Concepts
```python
# One-to-Many relationship
class User(db.Model):
    documents = db.relationship("Document", backref="owner", cascade="all, delete-orphan")

class Document(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
```

### Resources
- [SQLAlchemy Tutorial](https://docs.sqlalchemy.org/en/20/tutorial/) — Official
- [Flask-SQLAlchemy Quickstart](https://flask-sqlalchemy.palletsprojects.com/)

---

## 3. Authentication & Security

### What to Learn
| Topic | Why It Matters | Where It's Used |
|-------|---------------|-----------------|
| **Flask-Login** | Session-based user authentication | `__init__.py`, `routes.py` |
| **Flask-Bcrypt** | Password hashing (never store plaintext!) | `routes.py` (register/login) |
| **Role-Based Access Control** | Admin vs regular user permissions | `models.py` (role field), `decorators.py` |
| **CSRF Protection** | Preventing cross-site request forgery | Flask's session-based forms |
| **Rate Limiting** | Preventing API abuse | `Flask-Limiter` in `routes.py` |

### How Auth Works in This App
```
Register → hash password with Bcrypt → store in DB
Login → check hashed password → create session → Flask-Login tracks user
Admin check → @admin_required decorator → checks user.role == "admin"
```

### Resources
- [Flask-Login Docs](https://flask-login.readthedocs.io/)
- [OWASP Auth Cheatsheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)

---

## 4. RAG Pipeline

### What is RAG?
**Retrieval-Augmented Generation** — instead of asking an LLM to answer from its training data alone, you:
1. **Upload** documents (PDFs, text files)
2. **Chunk** them into smaller pieces
3. **Embed** each chunk into a vector (numerical representation)
4. **Store** vectors in a vector database (FAISS)
5. **Retrieve** the most relevant chunks for a user's question
6. **Generate** an answer using those chunks as context

### What to Learn
| Topic | Why It Matters | Where It's Used |
|-------|---------------|-----------------|
| **Text Chunking** | Breaking documents into manageable pieces | `rag_utils.py` (`RecursiveCharacterTextSplitter`) |
| **Embeddings** | Converting text → numbers for similarity search | `rag_utils.py` (`HuggingFaceEmbeddings`) |
| **Vector Store (FAISS)** | Fast similarity search over embeddings | `rag_utils.py` (Facebook AI Similarity Search) |
| **Semantic Search** | Finding relevant chunks by meaning, not keywords | `retrieve_relevant_chunks()` |
| **Prompt Engineering** | Crafting prompts for quiz/puzzle/question generation | `build_quiz_prompt()`, etc. |
| **LangChain** | Framework for building LLM applications | Used throughout `rag_utils.py` |

### The Pipeline Visually
```
PDF Upload → Extract Text → Split into Chunks → Generate Embeddings
                                                        ↓
User Question → Embed Question → FAISS Similarity Search → Top-K Chunks
                                                        ↓
                                          Chunks + Question → LLM → Answer
```

### Resources
- [RAG Explained (YouTube)](https://www.youtube.com/results?search_query=RAG+explained+simply) — Visual learners
- [LangChain Docs](https://python.langchain.com/docs/get_started/introduction)
- [FAISS Wiki](https://github.com/facebookresearch/faiss/wiki)
- [Sentence Transformers](https://www.sbert.net/) — How embeddings work

---

## 5. LLM Integration

### What to Learn
| Topic | Why It Matters | Where It's Used |
|-------|---------------|-----------------|
| **Ollama** | Run LLMs locally (Llama 3.2, etc.) | `rag_utils.py` |
| **Google Gemini API** | Cloud-based LLM alternative | `rag_utils.py` (fallback) |
| **Prompt Engineering** | Getting structured output (JSON) from LLMs | `build_quiz_prompt()`, `build_puzzle_prompt()`, `build_questions_prompt()` |
| **JSON Output Parsing** | Extracting structured data from LLM text | `parseJSON()` in JS files |

### Prompt Engineering Tips Used
```python
# 1. Be specific about format
"Return ONLY valid JSON, no markdown, no extra text."

# 2. Provide exact schema
"Return this exact JSON format: { ... }"

# 3. Set the role
"You are a quiz generator."

# 4. Constrain the source
"based ONLY on the Context below"
```

### Resources
- [Ollama](https://ollama.com/) — Run LLMs locally
- [Google AI Studio](https://aistudio.google.com/) — Gemini API playground
- [Prompt Engineering Guide](https://www.promptingguide.ai/)

---

## 6. Frontend (HTML/CSS/JS)

### What to Learn
| Topic | Why It Matters | Where It's Used |
|-------|---------------|-----------------|
| **CSS Variables** | Theming system (`--bg-primary`, `--accent-from`) | `style.css` (top of file) |
| **Glassmorphism** | Frosted glass UI effect | `.glass-card` class |
| **CSS Grid & Flexbox** | Responsive layouts | Stats grid, nav, controls |
| **CSS Animations** | `fadeUp`, `spin`, transitions | Throughout `style.css` |
| **3D CSS Transforms** | Flashcard flip effect | `.flashcard-inner` (`rotateY`) |
| **Fetch API** | Making AJAX requests from JavaScript | All JS files |
| **sessionStorage** | Persisting state across page navigations | All JS files |
| **DOM Manipulation** | Dynamically creating quiz/puzzle cards | `renderQuiz()`, `renderPuzzle()`, etc. |

### Key Pattern: Fetch + Render
```javascript
// 1. Send request to Flask
const res = await fetch('/quiz/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic, num_questions: 5 }),
});
// 2. Parse response
const data = await res.json();
// 3. Parse LLM output (may contain extra text)
const parsed = parseJSON(data.result);
// 4. Build UI dynamically
renderQuiz(parsed.questions);
// 5. Save state
sessionStorage.setItem('key', JSON.stringify(state));
```

### Resources
- [MDN Web Docs](https://developer.mozilla.org/) — The definitive web reference
- [CSS Tricks](https://css-tricks.com/) — CSS techniques
- [JavaScript.info](https://javascript.info/) — Modern JS tutorial

---

## 7. Docker & Deployment

### What to Learn
| Topic | Why It Matters | Where It's Used |
|-------|---------------|-----------------|
| **Dockerfile** | Building a container image | `Dockerfile` |
| **docker-compose** | Multi-service orchestration | `docker-compose.yml` |
| **Volumes** | Persistent data across container restarts | `DOCKER.md` |
| **Environment Variables** | Configuration without hardcoding secrets | `.env.example` |
| **Gunicorn** | Production WSGI server (vs Flask dev server) | `Dockerfile` |
| **Nginx** | Reverse proxy for production | `DOCKER.md` |

### Resources
- [Docker Getting Started](https://docs.docker.com/get-started/)
- [Docker Compose Tutorial](https://docs.docker.com/compose/gettingstarted/)
- See [DOCKER.md](DOCKER.md) in this project for hands-on deployment

---

## 8. Project Architecture

```
RAG Tutor
├── app/
│   ├── __init__.py          # App factory, extensions, CLI, error handlers
│   ├── models.py            # User + Document ORM models
│   ├── config.py            # Environment config loading
│   ├── decorators.py        # @admin_required
│   ├── routes.py            # Main routes: auth, CRUD, chat, quiz, puzzle, questions
│   ├── admin_routes.py      # Admin dashboard + user management
│   ├── rag_utils.py         # RAG pipeline + prompt builders
│   ├── templates/           # Jinja2 HTML templates
│   └── static/              # CSS + JS assets
├── run.py                   # Entry point
├── requirements.txt         # Python dependencies
├── Dockerfile               # Container build
├── docker-compose.yml       # Service orchestration
└── .env.example             # Config template
```

### Data Flow
```
User uploads PDF
  → Flask saves file + creates DB record
  → rag_utils chunks text + generates embeddings
  → Stored in FAISS vector index (filtered by user_id)

User asks question / generates quiz
  → Flask route receives request
  → rag_utils retrieves relevant chunks from FAISS
  → Builds specialized prompt (chat / quiz / puzzle / questions)
  → Sends to Ollama LLM → Returns response
  → Frontend renders result + saves to sessionStorage
```

---

## 9. Recommended Learning Path

### Phase 1: Foundations (Week 1-2)
1. **Python basics** — functions, classes, decorators, `f-strings`
2. **Flask basics** — routes, templates, forms, sessions
3. **HTML/CSS** — Flexbox, Grid, CSS variables, responsive design

### Phase 2: Database & Auth (Week 3)
4. **SQL basics** — tables, relationships, queries
5. **SQLAlchemy ORM** — models, relationships, queries in Python
6. **Authentication** — hashing, sessions, Flask-Login

### Phase 3: AI & RAG (Week 4-5)
7. **What are embeddings** — word2vec concept, sentence transformers
8. **Vector databases** — FAISS, similarity search
9. **LLM basics** — what they are, how prompting works
10. **RAG pattern** — retrieval + generation combined
11. **LangChain** — framework for building LLM apps

### Phase 4: DevOps (Week 6)
12. **Git & GitHub** — version control
13. **Docker** — containerization, Dockerfile, docker-compose
14. **Deployment** — cloud VMs, Nginx, HTTPS

### Phase 5: Advanced (Ongoing)
15. **Prompt engineering** — structured output, JSON mode, few-shot
16. **Role-based access control** — decorators, middleware
17. **Frontend JavaScript** — Fetch API, DOM manipulation, sessionStorage
18. **Performance** — rate limiting, lazy loading, caching

---

## Quick Reference: Key Files to Study

| Concept | File to Read | Lines of Interest |
|---------|-------------|-------------------|
| App initialization | `app/__init__.py` | App factory, extensions |
| Database models | `app/models.py` | User roles, relationships |
| Authentication | `app/routes.py` | register, login functions |
| RAG pipeline | `app/rag_utils.py` | Chunking, embedding, retrieval |
| Prompt engineering | `app/rag_utils.py` | `build_quiz_prompt()` and friends |
| Admin system | `app/admin_routes.py` | Role checks, user management |
| Frontend interactivity | `app/static/js/quiz.js` | Fetch, DOM, sessionStorage |
| CSS design system | `app/static/css/style.css` | Variables, glassmorphism |
| Docker setup | `Dockerfile` + `docker-compose.yml` | Build & orchestrate |

---

> **💡 Tip:** The best way to learn is to read the code, change something, and see what happens. Start with `routes.py` — follow a request from the URL to the template and back!
