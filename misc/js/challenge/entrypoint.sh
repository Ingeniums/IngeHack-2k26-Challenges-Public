#!/bin/sh
set -eu

if [ -f /app/flag.txt ]; then
    install -o root -g root -m 0444 /app/flag.txt /flag.txt
else
    FLAG_VALUE="${FLAG:-ingehack{fake_flag}}"

    printf '%s\n' "$FLAG_VALUE" > /flag.txt
    chmod 444 /flag.txt
    chown root:root /flag.txt
fi

exec su-exec ctf node /app/server.js
