# RAG Tutor 🧠

A multi-user **Retrieval Augmented Generation** application built with Flask. Upload your PDFs, text files, or markdown notes — then chat with an AI tutor that answers **only from your documents**.

## ✨ Features

- **User Authentication** — Register, login, logout with bcrypt password hashing
- **Document Management** — Upload, view, and delete files (PDF, TXT, MD)
- **RAG Pipeline** — Text extraction → chunking → embedding → vector storage
- **AI Chat** — Ask questions answered exclusively from your uploaded documents
- **Multi-User Isolation** — Each user's documents and vectors are completely separate
- **ACID Transaction Safety** — Proper rollback handling for uploads and deletes
- **Rate Limiting** — Protects the chat endpoint from abuse
- **Docker Ready** — One-command deployment with persistent volumes
- **Premium Dark UI** — Glassmorphism design with micro-animations

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask, SQLAlchemy, Flask-Login, Flask-Bcrypt |
| Database | SQLite (dev) / PostgreSQL (prod) |
| RAG | LangChain, ChromaDB, PyPDF |
| LLM | Google Gemini 1.5 Flash (free tier) |
| Embeddings | Gemini text-embedding-004 (free) |
| Deployment | Docker, Gunicorn, Nginx |

## 🚀 Quick Start

### 1. Clone & setup environment

```bash
git clone https://github.com/shivendra911/Flask-CRUD-RAG-LLM.git
cd Flask-CRUD-RAG-LLM

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
copy .env.example .env
# Edit .env and add your GEMINI_API_KEY
# Get one free at: https://aistudio.google.com/apikey
```

### 3. Run the application

```bash
python run.py
```

Visit **http://localhost:5000** — register, upload a PDF, and start chatting!

### 4. Docker deployment (optional)

```bash
docker compose up -d --build
```

## 📁 Project Structure

```
├── app/
│   ├── __init__.py         # Flask app factory
│   ├── config.py           # Environment-based configuration
│   ├── models.py           # User & Document models
│   ├── routes.py           # Auth, CRUD, and Chat routes
│   ├── rag_utils.py        # Chunking, embedding, retrieval, generation
│   ├── static/css/         # Premium dark theme styles
│   ├── static/js/          # Chat interface JavaScript
│   ├── templates/          # Jinja2 HTML templates
│   └── uploads/            # User-uploaded files (gitignored)
├── run.py                  # App entry point
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container build
├── docker-compose.yml      # Full stack orchestration
├── nginx.conf              # Reverse proxy template
└── .env.example            # Environment variable template
```

## 📄 License

MIT