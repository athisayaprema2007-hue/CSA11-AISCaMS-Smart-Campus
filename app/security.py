"""Session handling and role based access control helpers."""

from functools import wraps

from flask import current_app, flash, g, jsonify, redirect, request, session, url_for

from .database import get_db
from .exceptions import PermissionDeniedError
from .services.campus_facade import CampusFacade

SESSION_KEY = "user_id"


def get_facade():
    """One `CampusFacade` per request, sharing the request's connection."""
    if "facade" not in g:
        g.facade = CampusFacade(get_db())
    return g.facade


def login_user(user):
    session.clear()
    session[SESSION_KEY] = user.id
    session["role"] = user.role
    return user


def logout_user():
    session.clear()


def current_user():
    """The signed in `User` (concrete subclass) or None."""
    if "user" not in g:
        user_id = session.get(SESSION_KEY)
        g.user = get_facade().user(user_id) if user_id else None
    return g.user


def wants_json():
    return request.path.startswith("/api/") or request.is_json


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            if wants_json():
                return jsonify({"error": "AuthenticationError",
                                "message": "Sign in to continue."}), 401
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def permission_required(permission):
    """Refuse the request when the signed in role lacks the permission."""
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user.has_permission(permission):
                if wants_json():
                    error = PermissionDeniedError(
                        "%s users are not allowed to perform this action."
                        % user.role.title())
                    return jsonify(error.to_dict()), error.status_code
                flash("Your role (%s) cannot open that page." % user.role.title(), "error")
                return redirect(url_for("views.dashboard"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            user = current_user()
            if user.role not in roles:
                if wants_json():
                    error = PermissionDeniedError(
                        "This action is restricted to: %s." % ", ".join(roles))
                    return jsonify(error.to_dict()), error.status_code
                flash("That area is restricted to: %s." % ", ".join(r.title() for r in roles),
                      "error")
                return redirect(url_for("views.dashboard"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


def demo_accounts():
    """Demo accounts offered on the sign in screen (one per role)."""
    facade = get_facade()
    accounts = []
    for role in ("STUDENT", "FACULTY", "ADMIN", "SECURITY", "MAINTENANCE"):
        users = sorted(facade.repos.users.list_users(role=role, active_only=True),
                       key=lambda item: item.id)
        if users:
            user = users[0]
            accounts.append({"username": user.username, "full_name": user.full_name,
                             "role": user.role, "job_title": user.job_title,
                             "password": current_app.config["DEMO_PASSWORD"]})
    return accounts
