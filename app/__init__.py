"""AISCaMS application factory.

AI-Enabled Smart Campus Management System - Flask + SQLite implementation.
"""

import click
from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   url_for)

from . import database
from .config import CONFIGS
from .domain.users import Permission
from .exceptions import AiscamsError
from .utils import human_time, now

__version__ = "1.0.0"

#: Sidebar navigation, filtered by the permissions of the signed in role.
NAV_ITEMS = (
    ("views.dashboard", "Dashboard", "grid", None),
    ("views.schedule", "Academic schedule", "calendar", Permission.VIEW_SCHEDULE),
    ("views.facilities", "Campus facilities", "search", Permission.SEARCH_RESOURCES),
    ("views.recommendations", "Smart recommendations", "sparkle",
     Permission.VIEW_RECOMMENDATIONS),
    ("views.bookings", "My bookings", "bookmark", Permission.BOOK_RESOURCE),
    ("views.requests_page", "Service requests", "wrench", Permission.TRACK_REQUEST),
    ("views.maintenance", "Maintenance workspace", "tools",
     Permission.UPDATE_REQUEST_STATUS),
    ("views.iot", "IoT monitoring", "signal", Permission.VIEW_IOT),
    ("views.security", "Security operations", "shield", Permission.MONITOR_PARKING),
    ("views.events", "Campus events", "star", Permission.VIEW_EVENTS),
    ("views.admin", "Administration", "settings", Permission.VIEW_ANALYTICS),
    ("views.notifications", "Notifications", "bell", None),
)


def create_app(config_name="default", **overrides):
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(CONFIGS.get(config_name, CONFIGS["default"]))
    app.config.update(overrides)

    database.init_app(app)
    _register_blueprints(app)
    _register_errors(app)
    _register_context(app)
    _register_cli(app)
    return app


def _register_blueprints(app):
    from .routes import api, auth, views

    app.register_blueprint(auth.bp)
    app.register_blueprint(views.bp)
    app.register_blueprint(api.bp)


def _register_errors(app):
    @app.errorhandler(AiscamsError)
    def handle_domain_error(error):
        if request.path.startswith("/api/") or request.is_json:
            return jsonify(error.to_dict()), error.status_code
        flash(error.message, "error")
        return redirect(request.referrer or url_for("views.dashboard"))

    @app.errorhandler(404)
    def handle_missing(error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "NotFound", "message": "Unknown endpoint."}), 404
        return render_template("error.html", code=404,
                               message="The page you asked for does not exist."), 404

    @app.errorhandler(500)
    def handle_server_error(error):  # pragma: no cover - defensive
        if request.path.startswith("/api/"):
            return jsonify({"error": "ServerError",
                            "message": "Unexpected server error."}), 500
        return render_template("error.html", code=500,
                               message="Something went wrong on the server."), 500


def _register_context(app):
    from .security import current_user, get_facade

    @app.context_processor
    def inject_globals():
        user = current_user()
        items = []
        if user is not None:
            for endpoint, label, icon, permission in NAV_ITEMS:
                if permission is None or user.has_permission(permission):
                    items.append({"endpoint": endpoint, "label": label, "icon": icon})
        unread = 0
        if user is not None:
            unread = get_facade().repos.notifications.unread_count(user.id)
        return {
            "current_user": user,
            "nav_items": items,
            "unread_notifications": unread,
            "app_version": __version__,
            "current_year": now().year,
        }

    app.jinja_env.filters["human_time"] = human_time


def _register_cli(app):
    @app.cli.command("init-db")
    def init_db_command():
        """Create the SQLite schema (safe to run repeatedly)."""
        connection = database.connect(app.config["DATABASE_PATH"])
        database.init_schema(connection)
        connection.close()
        click.echo("Schema ready at %s" % app.config["DATABASE_PATH"])

    @app.cli.command("seed")
    def seed_command():
        """Insert the deterministic demo campus (idempotent)."""
        from .seed import seed_database, summary

        connection = database.connect(app.config["DATABASE_PATH"])
        seed_database(connection)
        counts = summary(connection)
        connection.close()
        for table, total in counts.items():
            click.echo("%-22s %d" % (table, total))
