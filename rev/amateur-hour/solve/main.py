#!/usr/bin/env python3

import os
from pathlib import Path

from pwn import process


def main() -> int:
    main_bin = "main"
    flag_file = "flag.txt"
    preload_so = "./preload.so"

    build = process(["bash", "compile.sh"])
    build.wait_for_close()
    if build.poll() != 0:
        return int(build.poll())

    env = os.environ.copy()
    env["LD_PRELOAD"] = str(preload_so)

    io = process([str(main_bin), str(flag_file)], env=env)
    io.interactive()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
