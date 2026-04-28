#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
gcc -shared -fPIC -x c preload.h -o preload.so
