#!/bin/sh
EXEC="/app/chall"
PORT=1337

exec socat -T300 tcp-l:$PORT,reuseaddr,fork,keepalive EXEC:"timeout -k 5s 10m $EXEC",stderr
