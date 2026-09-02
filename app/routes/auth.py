"""Authentication routes: sign in, demo role selection and sign out."""

from flask import (Blueprint, current_app, flash, redirect, render_template,
                   request, url_for)

from ..exceptions import AuthenticationError
from ..security import current_user, demo_accounts, login_user, logout_user

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user() is not None:
        return redirect(url_for("views.dashboard"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        try:
            from ..security import get_facade
            user = get_facade().authenticate(username, password)
            login_user(user)
            flash("Signed in as %s (%s)." % (user.full_name, user.job_title), "success")
            return redirect(request.args.get("next") or url_for("views.dashboard"))
        except AuthenticationError as exc:
            error = exc.message
    return render_template("login.html", error=error, accounts=demo_accounts(),
                           demo_password=current_app.config["DEMO_PASSWORD"])


@bp.route("/login/demo/<username>")
def demo_login(username):
    """Safe demo role selection: signs in one of the seeded demo accounts."""
    from ..security import get_facade

    allowed = {account["username"] for account in demo_accounts()}
    if username not in allowed:
        flash("Unknown demo account.", "error")
        return redirect(url_for("auth.login"))
    try:
        user = get_facade().authenticate(username, current_app.config["DEMO_PASSWORD"])
    except AuthenticationError as exc:
        flash(exc.message, "error")
        return redirect(url_for("auth.login"))
    login_user(user)
    flash("Signed in as %s (%s)." % (user.full_name, user.job_title), "success")
    return redirect(url_for("views.dashboard"))


@bp.route("/logout")
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))
