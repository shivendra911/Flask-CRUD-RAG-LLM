from datetime import datetime, timezone
from flask_login import UserMixin
from app import db


class User(UserMixin, db.Model):
    """Registered user account."""

    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    # Virtual relationship — not a real column in the table
    documents = db.relationship(
        "Document", backref="owner", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User {self.username}>"


class Document(db.Model):
    """Metadata record for an uploaded file."""

    __tablename__ = "document"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(300), nullable=False)       # UUID-safe name on disk
    original_name = db.Column(db.String(300), nullable=False)  # user-facing name
    upload_date = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False
    )

    def __repr__(self):
        return f"<Document {self.original_name}>"
