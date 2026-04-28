import base64
import hashlib
import hmac
import json
import os
import random
import secrets
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from PIL import Image, ImageChops, ImageStat
from pydantic import BaseModel, Field

app = FastAPI(title="Are You a Robot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Generic puzzle constants.
LEGACY_GRID_ROWS = 10
LEGACY_GRID_COLS = 10
ROTATION_STEP_DEGREES = 90
PUZZLE_TTL_SECONDS = 900
LEVEL_RUN_STALE_SECONDS = 24 * 60 * 60
ORIENTATION_DIFF_THRESHOLD = 2.0
WRONG_ANSWER_PENALTY_SECONDS = 10
TILE_FILL_RGB = (244, 244, 244)
TILE_FILL_RGBA = (244, 244, 244, 255)
TILE_JPEG_QUALITY = 90
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
DEFAULT_OBJECT_NAME = "street sign"
ASSET_OBJECT_NAMES: dict[str, str] = {}
ROTATION_CHOICES = tuple(range(0, 360, ROTATION_STEP_DEGREES))

# Auth constants.
DATABASE_PATH = Path(__file__).resolve().parent.parent / "app.db"
LEVELS_CONFIG_PATH = Path(__file__).resolve().parent.parent / "levels.js"
TYPES_CONFIG_PATH = Path(__file__).resolve().parent.parent / "types.js"
JWT_SECRET = os.getenv("JWT_SECRET", "development-secret-change-me")
ACCESS_TOKEN_EXPIRE_SECONDS = 24 * 60 * 60
PASSWORD_HASH_ITERATIONS = 390_000
MIN_PASSWORD_LENGTH = 8


@dataclass(frozen=True)
class AssetSource:
    image_path: Path
    source_url: str


@dataclass(frozen=True)
class PuzzleConfig:
    rows: int
    cols: int
    tag: str
    asset_sources: tuple[AssetSource, ...]


@dataclass(frozen=True)
class LevelConfig:
    level_id: int
    name: str
    time_limit_seconds: int
    puzzles: tuple[PuzzleConfig, ...]
    flag: str | None = None
    cards_gap: str | None = None


@dataclass
class PuzzleState:
    created_at: datetime
    applied_rotations: list[int]
    checkable_mask: list[bool]
    rows: int
    cols: int
    puzzle_payload: dict[str, Any]
    owner_user_id: int | None = None
    level_run_id: str | None = None


@dataclass
class LevelRunState:
    user_id: int
    level_id: int
    created_at: datetime
    expires_at: datetime
    puzzle_index: int
    total_puzzles: int
    current_puzzle_id: str
    puzzle_sources: tuple[AssetSource, ...]


class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime


class AuthRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class AuthMeResponse(BaseModel):
    email: str
    created_at: datetime


class CurrentLevelResponse(BaseModel):
    level_id: int
    cards_gap: str | None = None
    completed_level_ids: list[int] = Field(default_factory=list)


class PuzzleCreateResponse(BaseModel):
    puzzle_id: str
    object_name: str
    rows: int
    cols: int
    rotation_step: int
    image_width: int
    image_height: int
    tile_width: int
    tile_height: int
    tiles: list[str]
    source_url: str | None = None


class PuzzleCheckRequest(BaseModel):
    puzzle_id: str
    rotations: list[int]


class PuzzleCheckResponse(BaseModel):
    solved: bool
    incorrect_indices: list[int]


class LevelStartResponse(BaseModel):
    level_run_id: str
    level_id: int
    level_name: str
    puzzle_number: int
    total_puzzles: int
    puzzle_time_limit_seconds: int
    level_time_limit_seconds: int
    seconds_remaining: int
    expires_at: datetime
    puzzle: PuzzleCreateResponse


class LevelStartRequest(BaseModel):
    force_restart: bool = False


class LevelCheckRequest(BaseModel):
    level_run_id: str
    puzzle_id: str
    rotations: list[int]


class LevelCheckResponse(BaseModel):
    solved: bool
    incorrect_indices: list[int]
    level_completed: bool
    puzzle_number: int
    total_puzzles: int
    expires_at: datetime | None
    next_puzzle: PuzzleCreateResponse | None = None
    flag: str | None = None


PUZZLES: dict[str, PuzzleState] = {}
LEVEL_RUNS: dict[str, LevelRunState] = {}
security = HTTPBearer(auto_error=False)


def _db_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _init_db() -> None:
    with _db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_level_progress (
                user_id INTEGER NOT NULL,
                level_id INTEGER NOT NULL,
                completed_at TEXT NOT NULL,
                PRIMARY KEY (user_id, level_id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )


_init_db()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _base64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _base64url_decode(encoded: str) -> bytes:
    padded = encoded + "=" * (-len(encoded) % 4)
    return base64.urlsafe_b64decode(padded)


def _normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not normalized or normalized.count("@") != 1:
        raise HTTPException(status_code=400, detail="Invalid email address")

    local_part, domain = normalized.split("@", 1)
    if not local_part or not domain or "." not in domain:
        raise HTTPException(status_code=400, detail="Invalid email address")

    return normalized


def _validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {MIN_PASSWORD_LENGTH} characters",
        )


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return f"{_base64url_encode(salt)}.{_base64url_encode(digest)}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_segment, digest_segment = stored_hash.split(".", 1)
        salt = _base64url_decode(salt_segment)
        expected_digest = _base64url_decode(digest_segment)
    except (ValueError, TypeError):
        return False

    candidate_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return hmac.compare_digest(expected_digest, candidate_digest)


def _create_access_token(user: UserResponse) -> str:
    now_epoch = int(_now_utc().timestamp())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "created_at": user.created_at.isoformat(),
        "iat": now_epoch,
        "exp": now_epoch + ACCESS_TOKEN_EXPIRE_SECONDS,
    }

    header_segment = _base64url_encode(
        json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    payload_segment = _base64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )

    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    signature = _base64url_encode(
        hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    )

    return f"{header_segment}.{payload_segment}.{signature}"


