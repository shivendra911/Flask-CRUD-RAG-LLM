from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def admin_required(f):
    """Decorator that requires the current user to be an admin.
    Must be used AFTER @login_required (or it will stack both checks).
    """

    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)

    return decorated_function
