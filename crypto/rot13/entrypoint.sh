#!/bin/bash
socat TCP-LISTEN:4000,reuseaddr,fork EXEC:"/usr/bin/sage /app/chall.py",pty,stderr
