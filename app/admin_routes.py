import os

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    current_app,
)
from flask_login import current_user

from app import db
from app.decorators import admin_required
from app.models import User, Document

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  ADMIN DASHBOARD                                                   ║
# ╚══════════════════════════════════════════════════════════════════════╝

@admin_bp.route("/")
@admin_required
def dashboard():
    users = User.query.order_by(User.id).all()
    total_users = len(users)
    total_docs = Document.query.count()

    # Build user stats
    user_stats = []
    for user in users:
        doc_count = Document.query.filter_by(user_id=user.id).count()
        user_stats.append({
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "doc_count": doc_count,
        })

    return render_template(
        "admin/dashboard.html",
        user_stats=user_stats,
        total_users=total_users,
        total_docs=total_docs,
    )


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  TOGGLE USER ROLE                                                  ║
# ╚══════════════════════════════════════════════════════════════════════╝

@admin_bp.route("/users/<int:user_id>/toggle-role", methods=["POST"])
@admin_required
def toggle_role(user_id):
    user = User.query.get_or_404(user_id)

    # Prevent self-demotion
    if user.id == current_user.id:
        flash("You cannot change your own role.", "warning")
        return redirect(url_for("admin.dashboard"))

    user.role = "user" if user.role == "admin" else "admin"

    try:
        db.session.commit()
        flash(f'"{user.username}" is now {user.role}.', "success")
    except Exception:
        db.session.rollback()
        flash("Failed to update role.", "danger")

    return redirect(url_for("admin.dashboard"))


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  DELETE USER                                                       ║
# ╚══════════════════════════════════════════════════════════════════════╝

@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    # Prevent self-deletion
    if user.id == current_user.id:
        flash("You cannot delete your own account.", "warning")
        return redirect(url_for("admin.dashboard"))

    username = user.username

    # Delete user's uploaded files from disk
    for doc in user.documents:
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], doc.filename)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except OSError:
            pass

    try:
        db.session.delete(user)  # cascade deletes documents
        db.session.commit()
        flash(f'User "{username}" and all their data deleted.', "success")
    except Exception:
        db.session.rollback()
        flash("Failed to delete user.", "danger")

    return redirect(url_for("admin.dashboard"))
