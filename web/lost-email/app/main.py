from __future__ import annotations

import os

from flask import Flask, flash, redirect, render_template, request, session, url_for

APP_NAME = "ingebank"
PORT = int(os.getenv("PORT"))
FLAG = os.getenv("FLAG")
SESSION_SECRET = os.getenv("SESSION_SECRET")

USERS = {
    "koyphshi@ingenieums.club": {
        "password": "anti_ai_human",
        "username": "koyphshi",
        "display_name": "koyphshi",
        "account_name": "Ingenieums Personal Reserve",
        "balance": "$12,480.90",
    }
}

app = Flask(__name__)
app.secret_key = SESSION_SECRET


def mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if not local or not domain:
        return "your email"
    if len(local) <= 2:
        masked_local = local[0] + "*"
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{masked_local}@{domain}"


def current_user() -> dict[str, str] | None:
    email = session.get("user")
    if not isinstance(email, str):
        return None
    user = USERS.get(email)
    if not user:
        session.clear()
        return None
    return {"email": email, **user}


@app.get("/")
def index():
    user = current_user()
    return render_template("index.html", app_name=APP_NAME, user=user)


@app.get("/profile")
def profile():
    user = current_user()
    if not user:
        flash("Login first to access your banking profile.", "error")
        return redirect(url_for("login_page"))

    return render_template(
        "profile.html",
        app_name=APP_NAME,
        flag=FLAG,
        user=user,
        mfa_pending=bool(session.get("mfa_pending")),
    )


@app.get("/login")
def login_page():
    if current_user():
        return redirect(url_for("verify_page"))
    return render_template("login.html", app_name=APP_NAME)


@app.post("/login")
def login():
    username = request.form.get("user", "").strip().lower()
    password = request.form.get("pass", "")
    user = USERS.get(username)

    if not user or password != user["password"]:
        session.clear()
        flash("Invalid user or password.", "error")
        return redirect(url_for("login_page"))

    session.clear()
    session["user"] = username
    session["email"] = username
    session["mfa_pending"] = True
    session["mfa_verified"] = False
    flash("Password accepted. Enter the number sent to your email.", "success")
    return redirect(url_for("verify_page"))


@app.get("/verify")
def verify_page():
    user = current_user()
    if not user:
        flash("Login first to request an email code.", "error")
        return redirect(url_for("login_page"))

    return render_template(
        "verify.html",
        app_name=APP_NAME,
        masked_email=mask_email(user["email"]),
    )


@app.post("/verify")
def verify():
    code = request.form.get("code", "").strip()
    if not session.get("user"):
        flash("Your login session expired.", "error")
        return redirect(url_for("index"))

    session.clear()
    if code:
        flash("That email code is wrong or expired. Please log in again.", "error")
    else:
        flash("Email code required. Please log in again.", "error")
    return redirect(url_for("index"))


@app.post("/logout")
def logout():
    session.clear()
    flash("Signed out.", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
