import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # Database — defaults to SQLite, overridable via DATABASE_URL for PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///app.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # PostgreSQL connection pooling (ignored by SQLite)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }

    # File uploads
    UPLOAD_FOLDER = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "uploads"
    )
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20 MB
    ALLOWED_EXTENSIONS = {"pdf", "txt", "md"}

    # Gemini API
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
