#!/usr/bin/env python3

import sys
import random
from Crypto.Util.number import getPrime, bytes_to_long, long_to_bytes
import hashlib

# CONFIG
PRIME_BITS = 768
e = 65537

try:
    FLAG = open("/app/flag.txt", "rb").read().strip()
except FileNotFoundError:
    FLAG = b"CTF{fake_flag_for_testing_purposes}"


# STAGE 2 MATH (Computed FIRST to generate Lambdas)
def tiger_hash(x):
    return int.from_bytes(
        hashlib.sha256(long_to_bytes(x)).digest()[:24],
        "big",
    )


# 1. Generate base random seeds for the original vectors
r1 = random.randint(10**20, 10**21)
r2 = random.randint(10**20, 10**21)

# 2. Base vectors
P = (r1, tiger_hash(r1))
Q = (r2, tiger_hash(r2))

# 3. Secret rotation matrix variables
a = random.randint(10**5, 10**6)
b = random.randint(10**5, 10**6)


def rot(v):
    x, y = v
    return (a * x - b * y, b * x + a * y)


# 4. Rotated vectors
P1 = rot(P)
Q1 = rot(Q)

# 5. Extract the X-coordinates to be our RSA Lambdas
lambdas = [abs(P1[0]), abs(Q1[0])]

# Calculate the final 'out' variable using the squared norms of P1 and Q1
S = bytes_to_long(FLAG)
V = random.randint(10**50, 10**60)

out = S * (P1[0] ** 2 + P1[1] ** 2) + V * (Q1[0] ** 2 + Q1[1] ** 2)


# RSA SETUP (Using the extracted lambdas)
p = getPrime(PRIME_BITS)
q = getPrime(PRIME_BITS)
N0 = p * q

# This creates N0, N1, N2
Ns = [N0] + [(p + L) * (q + L) for L in lambdas]

TIGER_TEXTS = [
    "Tigers move silently. call the author to continue",
    "A tiger's patience is unmatched. call the author to continue",
    "Stripes make tigers invisible. call the author to continue",
    "A tiger waits, then strikes once. call the author to continue",
    "No roar, just focus. call the author to continue",
    "Tiger eyes never blink at fear. call the author to continue",
    "One step from a tiger means danger. call the author to continue",
    "In the jungle, tigers write the rules. call the author to continue",
    "A tiger tracks the wind before moving. call the author to continue",
    "The quietest paw leaves the deepest mark. call the author to continue",
    "Even shadows follow tigers carefully. call the author to continue",
    "A tiger chooses timing over speed. call the author to continue",
    "Respect the stripes or regret it. call the author to continue",
]
SUFFIX = " [ DECRYPTED ] Not the flag."
valid_messages = [f"{text}{SUFFIX}".encode() for text in TIGER_TEXTS]
valid_messages = [msg for msg in valid_messages if bytes_to_long(msg) < N0]

if valid_messages:
    message = random.choice(valid_messages)
else:
    base = "Tiger says hi."
    message = f"{base}{SUFFIX}".encode()
    while bytes_to_long(message) >= N0 and len(message) > 1:
        base = base[:-1]
        message = f"{base}{SUFFIX}".encode()

    if bytes_to_long(message) >= N0:
        message = b"\x01"

m = bytes_to_long(message)
ct = pow(m, e, N0)


# UI
def banner():
    print("=" * 70)
    print("        Related Moduli & Rotated Vectors")
    print("=" * 70)


def stage1():
    print("\n[ Stage 1 ] RSA\n")
    print("Given:")
    print("  p, q are secret primes")
    print(f"  size(p) = size(q) = {PRIME_BITS} bits")
    print("  N0 = p * q")
    print("  N1 = (p + λ1) * (q + λ1)")
    print("  N2 = (p + λ2) * (q + λ2)")
    print("  λ1 and λ2 are the hidden shifts used to build N1 and N2")
    print(f"  size(λ1) = {lambdas[0].bit_length()} bits")
    print(f"  size(λ2) = {lambdas[1].bit_length()} bits")
    print(f"  e = {e}\n")

    print("Moduli:")
    for i, N in enumerate(Ns):
        print(f"N_{i} = {N}")

    print("\nCiphertext:")
    print(f"c = {ct}\n")

    user = input("Decrypt the message >> ").strip().encode()
    if user != message.strip():
        print("[-] Wrong.")
        sys.exit()

    print("\n[+] Correct decryption!\n")


def stage2():
    print("\n[ Stage 2 ] The Hidden Vectors\n")
    phrase = input("Enter phrase: ").strip()

    if phrase != "undertaker is goated":
        print("[-] Access denied.")
        sys.exit()

    print("\n[+] Access granted!\n")
    print("Rotation details:")
    print("  Base vectors:")
    print("    P = (r1, tiger_hash(r1))")
    print("    Q = (r2, tiger_hash(r2))")
    print("  Rotation matrix used:")
    print("    [ a  -b ]")
    print("    [ b   a ]")
    print(f"  a = {a}")
    print(f"  b = {b}")
    print("  Applied as:")
    print("    P1 = (a*P_x - b*P_y, b*P_x + a*P_y)")
    print("    Q1 = (a*Q_x - b*Q_y, b*Q_x + a*Q_y)")
    print("  λ1 = |P1_x| and λ2 = |Q1_x| (these are the shifts from Stage 1)\n")

    print("Flag-hiding equation:")
    print("  S = bytes_to_long(FLAG)")
    print("  out = S*(P1_x^2 + P1_y^2) + V*(Q1_x^2 + Q1_y^2)")
    print("  where V is a random integer in [10^50, 10^60]\n")

    print("Values exposed to you:\n")
    print(f"P1_y = {P1[1]}")
    print(f"Q1_y = {Q1[1]}")
    print(f"\nout = {out}\n")

    guess = input("S (flag int) = ").strip()

    try:
        if long_to_bytes(int(guess)) == FLAG:
            print("\n[+] FLAG:")
            print(FLAG.decode())
        else:
            print("[-] Wrong.")
    except Exception:
        print("[-] Invalid input.")


if __name__ == "__main__":
    banner()
    stage1()
    stage2()
