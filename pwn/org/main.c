#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define OP_PUSH    0x01
#define OP_POP     0x02
#define OP_ADD     0x03
#define OP_STORE   0x04
#define OP_LOAD    0x05
#define OP_JMP     0x06
#define OP_HALT    0x07

#define OP_READBUF    0xF2
#define OP_DEBUG      0xF4
#define OP_PREP_OPEN  0xF5
#define OP_DO_OPEN    0xF6
#define OP_RAX_TO_RDI 0xF7
#define OP_PREP_READ  0xF8
#define OP_DO_READ    0xF9
#define OP_RAX_TO_RDX 0xFA
#define OP_PREP_WRITE 0xFB
#define OP_DO_WRITE   0xFC

#define STACK_SIZE  64
#define MEM_SIZE    256
#define BUF_SIZE    256
#define CODE_SIZE   512

char flag_path[] = "flag.txt";
char memo[0x400];

typedef struct VM {
    int     stack[STACK_SIZE];
    int     sp;
    uint8_t mem[MEM_SIZE];
    uint8_t code[CODE_SIZE];
    int     pc;
    char    vm_buf[BUF_SIZE];
    int     last_read;
    int     running;
} VM;

typedef struct {
    uint64_t rdi;
    uint64_t rsi;
    uint64_t rdx;
    uint64_t rax;
} CallCtx;

static VM *active_vm;
static CallCtx call_ctx;

static void vm_push(VM *vm, int val) {
    if (vm->sp >= STACK_SIZE) {
        fprintf(stderr, "[VM] Stack overflow\n");
        vm->running = 0;
        return;
    }
    vm->stack[vm->sp++] = val;
}

static int vm_pop(VM *vm) {
    if (vm->sp <= 0) {
        fprintf(stderr, "[VM] Stack underflow\n");
        vm->running = 0;
        return -1;
    }
    return vm->stack[--vm->sp];
}

__attribute__((noinline))
static void native_debug_sink(const char *data, size_t len) {
    char scratch[64];

    puts("[HOST] entering debug sink");
    memcpy(scratch, data, len);
    puts("[HOST] leaving debug sink");
}

static uint64_t vm_mem_qword(size_t offset) {
    uint64_t val = 0;
    size_t i;

    if (!active_vm || offset + 8 > MEM_SIZE) {
        return 0;
    }

    for (i = 0; i < 8; i++) {
        val |= ((uint64_t)active_vm->mem[offset + i]) << (8 * i);
    }

    return val;
}

static int validate(const uint8_t *code, size_t len) {
    size_t i = 0;

    while (i < len) {
        uint8_t op = code[i];

        if (op == OP_READBUF || op == OP_DEBUG || op == OP_PREP_OPEN ||
            op == OP_DO_OPEN || op == OP_RAX_TO_RDI || op == OP_PREP_READ ||
            op == OP_DO_READ || op == OP_RAX_TO_RDX || op == OP_PREP_WRITE ||
            op == OP_DO_WRITE) {
            fprintf(stderr,
                    "[VALIDATOR] Restricted opcode 0x%02X at offset %zu -- rejected!\n",
                    op, i);
            return 0;
        }

        switch (op) {
        case OP_PUSH:
            i += 3;
            break;
        case OP_POP:
        case OP_ADD:
        case OP_HALT:
            i += 1;
            break;
        case OP_STORE:
        case OP_LOAD:
        case OP_JMP:
            i += 2;
            break;
        default:
            fprintf(stderr, "[VALIDATOR] Unknown opcode 0x%02X at offset %zu\n",
                    op, i);
            return 0;
        }
    }
    puts("[VALIDATOR] Bytecode looks clean. Executing...");
    return 1;
}

