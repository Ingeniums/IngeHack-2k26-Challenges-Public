# Phase 1 Share Note

## Goal
Implement the Stage 1 solver hook and run the client.

## File
- `phase1_client.py`

## Required function
```python
def solve_stage1(stage1: Stage1Data) -> bytes:
    ...
```

## Input shape
`stage1` contains:
- `n0: int`
- `n1: int`
- `n2: int`
- `c: int`
- `e: int`
- `lambda1_bits: int`
- `lambda2_bits: int`

## Output shape
Return the exact Stage 1 plaintext as `bytes`.

## Run
```bash
python3 phase1_client.py --host <host> --port <port>
```

## Expected behavior
- Client reads by protocol marker (not fragile newline assumptions).
- Client auto-submits Stage 1 answer.
- Client stops after Phase 1 and indicates onsite handoff for next phase.
