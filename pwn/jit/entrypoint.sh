#!/bin/sh
EXEC="./run"
PORT=6702

exec socat -T300 tcp-l:$PORT,reuseaddr,fork,keepalive EXEC:"$EXEC",stderr
