from __future__ import annotations

import os
from typing import Any, Mapping

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from db import (
    AlreadyClaimedError,
    UserNotFoundError,
    claim_bonus_for_user,
    create_user,
    get_user_by_id,
    get_user_by_username,
    init_db,
    wallet_for_owner,
)

APP_NAME = "Mario Kart Garage"
PORT = int(os.getenv("PORT"))
SESSION_SECRET = os.getenv("SESSION_SECRET")
FLAG = os.getenv("FLAG")
WELCOME_BONUS_CENTS = 1000
TARGET_ITEM_PRICE_CENTS = 4200
TARGET_ITEM_ID = "rainbow-road-golden-kart"
PRODUCTS = [
    {
        "id": "banana-bunch",
        "name": "Banana Bunch",
        "description": "A bright yellow pack for defensive driving.",
        "price_cents": 700,
    },
    {
        "id": "blue-shell-turbo",
        "name": "Blue Shell Turbo",
        "description": "A collector shell with a sharp burst of speed.",
        "price_cents": 1800,
    },
    {
        "id": TARGET_ITEM_ID,
        "name": "Rainbow Road Golden Kart",
        "description": "The premium garage item every racer wants.",
        "price_cents": TARGET_ITEM_PRICE_CENTS,
    },
]

app = Flask(__name__)
app.secret_key = SESSION_SECRET


def read_input() -> dict[str, Any]:
    payload = request.get_json(silent=True)
    if isinstance(payload, dict):
        return payload
    if request.form:
        return request.form.to_dict(flat=True)
    return {}


def normalize_username(value: object) -> str:
    return str(value or "").strip().lower()


def money(cents: int) -> str:
    return f"${cents / 100:.2f}"


def user_payload(user: Mapping[str, Any]) -> dict[str, Any]:
    return {"id": user["id"], "username": user["username"]}


def current_user() -> Mapping[str, Any] | None:
    user_id = session.get("user_id")
    if not isinstance(user_id, int):
        return None

    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
    return user


def auth_error(message: str, status_code: int = 401):
    return jsonify({"ok": False, "error": message}), status_code


def wants_json_response() -> bool:
    return request.is_json or request.accept_mimetypes.best == "application/json"


def products_payload() -> list[dict[str, Any]]:
    return [{**product, "price": money(product["price_cents"])} for product in PRODUCTS]


def create_account(username: str, password: str) -> tuple[dict[str, Any], int]:
    username = normalize_username(username)

    if len(password) < 4:
        return {"ok": False, "error": "password must be at least 4 chars"}, 400

    if get_user_by_username(username):
        return {"ok": False, "error": "username already exists"}, 409

    password_hash = generate_password_hash(password)
    user_id = create_user(username, password_hash)

    session.clear()
    session["user_id"] = user_id
    return {
        "ok": True,
        "message": "account created",
        "user": {"id": user_id, "username": username},
    }, 201


def authenticate(username: str, password: str) -> tuple[dict[str, Any], int]:
    username = normalize_username(username)

    if not username or not password:
        return {"ok": False, "error": "username and password are required"}, 400

    user = get_user_by_username(username)
    if user and check_password_hash(user["password_hash"], password):
        session.clear()
        session["user_id"] = int(user["id"])
        return {"ok": True, "message": "logged in", "user": user_payload(user)}, 200

    return {"ok": False, "error": "invalid credentials"}, 401


def purchase_target_item(user: Mapping[str, Any]) -> tuple[dict[str, Any], int]:
    wallet = wallet_for_owner(user["username"])
    if wallet["balance_cents"] < TARGET_ITEM_PRICE_CENTS:
        return {"ok": False, "error": "insufficient wallet balance"}, 403

    return {"ok": True, "flag": FLAG}, 200


@app.get("/")
def index():
    user = current_user()
    if user is None:
        return redirect(url_for("login_page"))

    wallet = wallet_for_owner(user["username"])
    return render_template(
        "index.html",
        app_name=APP_NAME,
        user=user,
        wallet=wallet,
        claimed=bool(user["bonus_claimed"]),
        bonus=money(WELCOME_BONUS_CENTS),
        target=money(TARGET_ITEM_PRICE_CENTS),
        products=products_payload(),
        target_item_id=TARGET_ITEM_ID,
    )


@app.get("/register")
def register_page():
    if current_user():
        return redirect(url_for("index"))
    return render_template("register.html", app_name=APP_NAME, user=None, bonus=money(WELCOME_BONUS_CENTS))


@app.post("/register")
def register_form():
    data = read_input()
    result, status = create_account(
        data.get("username", ""),
        str(data.get("password", "")),
    )
    if wants_json_response():
        return jsonify(result), status

    if not result["ok"]:
        flash(result["error"], "error")
        return redirect(url_for("register_page"))

    return redirect(url_for("index"))


@app.get("/login")
def login_page():
    if current_user():
        return redirect(url_for("index"))
    return render_template("login.html", app_name=APP_NAME, user=None)


@app.post("/login")
def login_form():
    data = read_input()
    result, status = authenticate(
        data.get("username", ""),
        str(data.get("password", "")),
    )
    if wants_json_response():
        return jsonify(result), status

    if not result["ok"]:
        flash(result["error"], "error")
        return redirect(url_for("login_page"))

    flash("Logged in.", "success")
    return redirect(url_for("index"))


@app.post("/logout")
def logout_form():
    session.clear()
    if wants_json_response():
        return jsonify({"ok": True, "message": "logged out"})

    flash("Logged out.", "success")
    return redirect(url_for("index"))


@app.post("/claim")
def claim_form():
    user = current_user()
    if user is None:
        if wants_json_response():
            return auth_error("login required")
        flash("Login required.", "error")
        return redirect(url_for("login_page"))

    try:
        claim_bonus_for_user(user["id"], WELCOME_BONUS_CENTS)
    except UserNotFoundError:
        session.clear()
        if wants_json_response():
            return auth_error("login required")
        flash("Login required.", "error")
        return redirect(url_for("login_page"))
    except AlreadyClaimedError:
        result = {"ok": False, "error": "garage bonus already claimed for this account"}
        if wants_json_response():
            return jsonify(result), 409
        flash(result["error"], "error")
        return redirect(url_for("index"))

    result = {"ok": True, "message": "garage bonus claimed"}
    if wants_json_response():
        return jsonify(result)

    flash(f"{money(WELCOME_BONUS_CENTS)} added to your garage wallet.", "success")
    return redirect(url_for("index"))


@app.post("/purchase")
def purchase_form():
    user = current_user()
    if user is None:
        if wants_json_response():
            return auth_error("login required")
        flash("Login required.", "error")
        return redirect(url_for("login_page"))

    data = read_input()
    item_id = str(data.get("item", TARGET_ITEM_ID))
    if item_id != TARGET_ITEM_ID:
        result = {"ok": False, "error": "only the premium kart unlocks the prize"}
        if wants_json_response():
            return jsonify(result), 400
        flash("That item is not connected to the prize vault.", "error")
        return redirect(url_for("index"))

    result, status = purchase_target_item(user)
    if wants_json_response():
        return jsonify(result), status

    if result["ok"]:
        flash(f"Purchase complete. Flag: {result['flag']}", "success")
    else:
        wallet = wallet_for_owner(user["username"])
        flash(
            f"{result['error']}: need {money(TARGET_ITEM_PRICE_CENTS)}, current balance {money(wallet['balance_cents'])}.",
            "error",
        )
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
