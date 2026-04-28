#!/bin/sh
EXEC="./run"
PORT=1337

socat -T300 tcp-l:$PORT,reuseaddr,fork,keepalive EXEC:"$EXEC",stderr