def _raise_unauthorized(detail: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _decode_access_token(token: str) -> dict[str, Any]:
    segments = token.split(".")
    if len(segments) != 3:
        _raise_unauthorized("Invalid token")

    header_segment, payload_segment, signature_segment = segments
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    expected_signature = _base64url_encode(
        hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    )

    if not hmac.compare_digest(expected_signature, signature_segment):
        _raise_unauthorized("Invalid token signature")

    try:
        payload_raw = _base64url_decode(payload_segment)
        payload = json.loads(payload_raw)
    except (ValueError, json.JSONDecodeError):
        _raise_unauthorized("Invalid token payload")

    expiration = payload.get("exp")
    if not isinstance(expiration, int):
        _raise_unauthorized("Invalid token payload")

    if int(_now_utc().timestamp()) >= expiration:
        _raise_unauthorized("Token expired")

    return payload


def _user_from_row(row: sqlite3.Row) -> UserResponse:
    return UserResponse(
        id=int(row["id"]),
        email=str(row["email"]),
        created_at=datetime.fromisoformat(str(row["created_at"])),
    )


def _validate_token_identity(payload: dict[str, Any], user: UserResponse) -> None:
    token_email = payload.get("email")
    token_created_at = payload.get("created_at")

    if not isinstance(token_email, str) or token_email != user.email:
        _raise_unauthorized("Token user mismatch")

    if not isinstance(token_created_at, str) or token_created_at != user.created_at.isoformat():
        _raise_unauthorized("Token user mismatch")


def _get_user_row_by_id(user_id: int) -> sqlite3.Row | None:
    with _db_connection() as connection:
        return connection.execute(
            "SELECT id, email, created_at, password_hash FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()


def _get_user_row_by_email(email: str) -> sqlite3.Row | None:
    with _db_connection() as connection:
        return connection.execute(
            "SELECT id, email, created_at, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()


def _create_user(email: str, password: str) -> UserResponse:
    password_hash = _hash_password(password)
    created_at = _now_utc().isoformat()

    with _db_connection() as connection:
        try:
            cursor = connection.execute(
                "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
                (email, password_hash, created_at),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="Email is already registered") from exc

        row = connection.execute(
            "SELECT id, email, created_at FROM users WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=500, detail="Unable to create user")

    return _user_from_row(row)


def _get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> UserResponse:
    if credentials is None or credentials.scheme.lower() != "bearer":
        _raise_unauthorized("Missing bearer token")

    payload = _decode_access_token(credentials.credentials)
    subject = payload.get("sub")

    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        _raise_unauthorized("Invalid token subject")

    row = _get_user_row_by_id(user_id)
    if row is None:
        _raise_unauthorized("User not found")

    user = _user_from_row(row)
    _validate_token_identity(payload, user)
    return user


def _cleanup_expired_puzzles() -> None:
    cutoff = _now_utc() - timedelta(seconds=PUZZLE_TTL_SECONDS)
    active_level_puzzle_ids = {run.current_puzzle_id for run in LEVEL_RUNS.values()}
    expired_ids = [
        puzzle_id
        for puzzle_id, state in PUZZLES.items()
        if state.created_at < cutoff and puzzle_id not in active_level_puzzle_ids
    ]
    for puzzle_id in expired_ids:
        PUZZLES.pop(puzzle_id, None)


def _expire_level_run(level_run_id: str) -> None:
    level_run = LEVEL_RUNS.pop(level_run_id, None)
    if level_run is not None:
        PUZZLES.pop(level_run.current_puzzle_id, None)


def _cleanup_expired_level_runs() -> None:
    now = _now_utc()
    stale_cutoff = now - timedelta(seconds=LEVEL_RUN_STALE_SECONDS)
    expired_ids = [
        level_run_id
        for level_run_id, state in LEVEL_RUNS.items()
        if state.expires_at <= stale_cutoff
    ]
    for level_run_id in expired_ids:
        _expire_level_run(level_run_id)


def _fixed_image_sequence_for_level(level: LevelConfig) -> tuple[AssetSource, ...]:
    selected_sources: list[AssetSource] = []
    used_paths: set[str] = set()

    for puzzle_cfg in level.puzzles:
        if not puzzle_cfg.asset_sources:
            raise HTTPException(
                status_code=500,
                detail=f"No configured assets for tag: {puzzle_cfg.tag}",
            )

        unique_candidates = [
            source
            for source in puzzle_cfg.asset_sources
            if str(source.image_path.resolve()) not in used_paths
        ]
        if not unique_candidates:
            raise HTTPException(
                status_code=500,
                detail=f"Not enough unique images configured for tag: {puzzle_cfg.tag}",
            )

        chosen = random.choice(unique_candidates)
        selected_sources.append(chosen)
        used_paths.add(str(chosen.image_path.resolve()))

    return tuple(selected_sources)


def _response_from_puzzle_state(state: PuzzleState) -> PuzzleCreateResponse:
    return PuzzleCreateResponse(**state.puzzle_payload)


def _level_start_response_for_run(
    *,
    level_run_id: str,
    level_run: LevelRunState,
    level: LevelConfig,
) -> LevelStartResponse:
    state = PUZZLES.get(level_run.current_puzzle_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Active puzzle not found")

    return LevelStartResponse(
        level_run_id=level_run_id,
        level_id=level.level_id,
        level_name=level.name,
        puzzle_number=level_run.puzzle_index + 1,
        total_puzzles=level_run.total_puzzles,
        puzzle_time_limit_seconds=level.time_limit_seconds,
        level_time_limit_seconds=level.time_limit_seconds,
        seconds_remaining=_seconds_remaining(level_run.expires_at),
        expires_at=level_run.expires_at,
        puzzle=_response_from_puzzle_state(state),
    )


def _reset_level_run_after_timeout(
    *,
    level_run_id: str,
    level_run: LevelRunState,
    level: LevelConfig,
    user_id: int,
) -> LevelCheckResponse:
    first_puzzle_cfg = level.puzzles[0]
    first_source = level_run.puzzle_sources[0]
    next_expires_at = _now_utc() + timedelta(seconds=level.time_limit_seconds)

    PUZZLES.pop(level_run.current_puzzle_id, None)

    next_puzzle = _generate_puzzle(
        rows=first_puzzle_cfg.rows,
        cols=first_puzzle_cfg.cols,
        asset_sources=first_puzzle_cfg.asset_sources,
        owner_user_id=user_id,
        level_run_id=level_run_id,
        selected_source=first_source,
    )

    level_run.puzzle_index = 0
    level_run.current_puzzle_id = next_puzzle.puzzle_id
    level_run.expires_at = next_expires_at

    return LevelCheckResponse(
        solved=False,
        incorrect_indices=[],
        level_completed=False,
        puzzle_number=1,
        total_puzzles=level_run.total_puzzles,
        expires_at=next_expires_at,
        next_puzzle=next_puzzle,
    )


def _seconds_remaining(expires_at: datetime) -> int:
    return max(0, int((expires_at - _now_utc()).total_seconds()))


def _path_signature(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return stat.st_mtime_ns, stat.st_size


def _strip_js_comments(content: str) -> str:
    output: list[str] = []
    index = 0
    in_string = False
    escaped = False
    string_delimiter = ""

    while index < len(content):
        char = content[index]
        next_char = content[index + 1] if index + 1 < len(content) else ""

        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == string_delimiter:
                in_string = False
                string_delimiter = ""
            index += 1
            continue

        if char in ('"', "'"):
            in_string = True
            string_delimiter = char
            output.append(char)
            index += 1
            continue

        if char == "/" and next_char == "/":
            index += 2
            while index < len(content) and content[index] != "\n":
                index += 1
            continue

        if char == "/" and next_char == "*":
            index += 2
            while index + 1 < len(content) and not (
                content[index] == "*" and content[index + 1] == "/"
            ):
                index += 1
            index += 2
            continue

        output.append(char)
        index += 1

    return "".join(output)


def _resolve_asset_path(path_value: str) -> Path:
    value = path_value.strip().strip("/")
    if not value:
        raise HTTPException(status_code=500, detail="Asset path cannot be empty")

    if value.startswith("assets/"):
        path = (ASSETS_DIR.parent / value).resolve()
    else:
        path = (ASSETS_DIR / value).resolve()

    assets_root = ASSETS_DIR.resolve()

    if assets_root not in path.parents:
        raise HTTPException(status_code=500, detail=f"Invalid asset path: {path_value}")

    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=500, detail=f"Asset file does not exist: {path_value}")

    if path.suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=500, detail=f"Unsupported asset extension: {path_value}")

    return path


def _load_asset_type_config() -> dict[str, tuple[AssetSource, ...]]:
    if not TYPES_CONFIG_PATH.exists():
        raise HTTPException(status_code=500, detail=f"Missing types config file: {TYPES_CONFIG_PATH}")

    return _load_asset_type_config_cached(_path_signature(TYPES_CONFIG_PATH))


@lru_cache(maxsize=1)
def _load_asset_type_config_cached(
    _types_signature: tuple[int, int],
) -> dict[str, tuple[AssetSource, ...]]:
    raw = TYPES_CONFIG_PATH.read_text(encoding="utf-8")
    stripped = _strip_js_comments(raw).strip()
    if not stripped:
        raise HTTPException(status_code=500, detail="types.js cannot be empty")

    try:
        config_data = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Invalid JSON in types.js: {exc.msg}") from exc

    if not isinstance(config_data, dict):
        raise HTTPException(status_code=500, detail="types.js must contain a JSON object")

    levels_map = config_data.get("levels")
    if not isinstance(levels_map, dict) or not levels_map:
        raise HTTPException(status_code=500, detail="types.js must contain a non-empty levels object")

    parsed_types: dict[str, tuple[AssetSource, ...]] = {}

    for raw_tag, sources_data in levels_map.items():
        if not isinstance(raw_tag, str) or not raw_tag.strip():
            raise HTTPException(status_code=500, detail="types.js contains an invalid tag key")

        tag = raw_tag.strip().lower()
        if not isinstance(sources_data, list) or not sources_data:
            raise HTTPException(status_code=500, detail=f"Tag '{tag}' must contain a non-empty source list")

        parsed_sources: list[AssetSource] = []
        seen_paths: set[str] = set()

        for source_index, source_data in enumerate(sources_data):
            if not isinstance(source_data, dict):
                raise HTTPException(
                    status_code=500,
                    detail=f"Tag '{tag}' source #{source_index + 1} must be an object",
                )

            path_raw = source_data.get("path")
            url_raw = source_data.get("url")

            if not isinstance(path_raw, str) or not path_raw.strip():
                raise HTTPException(
                    status_code=500,
                    detail=f"Tag '{tag}' source #{source_index + 1} has invalid path",
                )
            if not isinstance(url_raw, str) or not url_raw.strip():
                raise HTTPException(
                    status_code=500,
                    detail=f"Tag '{tag}' source #{source_index + 1} has invalid url",
                )

            resolved_path = _resolve_asset_path(path_raw)
            resolved_key = str(resolved_path.resolve())
            if resolved_key in seen_paths:
                continue

            seen_paths.add(resolved_key)
            parsed_sources.append(
                AssetSource(
                    image_path=resolved_path,
                    source_url=url_raw.strip(),
                )
            )

        if not parsed_sources:
            raise HTTPException(status_code=500, detail=f"Tag '{tag}' has no usable sources")

        parsed_types[tag] = tuple(parsed_sources)

    return parsed_types


def _load_level_configs() -> list[LevelConfig]:
    if not LEVELS_CONFIG_PATH.exists():
        raise HTTPException(status_code=500, detail=f"Missing levels config file: {LEVELS_CONFIG_PATH}")
    if not TYPES_CONFIG_PATH.exists():
        raise HTTPException(status_code=500, detail=f"Missing types config file: {TYPES_CONFIG_PATH}")

    return list(
        _load_level_configs_cached(
            _path_signature(LEVELS_CONFIG_PATH),
            _path_signature(TYPES_CONFIG_PATH),
        )
    )


@lru_cache(maxsize=1)
def _load_level_configs_cached(
    _levels_signature: tuple[int, int],
    _types_signature: tuple[int, int],
) -> tuple[LevelConfig, ...]:
    raw = LEVELS_CONFIG_PATH.read_text(encoding="utf-8")
    stripped = _strip_js_comments(raw).strip()

    start_index = stripped.find("[")
    end_index = stripped.rfind("]")
    if start_index == -1 or end_index == -1 or end_index <= start_index:
        raise HTTPException(status_code=500, detail="levels.js must contain a JSON array")

    json_payload = stripped[start_index : end_index + 1]

    try:
        levels_data = json.loads(json_payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Invalid JSON in levels.js: {exc.msg}") from exc

    if not isinstance(levels_data, list) or not levels_data:
        raise HTTPException(status_code=500, detail="levels.js must define a non-empty levels array")

    parsed_levels: list[LevelConfig] = []
    seen_ids: set[int] = set()
    type_catalog = _load_asset_type_config()

    for index, level_data in enumerate(levels_data):
        if not isinstance(level_data, dict):
            raise HTTPException(status_code=500, detail=f"Level #{index + 1} must be an object")

        level_id_raw = level_data.get("level_id", index + 1)
        if not isinstance(level_id_raw, int) or level_id_raw <= 0:
            raise HTTPException(status_code=500, detail=f"Invalid level_id at level #{index + 1}")

        if level_id_raw in seen_ids:
            raise HTTPException(status_code=500, detail=f"Duplicate level_id: {level_id_raw}")
        seen_ids.add(level_id_raw)

        level_name_raw = level_data.get("name", f"Level {level_id_raw}")
        if not isinstance(level_name_raw, str) or not level_name_raw.strip():
            raise HTTPException(status_code=500, detail=f"Invalid name for level {level_id_raw}")

        level_time_limit_seconds = level_data.get("time_limit_seconds")
        if not isinstance(level_time_limit_seconds, int) or level_time_limit_seconds <= 0:
            raise HTTPException(status_code=500, detail=f"Invalid time_limit_seconds for level {level_id_raw}")

        flag_value: str | None = None
        if "flag" in level_data and level_data.get("flag") is not None:
            flag_raw = level_data.get("flag")
            if not isinstance(flag_raw, str) or not flag_raw.strip():
                raise HTTPException(status_code=500, detail=f"Invalid flag for level {level_id_raw}")
            flag_value = flag_raw.strip()

        cards_gap_value: str | None = None
        if "cards_gap" in level_data and level_data.get("cards_gap") is not None:
            cards_gap_raw = level_data.get("cards_gap")
            if not isinstance(cards_gap_raw, str) or not cards_gap_raw.strip():
                raise HTTPException(status_code=500, detail=f"Invalid cards_gap for level {level_id_raw}")
            cards_gap_value = cards_gap_raw.strip()

        puzzles_data = level_data.get("puzzles")
        if not isinstance(puzzles_data, list) or not puzzles_data:
            raise HTTPException(
                status_code=500,
                detail=f"Level {level_id_raw} must include a non-empty puzzles array",
            )

        puzzles: list[PuzzleConfig] = []

        for puzzle_index, puzzle_data in enumerate(puzzles_data):
            if not isinstance(puzzle_data, dict):
                raise HTTPException(
                    status_code=500,
                    detail=f"Level {level_id_raw} puzzle #{puzzle_index + 1} must be an object",
                )

            rows = puzzle_data.get("rows")
            cols = puzzle_data.get("cols")
            tag_raw = puzzle_data.get("tag")

            if not isinstance(rows, int) or rows <= 0:
                raise HTTPException(
                    status_code=500,
                    detail=f"Invalid rows for level {level_id_raw} puzzle #{puzzle_index + 1}",
                )
            if not isinstance(cols, int) or cols <= 0:
                raise HTTPException(
                    status_code=500,
                    detail=f"Invalid cols for level {level_id_raw} puzzle #{puzzle_index + 1}",
                )
            if not isinstance(tag_raw, str) or not tag_raw.strip():
                raise HTTPException(
                    status_code=500,
                    detail=f"Invalid tag for level {level_id_raw} puzzle #{puzzle_index + 1}",
                )

            tag = tag_raw.strip().lower()
            if tag not in type_catalog:
                available_tags = ", ".join(sorted(type_catalog))
                raise HTTPException(
                    status_code=500,
                    detail=(
                        f"Unknown tag '{tag_raw}' for level {level_id_raw} puzzle #{puzzle_index + 1}. "
                        f"Available tags: {available_tags}"
                    ),
                )

            puzzles.append(
                PuzzleConfig(
                    rows=rows,
                    cols=cols,
                    tag=tag,
                    asset_sources=type_catalog[tag],
                )
            )

        parsed_levels.append(
            LevelConfig(
                level_id=level_id_raw,
                name=level_name_raw.strip(),
                time_limit_seconds=level_time_limit_seconds,
                puzzles=tuple(puzzles),
                flag=flag_value,
                cards_gap=cards_gap_value,
            )
        )

    return tuple(parsed_levels)


def _level_lookup(levels: list[LevelConfig]) -> dict[int, int]:
    return {level.level_id: index for index, level in enumerate(levels)}


def _completed_level_ids(user_id: int) -> set[int]:
    with _db_connection() as connection:
        rows = connection.execute(
            "SELECT level_id FROM user_level_progress WHERE user_id = ?",
            (user_id,),
        ).fetchall()

    return {int(row["level_id"]) for row in rows}


def _mark_level_completed(user_id: int, level_id: int) -> None:
    completed_at = _now_utc().isoformat()
    with _db_connection() as connection:
        connection.execute(
            """
            INSERT INTO user_level_progress (user_id, level_id, completed_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, level_id)
            DO UPDATE SET completed_at = excluded.completed_at
            """,
            (user_id, level_id, completed_at),
        )


def _is_unlocked(level_index: int, levels: list[LevelConfig], completed_ids: set[int]) -> bool:
    if level_index == 0:
        return True
    previous_level_id = levels[level_index - 1].level_id
    return previous_level_id in completed_ids


def _current_level(levels: list[LevelConfig], completed_ids: set[int]) -> LevelConfig:
    current_level_index = 0
    for index, level in enumerate(levels):
        if not _is_unlocked(index, levels, completed_ids):
            break

        current_level_index = index
        if level.level_id not in completed_ids:
            return level

    return levels[current_level_index]


def _asset_images(assets_dir: Path) -> list[Path]:
    if not assets_dir.exists():
        return []

    return sorted(
        [
            path
            for path in assets_dir.iterdir()
            if path.is_file() and path.suffix.lower() in ALLOWED_IMAGE_EXTENSIONS
        ]
    )


def _asset_sources_from_dir(assets_dir: Path) -> tuple[AssetSource, ...]:
    images = _asset_images(assets_dir)
    return tuple(AssetSource(image_path=image.resolve(), source_url="") for image in images)


def _normalize_image(image_path: Path, rows: int, cols: int) -> Image.Image:
    with Image.open(image_path) as image:
        normalized = image.convert("RGBA")

    if normalized.width < cols or normalized.height < rows:
        raise HTTPException(
            status_code=500,
            detail=(
                "Image is too small for the configured grid size. "
                "Increase source image size or lower row/col values."
            ),
        )

    if normalized.width == normalized.height:
        return normalized

    square_side = min(normalized.width, normalized.height)
    left = (normalized.width - square_side) // 2
    top = (normalized.height - square_side) // 2
    return normalized.crop((left, top, left + square_side, top + square_side))


def _encode_tile_data_uri(image: Image.Image) -> str:
    buffer = BytesIO()
    rgba = image.convert("RGBA")
    flattened = Image.new("RGB", rgba.size, TILE_FILL_RGB)
    flattened.paste(rgba, mask=rgba.getchannel("A"))
    flattened.save(buffer, format="JPEG", quality=TILE_JPEG_QUALITY)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _rotation_choices_for_tile(tile: Image.Image) -> tuple[int, ...]:
    if tile.width != tile.height:
        options = tuple(rotation for rotation in ROTATION_CHOICES if rotation % 180 == 0)
        if options:
            return options
    return ROTATION_CHOICES


def _is_orientation_sensitive(tile: Image.Image, rotation_choices: tuple[int, ...]) -> bool:
    if len(rotation_choices) <= 1:
        return False

    base = tile.convert("RGBA")
    for rotation in rotation_choices:
        if rotation == 0:
            continue

        rotated = base.rotate(
            rotation,
            resample=Image.Resampling.BICUBIC,
            expand=False,
            fillcolor=TILE_FILL_RGBA,
        )
        diff = ImageChops.difference(base, rotated)
        diff_stats = ImageStat.Stat(diff)
        mean_diff = sum(diff_stats.mean) / len(diff_stats.mean)
        if mean_diff < ORIENTATION_DIFF_THRESHOLD:
            return False

    return True


def _split_and_rotate_tiles(
    image: Image.Image,
    rows: int,
    cols: int,
) -> tuple[list[str], list[int], list[bool], int, int]:
    x_edges = [round(index * image.width / cols) for index in range(cols + 1)]
    y_edges = [round(index * image.height / rows) for index in range(rows + 1)]

    min_tile_width = min(x_edges[index + 1] - x_edges[index] for index in range(cols))
    min_tile_height = min(y_edges[index + 1] - y_edges[index] for index in range(rows))

    if min_tile_width <= 0 or min_tile_height <= 0:
        raise HTTPException(
            status_code=500,
            detail=(
                "Grid resolution is too high for source image dimensions. "
                "Reduce rows/cols or use larger images."
            ),
        )

    tile_data: list[str] = []
    applied_rotations: list[int] = []
    checkable_mask: list[bool] = []

    for row in range(rows):
        for col in range(cols):
            left = x_edges[col]
            right = x_edges[col + 1]
            top = y_edges[row]
            bottom = y_edges[row + 1]
            tile = image.crop((left, top, right, bottom))

            rotation_choices = _rotation_choices_for_tile(tile)
            checkable_mask.append(_is_orientation_sensitive(tile, rotation_choices))

            rotation = random.choice(rotation_choices)
            applied_rotations.append(rotation)

            rotated_tile = tile.rotate(
                rotation,
                resample=Image.Resampling.BICUBIC,
                expand=False,
                fillcolor=TILE_FILL_RGBA,
            )
            tile_data.append(_encode_tile_data_uri(rotated_tile))

    return tile_data, applied_rotations, checkable_mask, min_tile_width, min_tile_height


def _object_name_for(path: Path) -> str:
    if path.name in ASSET_OBJECT_NAMES:
        return ASSET_OBJECT_NAMES[path.name]
    return DEFAULT_OBJECT_NAME


def _generate_puzzle(
    rows: int,
    cols: int,
    asset_sources: tuple[AssetSource, ...],
    owner_user_id: int | None = None,
    level_run_id: str | None = None,
    selected_source: AssetSource | None = None,
) -> PuzzleCreateResponse:
    _cleanup_expired_puzzles()

    if not asset_sources:
        raise HTTPException(status_code=500, detail="No asset sources are configured for this puzzle")

    if selected_source is None:
        chosen_source = random.choice(asset_sources)
    else:
        allowed_paths = {str(source.image_path.resolve()) for source in asset_sources}
        selected_path = selected_source.image_path.resolve()
        if str(selected_path) not in allowed_paths:
            raise HTTPException(status_code=500, detail="Configured image is outside puzzle source pool")
        chosen_source = selected_source

    selected_image_path = chosen_source.image_path.resolve()
    if (
        not selected_image_path.exists()
        or not selected_image_path.is_file()
        or selected_image_path.suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS
    ):
        raise HTTPException(
            status_code=500,
            detail=f"Configured image does not exist or is unsupported: {selected_image_path}",
        )

    image = _normalize_image(selected_image_path, rows, cols)

    (
        tiles,
        applied_rotations,
        checkable_mask,
        tile_width,
        tile_height,
    ) = _split_and_rotate_tiles(image, rows, cols)

    puzzle_id = uuid.uuid4().hex
    puzzle_response = PuzzleCreateResponse(
        puzzle_id=puzzle_id,
        object_name=_object_name_for(selected_image_path),
        rows=rows,
        cols=cols,
        rotation_step=ROTATION_STEP_DEGREES,
        image_width=image.width,
        image_height=image.height,
        tile_width=tile_width,
        tile_height=tile_height,
        tiles=tiles,
        source_url=chosen_source.source_url,
    )

    PUZZLES[puzzle_id] = PuzzleState(
        created_at=_now_utc(),
        applied_rotations=applied_rotations,
        checkable_mask=checkable_mask,
        rows=rows,
        cols=cols,
        puzzle_payload=puzzle_response.model_dump(),
        owner_user_id=owner_user_id,
        level_run_id=level_run_id,
    )

    return puzzle_response


def _normalize_rotations(rotations: list[int], state: PuzzleState) -> list[int]:
    expected_tile_count = state.rows * state.cols
    if len(rotations) != expected_tile_count:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Expected {expected_tile_count} rotations, "
                f"received {len(rotations)}"
            ),
        )

    normalized_rotations: list[int] = []
    for rotation in rotations:
        if rotation % ROTATION_STEP_DEGREES != 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Rotations must be multiples of {ROTATION_STEP_DEGREES} degrees"
                ),
            )
        normalized_rotations.append(rotation % 360)

    return normalized_rotations


def _incorrect_indices(state: PuzzleState, normalized_rotations: list[int]) -> list[int]:
    return [
        index
        for index, (applied, user_rotation) in enumerate(
            zip(state.applied_rotations, normalized_rotations)
        )
        if state.checkable_mask[index]
        if (applied - user_rotation) % 360 != 0
    ]


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Are You a Robot backend is running"}


@app.post("/api/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: AuthRequest) -> AuthResponse:
    email = _normalize_email(payload.email)
    _validate_password(payload.password)

    user = _create_user(email=email, password=payload.password)
    access_token = _create_access_token(user)

    return AuthResponse(access_token=access_token, token_type="bearer", user=user)


@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: AuthRequest) -> AuthResponse:
    email = _normalize_email(payload.email)
    user_row = _get_user_row_by_email(email)

    if user_row is None or not _verify_password(payload.password, str(user_row["password_hash"])):
        _raise_unauthorized("Invalid email or password")

    user = _user_from_row(user_row)
    access_token = _create_access_token(user)

    return AuthResponse(access_token=access_token, token_type="bearer", user=user)


@app.get("/api/auth/me", response_model=AuthMeResponse)
def get_me(current_user: UserResponse = Depends(_get_current_user)) -> AuthMeResponse:
    return AuthMeResponse(email=current_user.email, created_at=current_user.created_at)


@app.get("/api/levels", response_model=CurrentLevelResponse)
def list_levels(current_user: UserResponse = Depends(_get_current_user)) -> CurrentLevelResponse:
    levels = _load_level_configs()
    completed_ids = _completed_level_ids(current_user.id)
    current_level = _current_level(levels, completed_ids)
    return CurrentLevelResponse(
        level_id=current_level.level_id,
        cards_gap=current_level.cards_gap,
        completed_level_ids=sorted(completed_ids),
    )


@app.get("/api/puzzle/new", response_model=PuzzleCreateResponse)
def create_legacy_puzzle() -> PuzzleCreateResponse:
    return _generate_puzzle(
        rows=LEGACY_GRID_ROWS,
        cols=LEGACY_GRID_COLS,
        asset_sources=_asset_sources_from_dir(ASSETS_DIR),
    )


@app.post("/api/puzzle/check", response_model=PuzzleCheckResponse)
def check_legacy_puzzle(payload: PuzzleCheckRequest) -> PuzzleCheckResponse:
    _cleanup_expired_puzzles()

    state = PUZZLES.get(payload.puzzle_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Puzzle not found or expired")

    if state.level_run_id is not None:
        raise HTTPException(status_code=400, detail="Use /api/levels/check for level puzzles")

    normalized_rotations = _normalize_rotations(payload.rotations, state)
    incorrect_indices = _incorrect_indices(state, normalized_rotations)

    solved = len(incorrect_indices) == 0
    if solved:
        PUZZLES.pop(payload.puzzle_id, None)

    return PuzzleCheckResponse(solved=solved, incorrect_indices=[])


@app.post("/api/levels/{level_id}/start", response_model=LevelStartResponse)
def start_level(
    level_id: int,
    payload: LevelStartRequest | None = None,
    current_user: UserResponse = Depends(_get_current_user),
) -> LevelStartResponse:
    _cleanup_expired_level_runs()
    _cleanup_expired_puzzles()

    levels = _load_level_configs()
    level_by_id = _level_lookup(levels)

    if level_id not in level_by_id:
        raise HTTPException(status_code=404, detail="Level not found")

    completed_ids = _completed_level_ids(current_user.id)
    level_index = level_by_id[level_id]
    if not _is_unlocked(level_index, levels, completed_ids):
        raise HTTPException(status_code=403, detail="Level is locked")

    level = levels[level_index]
    force_restart = bool(payload.force_restart) if payload is not None else False

    existing_run_id: str | None = None
    existing_run: LevelRunState | None = None
    for run_id, run in LEVEL_RUNS.items():
        if run.user_id == current_user.id and run.level_id == level_id:
            existing_run_id = run_id
            existing_run = run
            break

    if existing_run is not None and not force_restart:
        if existing_run.expires_at <= _now_utc():
            timeout_reset = _reset_level_run_after_timeout(
                level_run_id=existing_run_id,
                level_run=existing_run,
                level=level,
                user_id=current_user.id,
            )
            if timeout_reset.next_puzzle is None or timeout_reset.expires_at is None:
                raise HTTPException(status_code=500, detail="Unable to resume level run")

            return LevelStartResponse(
                level_run_id=existing_run_id,
                level_id=level.level_id,
                level_name=level.name,
                puzzle_number=timeout_reset.puzzle_number,
                total_puzzles=timeout_reset.total_puzzles,
                puzzle_time_limit_seconds=level.time_limit_seconds,
                level_time_limit_seconds=level.time_limit_seconds,
                seconds_remaining=_seconds_remaining(timeout_reset.expires_at),
                expires_at=timeout_reset.expires_at,
                puzzle=timeout_reset.next_puzzle,
            )

        return _level_start_response_for_run(
            level_run_id=existing_run_id,
            level_run=existing_run,
            level=level,
        )

    for run_id, run in list(LEVEL_RUNS.items()):
        if run.user_id == current_user.id:
            _expire_level_run(run_id)

    puzzle_sources = _fixed_image_sequence_for_level(level)
    first_puzzle_cfg = level.puzzles[0]
    first_source = puzzle_sources[0]

    created_at = _now_utc()
    expires_at = created_at + timedelta(seconds=level.time_limit_seconds)
    level_run_id = uuid.uuid4().hex

    first_puzzle = _generate_puzzle(
        rows=first_puzzle_cfg.rows,
        cols=first_puzzle_cfg.cols,
        asset_sources=first_puzzle_cfg.asset_sources,
        owner_user_id=current_user.id,
        level_run_id=level_run_id,
        selected_source=first_source,
    )

    LEVEL_RUNS[level_run_id] = LevelRunState(
        user_id=current_user.id,
        level_id=level_id,
        created_at=created_at,
        expires_at=expires_at,
        puzzle_index=0,
        total_puzzles=len(level.puzzles),
        current_puzzle_id=first_puzzle.puzzle_id,
        puzzle_sources=puzzle_sources,
    )

    return LevelStartResponse(
        level_run_id=level_run_id,
        level_id=level.level_id,
        level_name=level.name,
        puzzle_number=1,
        total_puzzles=len(level.puzzles),
        puzzle_time_limit_seconds=level.time_limit_seconds,
        level_time_limit_seconds=level.time_limit_seconds,
        seconds_remaining=level.time_limit_seconds,
        expires_at=expires_at,
        puzzle=first_puzzle,
    )


@app.post("/api/levels/check", response_model=LevelCheckResponse)
def check_level_puzzle(
    payload: LevelCheckRequest,
    current_user: UserResponse = Depends(_get_current_user),
) -> LevelCheckResponse:
    _cleanup_expired_level_runs()
    _cleanup_expired_puzzles()

    level_run = LEVEL_RUNS.get(payload.level_run_id)
    if level_run is None or level_run.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Level run not found")

    levels = _load_level_configs()
    level_by_id = _level_lookup(levels)
    if level_run.level_id not in level_by_id:
        raise HTTPException(status_code=404, detail="Level not found")

    level = levels[level_by_id[level_run.level_id]]

    if level_run.puzzle_index >= len(level.puzzles):
        raise HTTPException(status_code=400, detail="Invalid level run state")

    if level_run.expires_at <= _now_utc():
        return _reset_level_run_after_timeout(
            level_run_id=payload.level_run_id,
            level_run=level_run,
            level=level,
            user_id=current_user.id,
        )

    if level_run.current_puzzle_id != payload.puzzle_id:
        raise HTTPException(status_code=400, detail="Puzzle does not match active level state")

    state = PUZZLES.get(payload.puzzle_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Puzzle not found or expired")

    if state.owner_user_id is not None and state.owner_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have access to this puzzle")

    if state.level_run_id != payload.level_run_id:
        raise HTTPException(status_code=400, detail="Puzzle does not belong to this level run")

    normalized_rotations = _normalize_rotations(payload.rotations, state)
    incorrect_indices = _incorrect_indices(state, normalized_rotations)

    if incorrect_indices:
        level_run.expires_at = level_run.expires_at - timedelta(seconds=WRONG_ANSWER_PENALTY_SECONDS)
        if level_run.expires_at <= _now_utc():
            return _reset_level_run_after_timeout(
                level_run_id=payload.level_run_id,
                level_run=level_run,
                level=level,
                user_id=current_user.id,
            )

        return LevelCheckResponse(
            solved=False,
            incorrect_indices=[],
            level_completed=False,
            puzzle_number=level_run.puzzle_index + 1,
            total_puzzles=level_run.total_puzzles,
            expires_at=level_run.expires_at,
            next_puzzle=None,
        )

    PUZZLES.pop(payload.puzzle_id, None)

    next_index = level_run.puzzle_index + 1
    if next_index >= level_run.total_puzzles:
        LEVEL_RUNS.pop(payload.level_run_id, None)
        _mark_level_completed(current_user.id, level_run.level_id)
        return LevelCheckResponse(
            solved=True,
            incorrect_indices=[],
            level_completed=True,
            puzzle_number=level_run.total_puzzles,
            total_puzzles=level_run.total_puzzles,
            expires_at=None,
            next_puzzle=None,
            flag=level.flag,
        )

    next_puzzle_cfg = level.puzzles[next_index]
    next_source = level_run.puzzle_sources[next_index]

    next_puzzle = _generate_puzzle(
        rows=next_puzzle_cfg.rows,
        cols=next_puzzle_cfg.cols,
        asset_sources=next_puzzle_cfg.asset_sources,
        owner_user_id=current_user.id,
        level_run_id=payload.level_run_id,
        selected_source=next_source,
    )

    level_run.puzzle_index = next_index
    level_run.current_puzzle_id = next_puzzle.puzzle_id

    return LevelCheckResponse(
        solved=True,
        incorrect_indices=[],
        level_completed=False,
        puzzle_number=next_index + 1,
        total_puzzles=level_run.total_puzzles,
        expires_at=level_run.expires_at,
        next_puzzle=next_puzzle,
    )
