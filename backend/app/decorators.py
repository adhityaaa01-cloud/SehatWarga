from functools import wraps
from flask import abort
from flask_login import current_user
from app.extensions import login_manager


def role_required(*allowed_roles):
    """
    Decorator to restrict route access to authenticated users with specific roles.
    If not authenticated, triggers login_manager.unauthorized() (redirects to login).
    If authenticated but role does not match, aborts with 403 Forbidden.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if not current_user.is_active or current_user.role not in allowed_roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
