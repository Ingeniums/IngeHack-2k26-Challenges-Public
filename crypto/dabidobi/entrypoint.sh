#!/bin/bash

# Run challenge with socat
socat TCP-LISTEN:4000,reuseaddr,fork EXEC:"python3 /app/chall.py",pty,stderr
