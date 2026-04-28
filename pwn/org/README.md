# org writeup

The VM looks restrictive at first because the validator only allows these opcodes:

- `PUSH`
- `POP`
- `ADD`
- `STORE`
- `LOAD`
- `JMP`
- `HALT`

All of the interesting host-side opcodes are explicitly banned by `validate()`:

- `OP_PREP_OPEN`
- `OP_DO_OPEN`
- `OP_RAX_TO_RDI`
- `OP_PREP_READ`
- `OP_DO_READ`
- `OP_RAX_TO_RDX`
- `OP_PREP_WRITE`
- `OP_DO_WRITE`

## Bug

The validator walks the bytecode linearly and assumes execution always starts at opcode boundaries.

That assumption is false because `JMP` can jump to any byte offset. This means we can hide a banned opcode inside the operand byte of a valid instruction and then jump directly to that operand.

The solver uses this pattern:

```text
04 f5
```

When the validator reads this, it sees:

- `04` = `STORE`
- `f5` = operand byte

So validation succeeds.

But if execution jumps to the second byte, the VM sees:

- `f5` = `OP_PREP_OPEN`

That gives us access to the banned host helpers without ever placing those opcodes at positions the validator recognizes as instruction starts.

## What the hidden opcodes do

The VM has a global `call_ctx` and several hidden opcodes that effectively expose a tiny syscall chain:

1. `OP_PREP_OPEN`
   Loads:
   - `rdi = *(uint64_t *)&vm->mem[0x00]`
   - `rsi = *(uint64_t *)&vm->mem[0x08]`
2. `OP_DO_OPEN`
   Calls `open((char *)rdi, (int)rsi)`
3. `OP_RAX_TO_RDI`
   Moves the returned file descriptor into `rdi`
4. `OP_PREP_READ`
   Loads:
   - `rsi = *(uint64_t *)&vm->mem[0x10]`
   - `rdx = *(uint64_t *)&vm->mem[0x18]`
5. `OP_DO_READ`
   Calls `read((int)rdi, (void *)rsi, rdx)`
6. `OP_RAX_TO_RDX`
   Moves the number of bytes read into `rdx`
7. `OP_PREP_WRITE`
   Loads:
   - `rdi = *(uint64_t *)&vm->mem[0x20]`
   - `rsi = *(uint64_t *)&vm->mem[0x28]`
8. `OP_DO_WRITE`
   Calls `write((int)rdi, (void *)rsi, rdx)`

So the intended exploit is really:

```text
open("flag.txt", 0)
read(fd, memo, 0x80)
write(1, memo, bytes_read)
```

## How the solver builds the payload

The solver first places a normal `JMP` at offset 0 so execution skips over the hidden opcode stubs.

Each hidden stub is encoded as:

```text
JMP <filled later>
STORE <banned opcode>
```

The important part is the `STORE <banned opcode>` sequence. The banned opcode lives in the second byte, and the solver later makes the corresponding `JMP` land on that second byte.

So every hidden operation is reachable like this:

1. Validator parses `STORE operand`
2. VM jumps to `operand`
3. VM executes the banned opcode

## VM memory setup

Before triggering the hidden chain, the solver fills VM memory using only legal instructions.

It writes:

- `mem[0x00:0x08] = &flag_path`
- `mem[0x08:0x10] = 0`
- `mem[0x10:0x18] = &memo`
- `mem[0x18:0x20] = 0x80`
- `mem[0x20:0x28] = 1`
- `mem[0x28:0x30] = &memo`

These are real symbols from the binary:

- `flag_path` points to `"flag.txt"`
- `memo` is a writable global buffer

That is why the fixed solver uses `elf.symbols["memo"]`. The older `rop_area` name was wrong for this binary.

## Full execution flow

After setup, the payload jumps through the hidden opcodes in this order:

1. `PREP_OPEN`
2. `DO_OPEN`
3. `RAX_TO_RDI`
4. `PREP_READ`
5. `DO_READ`
6. `RAX_TO_RDX`
7. `PREP_WRITE`
8. `DO_WRITE`

At that point the flag has been copied from `flag.txt` to stdout.

The payload then stops with `HALT`.

## Why it works

The core mistake is that validation is done on a linear decode, but execution is done with arbitrary byte jumps.

That means the validator and the interpreter disagree on what counts as an instruction boundary. Once that happens, any banned opcode can be smuggled inside the immediate bytes of an allowed opcode and reached with `JMP`.

## Reproducing

Local:

```bash
python3 solver/solve.py
```

Remote:

```bash
python3 solver/solve.py HOST PORT
```

Expected result:

```text
ingehack{rev_2_pwn_2_own}
```
