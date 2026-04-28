# canaries - writeup

## TL;DR
The challenge has a custom canary scheme (not GCC stack canary), but canaries are generated with:

- `srand(time(0))`
- repeated `rand()`

So canary values are predictable by bruteforcing nearby timestamps.

Full exploit chain:

1. Trigger a 16-bit length underflow to get `read(..., 65535)` into a 16-byte stack buffer.
2. Leak `printf` from GOT via OOB index in menu option `2`.
3. Compute `libc` base from the leak.
4. Predict canary for the buffer-adjacent custom canary slot.
5. Overflow with correct predicted canary + ROP (`system("/bin/sh")`).

---

## Binary notes

- Arch: `amd64`
- NX: enabled
- PIE: enabled
- RELRO: Partial
- No compiler stack canary (`checksec` says no canary), but binary has injected custom checks:
  - `__init_canary_stub`
  - `__check_canary_stub`

Important mismatch: `main.c` in folder is **not** the real logic used for exploitation details (the ELF has extra canary instrumentation).

---

## Vulnerability 1: OOB read in option `2` (libc leak)

`g_canary_stats` has 4 entries, but bounds check is effectively:

- reject only if `index > 4`
- negative values are accepted

So `index = -3` reads memory before the array base.

Array base is `0x4050`, element size `0x18`, so:

- `g_canary_stats[-3]` points at `0x4050 - 3*0x18 = 0x4008`

And in `.got.plt`:

- `0x4008` -> `setbuf@got` (printed as `name` pointer)
- `0x4010` -> `printf@got` (printed as `weight` field)

So `weight` gives a runtime `printf` address => libc leak.

---

## Vulnerability 2: length underflow -> large BOF

In option `0`, program does (simplified):

```c
length = read(0, buf, length);
buf[length - 1] = 0;
length = length - 1;
```

`length` is `uint16_t` and starts at `16`.

### Required 2-step setup

This is the important gotcha:

1. First call to option `0` with just newline:
   - `read(..., 16)` returns `1`
   - then `length = 0`
2. Second call to option `0`:
   - `read(..., 0)` returns `0`
   - then `length = 0 - 1 = 65535` (unsigned wrap)

After that, next option `0` reads up to `65535` bytes into 16-byte `buf`.

---

## Custom canary behavior

From `__init_canary_stub`:

- first call seeds once with `time(0)`
- each canary init uses two `rand()` outputs:

```c
canary = ((uint64_t)rand() << 32) | rand();
if (canary == 0) canary = 0xA55AA55AA55AA55A;
```

Buffer-adjacent custom canary is the first one (index `0`).

During BOF, we overwrite:

- `buf[16]`
- custom canary slot right after `buf`
- custom canary index slot right after that

To pass post-read checks, payload must include:

- predicted canary value for slot 0
- index `0` (so checker compares against `__var_canary_table[0]`)

---

## Stack layout used by exploit

Payload structure used in `solve.py`:

```python
flat(
    b"A" * 0x10,      # buf
    canary0,          # custom canary value for slot0
    0,                # custom canary index slot0
    b"B" * 0x10,      # padding to saved rbp area
    0x4242424242424242,
    ret,
    pop_rdi,
    bin_sh,
    libc.sym.system,
)
```

Also append one sacrificial byte (`b"Z"`) because code does `buf[length-1] = 0`, so the last byte we send gets nulled.

---

## Exploit flow in `solve.py`

1. `prime_underflow()`:
   - option `0` once to set `length=0`
   - option `0` again to wrap `length=65535`
2. `leak_printf()` with option `2`, index `-3`
3. `libc.address = leak - libc.sym.printf`
4. Bruteforce seeds around `int(time.time())`
5. For each seed:
   - predict canary0 using local `ctypes.CDLL(libc).srand/rand`
   - send BOF payload
   - force loop exit by invalid menu input (`"x"`) to hit function `ret`
   - ROP executes `system("/bin/sh")`

---

## Usage

Local:

```bash
python3 solve.py --window 20
```

Remote:

```bash
python3 solve.py --host <HOST> --port <PORT> --window 60
```

If remote clock drift is bigger, increase `--window` or provide `--seed` manually.

---

## Notes / pitfalls

- `main.py` leak primitive was correct, but BOF setup needs the **second** option `0` call for underflow to `65535`.
- Local `flag.txt` in this folder is empty, so test shell success with marker command first (as script does).
