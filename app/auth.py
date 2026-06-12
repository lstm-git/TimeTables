"""Sign-in.

Two modes, chosen automatically:
  - Entra ID (Microsoft) when AZURE_CLIENT_ID is configured — users sign in
    with their LSTM account; access is controlled by the Enterprise App
    assignment in Azure.
  - Dev mode otherwise — a plain name/email form, for local development only.
"""
from functools import wraps

from flask import (Blueprint, current_app, redirect, render_template, request,
                   session, url_for)

bp = Blueprint("auth", __name__)


def azure_enabled():
    return bool(current_app.config.get("AZURE_CLIENT_ID"))


def current_user():
    return session.get("user")


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("auth.login", next=request.full_path))
        return f(*args, **kwargs)
    return wrapper


def _msal_app():
    import msal
    cfg = current_app.config
    return msal.ConfidentialClientApplication(
        cfg["AZURE_CLIENT_ID"],
        client_credential=cfg["AZURE_CLIENT_SECRET"],
        authority=cfg["AZURE_AUTHORITY"],
    )


@bp.route("/login", methods=["GET", "POST"])
def login():
    next_url = request.args.get("next") or url_for("main.index")

    if azure_enabled():
        flow = _msal_app().initiate_auth_code_flow(
            scopes=[],
            redirect_uri=url_for("auth.callback", _external=True),
        )
        session["auth_flow"] = flow
        session["next_url"] = next_url
        return redirect(flow["auth_uri"])

    # Dev mode: simple form.
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        if name:
            session["user"] = {"name": name, "email": email}
            return redirect(request.form.get("next") or url_for("main.index"))
    return render_template("login.html", next=next_url)


@bp.route("/auth/callback")
def callback():
    result = _msal_app().acquire_token_by_auth_code_flow(
        session.pop("auth_flow", {}), request.args
    )
    if "error" in result:
        return f"Sign-in failed: {result.get('error_description')}", 403
    claims = result["id_token_claims"]
    session["user"] = {
        "name": claims.get("name", "Unknown"),
        "email": claims.get("preferred_username", ""),
    }
    return redirect(session.pop("next_url", url_for("main.index")))


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
