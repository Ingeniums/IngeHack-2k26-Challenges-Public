#!/usr/bin/env python3

import os
import string
from pathlib import Path

from pwn import PIPE, context, process

context.log_level = "error"

SOLVE_DIR = Path(__file__).resolve().parent
MAIN_BIN = SOLVE_DIR / "main"
PRELOAD_SO = SOLVE_DIR / "preload.so"
TARGET_FILE = SOLVE_DIR / "flag_cmp.txt"
WORK_FILE = SOLVE_DIR / ".bf_work.bin"

# Typical CTF flag alphabet first, then fallback to full byte range.
PRIMARY_ALPHABET = (
    string.ascii_lowercase
    + string.ascii_uppercase
    + string.digits
    + "_{}-!@#$%^&*().,:"
).encode()
BYTE_ORDER = list(PRIMARY_ALPHABET) + [b for b in range(256) if b not in PRIMARY_ALPHABET]
ENC_CACHE = {}


def compile_preload() -> None:
    io = process(
        ["bash", "compile.sh"],
        cwd=str(SOLVE_DIR),
        stdin=PIPE,
        stdout=PIPE,
        stderr=PIPE,
    )
    out = io.recvall(timeout=2)
    io.wait_for_close()
    if io.poll() != 0:
        raise SystemExit(f"compile.sh failed:\n{out.decode(errors='ignore')}")


def encrypt(data: bytes) -> bytes:
    if data in ENC_CACHE:
        return ENC_CACHE[data]

    WORK_FILE.write_bytes(data)
    env = os.environ.copy()
    env["LD_PRELOAD"] = str(PRELOAD_SO)

    io = process(
        [str(MAIN_BIN), str(WORK_FILE)],
        cwd=str(SOLVE_DIR),
        env=env,
        stdin=PIPE,
        stdout=PIPE,
        stderr=PIPE,
    )
    io.recvall(timeout=2)
    io.wait_for_close()
    if io.poll() != 0:
        raise RuntimeError("main failed")
    out = WORK_FILE.read_bytes()
    ENC_CACHE[data] = out
    return out


def find_candidates(prefix: bytes, target: bytes, index: int) -> list[int]:
    want = target[: index + 1]
    out = []
    for b in BYTE_ORDER:
        enc = encrypt(prefix + bytes([b]))
        if enc[: index + 1] == want:
            out.append(b)
    return out


def recover(prefix: bytes, target: bytes) -> bytes | None:
    index = len(prefix)
    if index >= len(target):
        return prefix

    cands = find_candidates(prefix, target, index)
    if not cands:
        return None

    for b in cands:
        nxt = prefix + bytes([b])
        try:
            view = nxt.decode()
        except UnicodeDecodeError:
            view = nxt.decode("latin-1")
        print(f"[{index:02d}] {view!r}", flush=True)

        if b == ord("}") and nxt.startswith(b"ingehack{"):
            return nxt

        got = recover(nxt, target)
        if got is not None:
            return got

    return None


def main() -> int:
    compile_preload()

    target = TARGET_FILE.read_bytes()
    recovered = b"ingehack{"

    # Validate known prefix first.
    enc_prefix = encrypt(recovered)
    if enc_prefix != target[: len(recovered)]:
        raise SystemExit("known prefix does not match target ciphertext")

    print(f"[+] starting from known prefix: {recovered.decode()}", flush=True)
    out = recover(recovered, target)
    if out is None:
        raise SystemExit("failed to recover flag")

    try:
        flag = out.decode()
    except UnicodeDecodeError:
        flag = out.decode("latin-1")

    print(f"[+] flag: {flag}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
