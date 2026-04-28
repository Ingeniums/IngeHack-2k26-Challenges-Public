# Chess Signal

Local CTF service for the chess-themed challenge.

## Run Locally

### Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:8000`.

### Docker

```bash
docker build -t chess-signal .
docker run --rm -p 8000:8000 chess-signal
```

Open `http://127.0.0.1:8000`.

## Solver

`solver.py` is for challenge authors and testing.

The service reads its runtime flag from `flag.txt`. You can still override it with the `FLAG` environment variable if needed.

Run against a local instance:

```bash
python3 solver.py
```

Run against another host:

```bash
python3 solver.py http://127.0.0.1:8000
```

## Files

- `app.py`: Flask app and JSON API
- `challenge.py`: session state and server validation
- `flag.txt`: runtime flag source for the service
- `index.html`: frontend that renders state and sends numeric values
- `solver.py`: example solver for challenge authors
- `Dockerfile`: local packaging
