# Phase 2 Player Handout

You receive this file together with `phase2_client.py` after onsite Phase 1 validation.

The provided client script is here to help you avoid boilerplate networking/scripting.
Your job is only to write solve logic inside the required functions.

## Run

```bash
python3 phase2_client.py --host <HOST> --port <PORT>
```

## What you must implement

Open `phase2_client.py` and implement these 3 functions only.

### 1) `solve_phase1(outputs) -> int`

Input:

- `outputs`: `dict`
  - `outputs["x1"]`: `int`
  - `outputs["x2"]`: `int`
  - `outputs["x3"]`: `int`
  - `outputs["x4"]`: `int`

Output:

- Return recovered `a` as `int`.

---

### 2) `solve_commitments(commitments) -> dict[int, int]`

Input:

- `commitments`: `list[dict]`
- Each element has:
  - `index`: `int`
  - `k`: `int`
  - `Q`: `dict` with
    - `Q["x"]`: `int`
    - `Q["y"]`: `int`
    - `Q["z"]`: `int`
  - `sha256_px`: `str` (hex digest)

Output:

- Return a dictionary mapping each `index` to recovered `P_i.x`:
  - `{0: <int>, 1: <int>, 2: <int>, ...}`

Rules:

- Include all indices present in `commitments`.
- Values must be `int`.

---

### 3) `build_final_submission() -> str`

Output:

- Return the final submit string as `str`.

## What the script does for you

- Connects to the server
- Parses challenge text and commitment data
- Calls your functions
- Auto-submits your computed values
- Prints server response

You only implement logic in the 3 functions above.