static void vm_run(VM *vm) {
    active_vm = vm;
    vm->running = 1;

    while (vm->running && vm->pc >= 0 && vm->pc < CODE_SIZE) {
        uint8_t op = vm->code[vm->pc];

        switch (op) {
        case OP_PUSH: {
            uint8_t hi;
            uint8_t lo;
            int val;

            vm->pc++;
            hi = vm->code[vm->pc++];
            lo = vm->code[vm->pc++];
            val = (hi << 8) | lo;
            vm_push(vm, val);
            break;
        }

        case OP_POP:
            vm_pop(vm);
            vm->pc++;
            break;

        case OP_ADD: {
            int b = vm_pop(vm);
            int a = vm_pop(vm);

            vm_push(vm, a + b);
            vm->pc++;
            break;
        }

        case OP_STORE: {
            uint8_t addr;

            vm->pc++;
            addr = vm->code[vm->pc++];
            vm->mem[addr] = (uint8_t)vm_pop(vm);
            break;
        }

        case OP_LOAD: {
            uint8_t addr;

            vm->pc++;
            addr = vm->code[vm->pc++];
            vm_push(vm, vm->mem[addr]);
            break;
        }

        case OP_JMP: {
            uint8_t target;

            vm->pc++;
            target = vm->code[vm->pc];
            vm->pc = target;
            break;
        }

        case OP_HALT:
            puts("[VM] HALT");
            vm->running = 0;
            break;

        case OP_READBUF: {
            int fd = vm_pop(vm);
            int n;

            memset(vm->vm_buf, 0, sizeof(vm->vm_buf));
            n = (int)read(fd, vm->vm_buf, sizeof(vm->vm_buf));
            if (n < 0) {
                n = 0;
            }
            vm->last_read = n;
            printf("[VM] OP_READBUF: read %d bytes into vm_buf\n", n);
            vm_push(vm, n);
            vm->pc++;
            break;
        }

        case OP_DEBUG:
            printf("[VM] OP_DEBUG: forwarding %d bytes into host helper\n",
                   vm->last_read);
            native_debug_sink(vm->vm_buf, (size_t)vm->last_read);
            vm->pc++;
            break;

        case OP_PREP_OPEN:
            call_ctx.rdi = vm_mem_qword(0x00);
            call_ctx.rsi = vm_mem_qword(0x08);
            vm->pc++;
            break;

        case OP_DO_OPEN:
            call_ctx.rax = (uint64_t)open((const char *)call_ctx.rdi,
                                          (int)call_ctx.rsi);
            vm->pc++;
            break;

        case OP_RAX_TO_RDI:
            call_ctx.rdi = call_ctx.rax;
            vm->pc++;
            break;

        case OP_PREP_READ:
            call_ctx.rsi = vm_mem_qword(0x10);
            call_ctx.rdx = vm_mem_qword(0x18);
            vm->pc++;
            break;

        case OP_DO_READ:
            call_ctx.rax = (uint64_t)read((int)call_ctx.rdi,
                                          (void *)call_ctx.rsi,
                                          (size_t)call_ctx.rdx);
            vm->pc++;
            break;

        case OP_RAX_TO_RDX:
            call_ctx.rdx = call_ctx.rax;
            vm->pc++;
            break;

        case OP_PREP_WRITE:
            call_ctx.rdi = vm_mem_qword(0x20);
            call_ctx.rsi = vm_mem_qword(0x28);
            vm->pc++;
            break;

        case OP_DO_WRITE:
            call_ctx.rax = (uint64_t)write((int)call_ctx.rdi,
                                           (const void *)call_ctx.rsi,
                                           (size_t)call_ctx.rdx);
            vm->pc++;
            break;

        default:
            fprintf(stderr, "[VM] Unknown opcode 0x%02X at pc=%d\n", op, vm->pc);
            vm->running = 0;
            break;
        }
    }

    active_vm = NULL;
}

static int load_bytecode(VM *vm) {
    size_t n;

    n = fread(vm->code, 1, CODE_SIZE, stdin);
    printf("[*] Loaded %zu bytes of bytecode\n", n);
    return (int)n;
}

int main(void) {
    setbuf(stdout, NULL);
    setbuf(stdin, NULL);
    setbuf(stderr, NULL);
    VM vm;
    int n;
    memset(&vm, 0, sizeof(vm));
    n = load_bytecode(&vm);
    if (n < 0) {
        return 1;
    }

    if (!validate(vm.code, (size_t)n)) {
        fputs("[*] Bytecode rejected. Exiting.\n", stderr);
        return 1;
    }

    vm_run(&vm);
    return 0;
}
