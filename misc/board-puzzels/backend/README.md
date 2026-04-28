# Backend (FastAPI)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

## Puzzle API

- `GET /api/puzzle/new`
  - Picks a random image from `backend/assets`
  - Splits it into a grid (`GRID_ROWS` x `GRID_COLS`)
  - Rotates each tile randomly in `ROTATION_STEP_DEGREES` increments
  - Returns rotated tiles as base64 PNG data URIs
- `POST /api/puzzle/check`
  - Accepts `puzzle_id` and the user tile rotations
  - Returns whether the puzzle is solved plus incorrect tile indices

## Developer constants

You can tune grid/rotation behavior in `app/main.py`:

- `GRID_ROWS`
- `GRID_COLS`
- `ROTATION_STEP_DEGREES`
- `MAX_IMAGE_DIMENSION`
- `DEFAULT_OBJECT_NAME`
