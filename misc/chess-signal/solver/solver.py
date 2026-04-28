from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from http.cookiejar import CookieJar


BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"

SOLVE_STEPS = [
    ("bishop-1", 169),
    ("bishop-2", 157),
    ("bishop-3", 153),
    ("queen-1", 143),
    ("queen-2", 149),
    ("queen-3", 129),
    ("knight-1", 132),
    ("knight-2", 174),
    ("king-1", 131),
    ("king-2", 176),
]


def build_opener() -> urllib.request.OpenerDirector:
    jar = CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def get_json(opener: urllib.request.OpenerDirector, path: str) -> dict:
    with opener.open(f"{BASE_URL}{path}") as response:
        return json.load(response)


def post_json(opener: urllib.request.OpenerDirector, path: str, payload: dict) -> dict:
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with opener.open(request) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        body = error.read().decode()
        raise RuntimeError(body) from error


def main() -> int:
    opener = build_opener()
    state = get_json(opener, "/api/state")
    print(f"Loaded board: {state['board_size']}x{state['board_size']}")

    reset = post_json(opener, "/api/reset", {})
    print(reset["message"])

    final_flag = None
    for piece_id, probe in SOLVE_STEPS:
        result = post_json(opener, "/api/move", {"piece_id": piece_id, "probe": probe})
        print(result["message"])
        if result.get("flag"):
            final_flag = result["flag"]

    if not final_flag:
        final_state = get_json(opener, "/api/state")
        final_flag = final_state.get("flag")

    if not final_flag:
        print("Solver did not recover a flag.")
        return 1

    print(f"Recovered flag: {final_flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
