import os
import uuid
from datetime import datetime, timezone

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    jsonify,
    current_app,
    abort,
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename

from app import db, bcrypt, limiter
from app.models import User, Document

main = Blueprint("main", __name__)


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  HELPERS                                                           ║
# ╚══════════════════════════════════════════════════════════════════════╝

def _allowed_file(filename: str) -> bool:
    """Check if the file extension is in the whitelist."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in current_app.config["ALLOWED_EXTENSIONS"]
    )


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  LANDING / HOME                                                    ║
# ╚══════════════════════════════════════════════════════════════════════╝

@main.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("main.login"))


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  AUTHENTICATION                                                    ║
# ╚══════════════════════════════════════════════════════════════════════╝

@main.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm_password", "").strip()

        # ── Validation ───────────────────────────────────────────────
        if not username or not password:
            flash("Username and password are required.", "danger")
            return redirect(url_for("main.register"))

        if len(username) < 3 or len(username) > 80:
            flash("Username must be 3–80 characters.", "danger")
            return redirect(url_for("main.register"))

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return redirect(url_for("main.register"))

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("main.register"))

        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "danger")
            return redirect(url_for("main.register"))

        # ── Create user ──────────────────────────────────────────────
        hashed = bcrypt.generate_password_hash(password).decode("utf-8")
        user = User(username=username, password_hash=hashed)

        try:
            db.session.add(user)
            db.session.commit()
            flash("Account created! Please log in.", "success")
            return redirect(url_for("main.login"))
        except Exception:
            db.session.rollback()
            flash("Registration failed. Please try again.", "danger")
            return redirect(url_for("main.register"))

    return render_template("register.html")


@main.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.dashboard"))

        flash("Invalid username or password.", "danger")
        return redirect(url_for("main.login"))

    return render_template("login.html")


@main.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.login"))


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  DASHBOARD  (Read)                                                 ║
# ╚══════════════════════════════════════════════════════════════════════╝

@main.route("/dashboard")
@login_required
def dashboard():
    # Filter by current user — multi-user isolation
    docs = (
        Document.query.filter_by(user_id=current_user.id)
        .order_by(Document.upload_date.desc())
        .all()
    )
    return render_template("dashboard.html", documents=docs)


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  UPLOAD  (Create)                                                  ║
# ╚══════════════════════════════════════════════════════════════════════╝

@main.route("/upload", methods=["POST"])
@login_required
def upload():
    file = request.files.get("file")

    if not file or file.filename == "":
        flash("No file selected.", "warning")
        return redirect(url_for("main.dashboard"))

    if not _allowed_file(file.filename):
        flash("Only .pdf, .txt, and .md files are allowed.", "danger")
        return redirect(url_for("main.dashboard"))

    original_name = file.filename
    safe_name = (
        str(uuid.uuid4()) + "_" + secure_filename(original_name)
    )
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], safe_name)

    # Step 1 — save file to disk (outside DB transaction)
    file.save(filepath)

    # Steps 2 + 3 — DB record + vector storage wrapped in transaction
    try:
        new_doc = Document(
            filename=safe_name,
            original_name=original_name,
            upload_date=datetime.now(timezone.utc),
            user_id=current_user.id,
        )
        db.session.add(new_doc)
        db.session.flush()  # get new_doc.id without committing yet

        # Chunk & embed into ChromaDB
        try:
            from app.rag_utils import load_and_chunk, store_chunks

            chunks = load_and_chunk(filepath)
            if chunks:
                date_str = new_doc.upload_date.strftime("%Y-%m-%d %H:%M:%S UTC")
                store_chunks(
                    chunks, 
                    current_user.id, 
                    new_doc.id,
                    filename=original_name,
                    upload_date=date_str
                )
        except Exception as rag_err:
            current_app.logger.warning(f"RAG processing skipped: {rag_err}")

        db.session.commit()
        flash(f'"{original_name}" uploaded successfully!', "success")

    except Exception as e:
        db.session.rollback()
        # Clean up the file we already saved
        if os.path.exists(filepath):
            os.remove(filepath)
        current_app.logger.error(f"Upload failed: {e}")
        flash("Upload failed. Please try again.", "danger")

    return redirect(url_for("main.dashboard"))


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  DELETE  (Delete)                                                  ║
# ╚══════════════════════════════════════════════════════════════════════╝

@main.route("/delete/<int:doc_id>", methods=["POST"])
@login_required
def delete_document(doc_id):
    doc = Document.query.get_or_404(doc_id)

    # ── Ownership check — NEVER skip this ─────────────────────────────
    if doc.user_id != current_user.id:
        abort(403)

    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], doc.filename)
    saved_doc_id = str(doc.id)
    saved_name = doc.original_name

    # Step 1 — delete SQL record (atomic)
    try:
        db.session.delete(doc)
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Delete failed.", "danger")
        return redirect(url_for("main.dashboard"))

    # Step 2 — clean up file (best-effort after SQL commit)
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except OSError:
        pass

    # Step 3 — clean up vectors (best-effort)
    try:
        from app.rag_utils import delete_chunks

        delete_chunks(saved_doc_id)
    except Exception:
        pass

    flash(f'"{saved_name}" deleted.', "success")
    return redirect(url_for("main.dashboard"))


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  CHAT  (AI Tutor)                                                 ║
# ╚══════════════════════════════════════════════════════════════════════╝

@main.route("/chat")
@login_required
def chat_page():
    return render_template("chat.html")


@main.route("/chat", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def chat():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request."}), 400

    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "Empty question."}), 400

    try:
        from app.rag_utils import (
            retrieve_relevant_chunks,
            build_prompt,
            generate_answer,
        )

        chunks = retrieve_relevant_chunks(question, current_user.id)

        if not chunks:
            return jsonify(
                {
                    "answer": "No relevant documents found. "
                    "Try uploading some notes first!"
                }
            )

        prompt = build_prompt(question, chunks)
        answer = generate_answer(prompt)
        return jsonify({"answer": answer})

    except Exception as e:
        error_str = str(e).lower()
        is_rate_limit = (
            "429" in str(e)
            or "resourceexhausted" in type(e).__name__.lower()
            or "resource_exhausted" in error_str
            or "quota" in error_str
        )
        if is_rate_limit:
            return jsonify(
                {
                    "answer": "⏳ API rate limit reached. The free tier has limited daily requests. "
                    "Please wait a minute and try again."
                }
            )
        current_app.logger.error(f"Chat error: {e}")
        return jsonify(
            {"error": "Something went wrong. Please try again."}
        ), 500


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  QUIZ GENERATOR                                                    ║
# ╚══════════════════════════════════════════════════════════════════════╝

@main.route("/quiz")
@login_required
def quiz_page():
    return render_template("quiz.html")


@main.route("/quiz/generate", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def quiz_generate():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request."}), 400

    num_questions = min(int(data.get("num_questions", 5)), 10)
    topic = data.get("topic", "").strip()

    try:
        from app.rag_utils import (
            retrieve_relevant_chunks,
            build_quiz_prompt,
            generate_answer,
        )

        query = topic if topic else "key concepts and important topics"
        chunks = retrieve_relevant_chunks(query, current_user.id, k=6)

        if not chunks:
            return jsonify({"error": "No documents found. Upload some files first!"})

        prompt = build_quiz_prompt(chunks, num_questions, topic)
        result = generate_answer(prompt)
        return jsonify({"result": result})

    except Exception as e:
        current_app.logger.error(f"Quiz generation error: {e}")
        return jsonify({"error": "Failed to generate quiz. Please try again."}), 500


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  PUZZLE GENERATOR                                                  ║
# ╚══════════════════════════════════════════════════════════════════════╝

@main.route("/puzzle")
@login_required
def puzzle_page():
    return render_template("puzzle.html")


@main.route("/puzzle/generate", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def puzzle_generate():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request."}), 400

    puzzle_type = data.get("type", "fill_blank")
    count = min(int(data.get("count", 8)), 12)

    try:
        from app.rag_utils import (
            retrieve_relevant_chunks,
            build_puzzle_prompt,
            generate_answer,
        )

        chunks = retrieve_relevant_chunks("important concepts and key terms", current_user.id, k=6)

        if not chunks:
            return jsonify({"error": "No documents found. Upload some files first!"})

        prompt = build_puzzle_prompt(chunks, puzzle_type, count)
        result = generate_answer(prompt)
        return jsonify({"result": result})

    except Exception as e:
        current_app.logger.error(f"Puzzle generation error: {e}")
        return jsonify({"error": "Failed to generate puzzle. Please try again."}), 500


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  QUESTION BANK                                                     ║
# ╚══════════════════════════════════════════════════════════════════════╝

@main.route("/questions")
@login_required
def questions_page():
    return render_template("questions.html")


@main.route("/questions/generate", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def questions_generate():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request."}), 400

    q_type = data.get("type", "short_answer")
    count = min(int(data.get("count", 6)), 10)

    try:
        from app.rag_utils import (
            retrieve_relevant_chunks,
            build_questions_prompt,
            generate_answer,
        )

        chunks = retrieve_relevant_chunks("key concepts and study material", current_user.id, k=6)

        if not chunks:
            return jsonify({"error": "No documents found. Upload some files first!"})

        prompt = build_questions_prompt(chunks, q_type, count)
        result = generate_answer(prompt)
        return jsonify({"result": result})

    except Exception as e:
        current_app.logger.error(f"Questions generation error: {e}")
        return jsonify({"error": "Failed to generate questions. Please try again."}), 500
