from Crypto.Util.number import *
from gmpy2 import next_prime

A  = getStrongPrime(1024)
B  = next_prime(A ^ ((1 << 1024) - 1))
M  = A * B

p, q   = getPrime(1024), getPrime(1024)
k1, k2 = getPrime(200),  getPrime(200)
n      = p * q

c1 = (A*pow(p,   67, n) + k1*pow(q,   1337, n)) % n
c2 = (B*pow(p, 6767, n) + k2*pow(q, 133777, n)) % n

c = pow(bytes_to_long(flag), 0x10001, n)

with open('data.txt', 'w') as f:
    f.write(f"{M}\n{c1}\n{c2}\n{n}\n{c}\n")
