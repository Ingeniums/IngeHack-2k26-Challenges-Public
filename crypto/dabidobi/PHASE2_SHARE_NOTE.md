# Phase 2 Player Handout

## Goal
Implement Stage 1 + Stage 2 hooks and run the client end-to-end.

You should be able to solve Phase 2 from this handout + the client template, without needing to discover hidden details from gated server output first.

## File
- `player_client_phase2.py`

## Required functions
```python
def solve_stage1(stage1: Stage1Data) -> bytes:
    ...

def derive_connection_values(stage1: Stage1Data) -> ConnectionValues:
    ...

def solve_stage2(stage2: Stage2Data, connection: ConnectionValues) -> int:
    ...
```

## Full problem statement

### Stage 1 (RSA with related moduli)
Server generates secret primes `p, q` and uses:

- `N0 = p * q`
- `N1 = (p + λ1) * (q + λ1)`
- `N2 = (p + λ2) * (q + λ2)`

You receive `N0, N1, N2, c, e` and bit-length hints for `λ1, λ2`.

`solve_stage1` must recover the exact plaintext bytes of `c mod N0`.

`derive_connection_values` must recover the per-connection values:

- `lambda1 = λ1`
- `lambda2 = λ2`

These must be derived fresh for each connection.

### Stage 2 (rotated vectors + linear combination)
The challenge internally defines:

- `P = (r1, tiger_hash(r1))`
- `Q = (r2, tiger_hash(r2))`
- Rotation matrix `[[a, -b], [b, a]]`
- `P1 = (a*P_x - b*P_y, b*P_x + a*P_y)`
- `Q1 = (a*Q_x - b*Q_y, b*Q_x + a*Q_y)`

And links Stage 1 shifts to rotated x-coordinates:

- `λ1 = |P1_x|`
- `λ2 = |Q1_x|`

The hidden flag integer is:

- `S = bytes_to_long(FLAG)`

The server computes:

- `out = S*(P1_x^2 + P1_y^2) + V*(Q1_x^2 + Q1_y^2)`

where `V` is a random integer in `[10^50, 10^60]`.

For Stage 2, server gives you:

- `P1_y`
- `Q1_y`
- `out`

Your `solve_stage2` must return `S` as an integer.

### What you know vs what you recover

- Known from Stage 1 parse: `N0, N1, N2, c, e, lambda1_bits, lambda2_bits`
- Recovered in Stage 1 logic: `λ1, λ2`
- Carried into Stage 2 via `ConnectionValues`: `lambda1, lambda2`
- Known from Stage 2 parse: `P1_y, Q1_y, out`
- Target output of Stage 2: `S`

## Input shapes
`Stage1Data`:
- `n0: int`
- `n1: int`
- `n2: int`
- `c: int`
- `e: int`
- `lambda1_bits: int`
- `lambda2_bits: int`

`ConnectionValues`:
- `lambda1: int`
- `lambda2: int`

`Stage2Data`:
- `p1y: int`
- `q1y: int`
- `out: int`

## Output shapes
- `solve_stage1` returns Stage 1 plaintext as `bytes`.
- `derive_connection_values` returns per-connection values needed for Stage 2.
- `solve_stage2` returns `S` as `int`.

## Run
```bash
python3 player_client_phase2.py --host <host> --port <port>
```

## Notes
- Re-derive per-connection values every run; do not reuse values from older connections.
- Script auto-submits both phases using prompt-synchronized marker reads.
- Stage 2 uses the same connection-specific `λ1, λ2` recovered from that run's Stage 1.
