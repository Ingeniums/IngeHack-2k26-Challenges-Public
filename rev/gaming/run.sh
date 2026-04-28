#!/bin/sh
qemu-system-i386 -m 4G   -drive file=os_img.bin,if=floppy,format=raw  -vga std