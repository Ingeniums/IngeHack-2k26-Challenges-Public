# jit (pwn) - Writeup

## TL;DR
The challenge is a LuaJIT program that exposes a stack machine. A bounds bug lets us read/write out of bounds on an FFI array (`uint64_t[10]`) up to index `16`. That reaches neighboring FFI objects (`STACK_STATE`, `STACK`) and gives arbitrary read/write over a large memory range. From there:

1. leak a `libluajit` code pointer,
2. resolve libc via a GOT entry (`mprotect`),
3. read `environ` from libc to locate the real C stack,
4. overwrite saved RIP with a libc ROP chain,
5. return into `system("/bin/sh")`.

A working exploit is in `solve.py`.

---

## Vulnerability
From [`main.lua`](./main.lua):

- `ARRAY` is allocated as `ffi.new("uint64_t[10]")`.
- But bounds checks use `ARRAY_SIZE = 0x10` (16).
- `set` and `get` allow `idx` in `[0, 16]`.

So indices `10..16` are out-of-bounds and overlap adjacent LuaJIT cdata allocations.

Relevant lines:
- allocation: lines 31-34
- bounds checks: lines 114-117 and 135-138
- OOB access: lines 121 and 142

---

## Why this is exploitable
The three cdata objects are allocated close together:

- `ARRAY = uint64_t[10]`
- `STACK_STATE = uint64_t[2]`
- `STACK = uint64_t[20]`

Using OOB `set/get` on `ARRAY`, we can modify/read `STACK_STATE` fields via overlapping indices.

`STACK_STATE` layout used by program logic:
- `STACK_STATE[1]` = current stack length
- `STACK_STATE[2]` = max stack length

By overwriting these through OOB writes:

- set `STACK_STATE[2]` to a huge value (`10**13`, still safe under Lua number precision limit),
- set `STACK_STATE[1]` to attacker-controlled values,

we turn `pop` into an arbitrary read primitive over memory reachable as `STACK[idx]`, and `push` into arbitrary write to the same region.

In the exploit these are wrapped as:

- `read_q(addr)`
- `write_q(addr, value)`

with address translation through leaked `stack_base`.

---

## Leak chain

### 1) Leak internal stack base
`get 16` leaks a pointer-like value in adjacent memory. For this build:

- `stack_base = leak16 + 0x38`

This base is used to convert absolute addresses into `STACK` indices.

### 2) Leak libluajit base
A stable sequence of `set 14 i` + `pop` for `i in [18..39]` ends on a `libluajit` code pointer (`...24a`).

- `luajit_base = luajit_leak - 0xC24A`

### 3) Leak libc base from luajit GOT
Read `mprotect@GOT` in `libluajit`:

- `mprotect_ptr = *(luajit_base + 0x90008)`
- `libc_base = mprotect_ptr - 0x125C40`

### 4) Find saved return address via `environ`
Read libc `environ` pointer:

- `environ_ptr = *(libc_base + 0x20AD58)`

For this challenge/runtime layout:

- saved RIP for the `lua_pcall` return path is at `environ_ptr - 0x150`
- sanity check: low 12 bits are `0x271` (`main+0x271`)

---

## Code execution
Write a ROP chain at saved RIP:

1. `ret` (stack alignment)
2. `pop rdi ; ret`
3. pointer to `"/bin/sh"` in libc
4. `system`
5. `exit`

Offsets used (glibc in challenge container):

- `ret`: `0x2882f`
- `pop rdi ; ret`: `0x10f78b`
- `"/bin/sh"`: `0x1cb42f`
- `system`: `0x58750`
- `exit`: `0x47ba0`

Trigger by sending an invalid command (`x`) so loop exits and control returns through overwritten RIP.

---

## Repro

### Local binary
```bash
python3 solve.py
```

### Docker
Important: this image runs under `pwn.red/jail`, so it needs privileged mode and container port `5000`.

```bash
docker run --privileged -p 6700:5000 $(docker build -q .)
python3 solve.py REMOTE HOST=127.0.0.1 PORT=6700
```

### Remote
```bash
python3 solve.py REMOTE HOST=jit.ctf.ingeniums.club PORT=6703
```

---

## Notes
- The exploit retries up to 80 times because some layouts are not immediately usable (e.g., reachability constraints from `stack_base`).
- Lua numbers are doubles; to keep integer writes exact, values are kept below `2^53` where needed (`10**13` is safe).
- Pointer-like leaked values may be LuaJIT-tagged; exploit masks them with `0x7fffffffffff` when needed.
