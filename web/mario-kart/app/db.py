from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.getenv("DB_PATH", "/data/wallet.db"))


class AlreadyClaimedError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


def connect_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA busy_timeout = 5000")
    db.execute("PRAGMA journal_mode = WAL")
    return db


def init_db() -> None:
    with connect_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                bonus_claimed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS wallet_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_owner TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                amount_cents INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )


def get_user_by_username(username: str) -> sqlite3.Row | None:
    with connect_db() as db:
        return db.execute(
            "SELECT id, username, password_hash, bonus_claimed FROM users WHERE username = ? LIMIT 1",
            (username,),
        ).fetchone()


def create_user(username: str, password_hash: str) -> int:
    with connect_db() as db:
        cursor = db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash),
        )
        return int(cursor.lastrowid)


def get_user_by_id(user_id: int) -> sqlite3.Row | None:
    with connect_db() as db:
        return db.execute(
            "SELECT id, username, password_hash, bonus_claimed FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()


def wallet_for_owner(wallet_owner: str) -> sqlite3.Row:
    with connect_db() as db:
        return db.execute(
            """
            SELECT ? AS wallet_owner, COALESCE(SUM(amount_cents), 0) AS balance_cents
            FROM wallet_ledger
            WHERE wallet_owner = ?
            """,
            (wallet_owner, wallet_owner),
        ).fetchone()


def claim_bonus_for_user(user_id: int, bonus_cents: int) -> sqlite3.Row:
    db = connect_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        user = db.execute(
            "SELECT id, username, bonus_claimed FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if user is None:
            db.execute("ROLLBACK")
            raise UserNotFoundError

        if user["bonus_claimed"]:
            db.execute("ROLLBACK")
            raise AlreadyClaimedError

        db.execute("UPDATE users SET bonus_claimed = 1 WHERE id = ?", (user["id"],))
        db.execute(
            """
            INSERT INTO wallet_ledger (wallet_owner, user_id, amount_cents)
            VALUES (?, ?, ?)
            """,
            (user["username"], user["id"], bonus_cents),
        )
        wallet = db.execute(
            """
            SELECT ? AS wallet_owner, COALESCE(SUM(amount_cents), 0) AS balance_cents
            FROM wallet_ledger
            WHERE wallet_owner = ?
            """,
            (user["username"], user["username"]),
        ).fetchone()
        db.execute("COMMIT")
        return wallet
    except Exception:
        if db.in_transaction:
            db.execute("ROLLBACK")
        raise
    finally:
        db.close()
