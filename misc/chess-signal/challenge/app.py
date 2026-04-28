from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, make_response, request

from challenge import SessionStore


ROOT = Path(__file__).resolve().parent
SESSION_COOKIE = "chess_signal_sid"

app = Flask(__name__)
store = SessionStore()


def _session():
    session_id = request.cookies.get(SESSION_COOKIE)
    return store.ensure(session_id)


def _json_with_session(payload: dict, session_id: str, status: int = 200):
    response = make_response(jsonify(payload), status)
    response.set_cookie(SESSION_COOKIE, session_id, httponly=True, samesite="Lax")
    return response


@app.get("/")
def index():
    session_id, _ = _session()
    response = make_response((ROOT / "index.html").read_text(encoding="utf-8"))
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    response.set_cookie(SESSION_COOKIE, session_id, httponly=True, samesite="Lax")
    return response


@app.get("/api/state")
def api_state():
    session_id, session = _session()
    return _json_with_session(session.public_state(), session_id)


@app.post("/api/reset")
def api_reset():
    session_id, _ = _session()
    session = store.reset(session_id)
    return _json_with_session(
        {
            "ok": True,
            "message": "Session reset.",
            "state": session.public_state(),
        },
        session_id,
    )


@app.post("/api/move")
def api_move():
    session_id, session = _session()
    payload = request.get_json(silent=True) or {}
    piece_id = payload.get("piece_id", "")
    value = int(payload.get("value", -1))

    result = session.move(piece_id, value)
    status = 200 if result.ok else 400
    return _json_with_session(
        {
            "ok": result.ok,
            "message": result.message,
            "flag": result.flag,
            "state": session.public_state(),
        },
        session_id,
        status=status,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
