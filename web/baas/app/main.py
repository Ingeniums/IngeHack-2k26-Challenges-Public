from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

import requests
from flask import Flask, Response, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix

APP_NAME = "BAAS"
PORT = int(os.getenv("PORT", "9898"))
FLAG = os.getenv("FLAG", "ingehack{l0c4lh0st_1s_st1ll_4_pl4c3_y0u_c4n_br0ws3}")
SESSION_SECRET = os.getenv("SESSION_SECRET", "baas-dev-secret")
PUBLIC_ORIGIN = os.getenv("PUBLIC_ORIGIN", "https://baas.ctf.ingeniums.club").strip()
INTERNAL_FETCH_TOKEN = os.getenv("INTERNAL_FETCH_TOKEN", "baas-dev-fetch-token")
BASE_DIR = os.path.dirname(__file__)

BROWSER_FACTS: list[dict[str, Any]] = [
    {
        "name": "Chromium Drift",
        "engine": "Blink",
        "share": "65.1%",
        "note": "Leads synthetic benchmark runs across desktop test rigs.",
    },
    {
        "name": "Foxhound Mobile",
        "engine": "Gecko",
        "share": "18.4%",
        "note": "Still favored by privacy-focused teams for debugging sessions.",
    },
    {
        "name": "Safari Coast",
        "engine": "WebKit",
        "share": "13.2%",
        "note": "Strong battery numbers, weaker extension support in the lab.",
    },
    {
        "name": "Arc Static",
        "engine": "Blink",
        "share": "3.3%",
        "note": "Low adoption, high enthusiasm, dramatic tab management demos.",
    },
]

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
app.secret_key = SESSION_SECRET
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)


def is_allowed_target(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_loopback_request() -> bool:
    remote_addr = (request.remote_addr or "").strip()
    return remote_addr in {"127.0.0.1", "::1"}


def has_internal_fetch_access() -> bool:
    token = request.headers.get("X-BAAS-Internal-Token", "")
    return token == INTERNAL_FETCH_TOKEN


@app.get("/")
def index():
    return render_template(
        "index.html",
        app_name=APP_NAME,
        facts=BROWSER_FACTS,
    )


@app.get("/sitemap.xml")
def sitemap():
    origin = PUBLIC_ORIGIN.rstrip("/")
    public_browser = f"{origin}/browser"
    public_delta = f"{origin}/delta-browser"
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{public_browser}</loc>
  </url>
  <url>
    <loc>{public_delta}</loc>
  </url>
</urlset>
"""
    return Response(xml, mimetype="application/xml")


@app.route("/browser", methods=["GET", "POST"])
def browser():
    target = ""
    error = None
    result = None

    if request.method == "POST":
        target = request.form.get("url", "").strip()

        if not target:
            error = "Enter a link for the browser worker."
        elif not is_allowed_target(target):
            error = "Only absolute http:// or https:// links are supported."
        else:
            try:
                response = requests.get(
                    target,
                    timeout=5,
                    headers={
                        "User-Agent": "BAAS/1.0",
                        "X-BAAS-Internal-Token": INTERNAL_FETCH_TOKEN,
                    },
                    allow_redirects=True,
                )
                result = {
                    "body": response.text[:40000],
                }
            except requests.RequestException as exc:
                error = f"Browser worker failed: {exc}"

    return render_template(
        "browser.html",
        app_name=APP_NAME,
        target=target,
        error=error,
        result=result,
    )


@app.get("/delta-browser")
def delta_browser():
    if not is_loopback_request() and not has_internal_fetch_access():
        return Response("delta browser is still under construction\n", status=403, mimetype="text/plain")

    return Response(
        f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Delta Browser</title>
  </head>
  <body>
    <h1>Delta Browser Diagnostics</h1>
    <pre>{FLAG}</pre>
  </body>
</html>
""",
        mimetype="text/html",
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
