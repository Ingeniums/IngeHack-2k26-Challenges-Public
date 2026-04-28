from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Dict, List, Tuple
from uuid import uuid4

import numpy as np


BOARD_SIZE = 16
LANE_WIDTH = 127 * 2
FILES = [chr(ord("a") + index) for index in range(BOARD_SIZE)]
RANKS = list(range(BOARD_SIZE, 0, -1))
ROOT = Path(__file__).resolve().parent
DEFAULT_FLAG = "ingehack{this_is_a_local_test_flag}"


def load_flag() -> str:
    env_flag = os.getenv("FLAG")
    if env_flag:
        return env_flag.strip()

    flag_path = ROOT / "flag.txt"
    if flag_path.exists():
        return flag_path.read_text(encoding="utf-8").strip()

    return DEFAULT_FLAG


FLAG_VALUE = load_flag()


PIECE_DEFS = [
    {"id": "bishop-1", "label": "Bishop I", "glyph": "♗", "type": "bishop", "start": "c1", "target": "h6"},
    {"id": "bishop-2", "label": "Bishop II", "glyph": "♗", "type": "bishop", "start": "f1", "target": "l7"},
    {"id": "bishop-3", "label": "Bishop III", "glyph": "♗", "type": "bishop", "start": "n1", "target": "h7"},
    {"id": "queen-1", "label": "Queen I", "glyph": "♕", "type": "queen", "start": "g1", "target": "n8"},
    {"id": "queen-2", "label": "Queen II", "glyph": "♕", "type": "queen", "start": "j1", "target": "d7"},
    {"id": "queen-3", "label": "Queen III", "glyph": "♕", "type": "queen", "start": "p1", "target": "p9"},
    {"id": "knight-1", "label": "Knight I", "glyph": "♘", "type": "knight", "start": "b6", "target": "c8"},
    {"id": "knight-2", "label": "Knight II", "glyph": "♘", "type": "knight", "start": "o5", "target": "m6"},
    {"id": "king-1", "label": "King I", "glyph": "♔", "type": "king", "start": "a7", "target": "b8"},
    {"id": "king-2", "label": "King II", "glyph": "♔", "type": "king", "start": "o7", "target": "o6"},
]


SQUARE_RE = re.compile(r"^([a-z]+)(\d+)$")


@dataclass
class PieceState:
    id: str
    label: str
    glyph: str
    type: str
    position: str
    target: str
    locked: bool = False


@dataclass
class MoveResult:
    ok: bool
    message: str
    flag: str | None = None


def coords_to_notation(x: int, y: int) -> str:
    return f"{FILES[x]}{BOARD_SIZE - y}"


def notation_to_coords(square: str) -> Tuple[int, int]:
    match = SQUARE_RE.fullmatch(square)
    if not match:
        raise ValueError(f"invalid square: {square}")

    file_name, rank_value = match.groups()
    if file_name not in FILES:
        raise ValueError(f"invalid file: {file_name}")

    rank = int(rank_value)
    if rank < 1 or rank > BOARD_SIZE:
        raise ValueError(f"invalid rank: {rank}")

    return FILES.index(file_name), BOARD_SIZE - rank


def square_to_linear(square: str) -> int:
    x, y = notation_to_coords(square)
    return y * BOARD_SIZE + x


def linear_to_square(index: int) -> str:
    if index < 0 or index >= BOARD_SIZE * BOARD_SIZE:
        raise ValueError(f"invalid board index: {index}")
    y, x = divmod(index, BOARD_SIZE)
    return coords_to_notation(x, y)


class ChallengeSession:
    def __init__(self) -> None:
        self.layout = np.full((len(PIECE_DEFS), LANE_WIDTH), -1, dtype=np.int16)
        self.pieces: List[PieceState] = self._build_pieces()

    def _build_pieces(self) -> List[PieceState]:
        self.layout.fill(-1)
        pieces: List[PieceState] = []
        for index, piece_def in enumerate(PIECE_DEFS):
            target_index = square_to_linear(piece_def["target"])
            if target_index >= LANE_WIDTH:
                raise ValueError("target index exceeds lane width")
            self.layout[index, target_index] = index
            pieces.append(
                PieceState(
                    id=piece_def["id"],
                    label=piece_def["label"],
                    glyph=piece_def["glyph"],
                    type=piece_def["type"],
                    position=piece_def["start"],
                    target=piece_def["target"],
                )
            )
        return pieces

    def reset(self) -> None:
        self.pieces = self._build_pieces()

    def public_state(self) -> Dict[str, object]:
        return {
            "board_size": BOARD_SIZE,
            "files": FILES,
            "ranks": RANKS,
            "targets": [piece.target for piece in self.pieces],
            "pieces": [
                {
                    "id": piece.id,
                    "label": piece.label,
                    "glyph": piece.glyph,
                    "type": piece.type,
                    "position": piece.position,
                    "locked": piece.locked,
                }
                for piece in self.pieces
            ],
            "solved": self.is_solved(),
            "flag": self.flag() if self.is_solved() else None,
        }

    def is_solved(self) -> bool:
        return all(piece.locked for piece in self.pieces)

    def flag(self) -> str:
        return FLAG_VALUE

    def move(self, piece_id: str, value: int) -> MoveResult:
        piece = self._piece_by_id(piece_id)
        if piece is None:
            return MoveResult(False, "Unknown piece.")

        if piece.locked:
            return MoveResult(False, f"{piece.label} is already locked.")

        if self.is_solved():
            return MoveResult(False, "Session already solved.", self.flag())

        if value < 0 or value > 255:
            return MoveResult(False, "Value outside accepted range.")

        piece_index = self._index_by_id(piece_id)
        slot = int(np.uint8(value).view(np.int8))
        if slot >= 0:
            return MoveResult(False, "Selection rejected.")

        landing_index = LANE_WIDTH + slot
        try:
            landing_square = linear_to_square(landing_index)
        except ValueError:
            return MoveResult(False, "Selection fell outside board.")

        occupancy = self._occupancy()
        dest_x, dest_y = notation_to_coords(landing_square)
        current_x, current_y = notation_to_coords(piece.position)

        if occupancy[dest_y, dest_x] != -1:
            return MoveResult(False, f"Landing square {landing_square} is occupied.")

        owner_index = int(self.layout[piece_index, slot])
        if owner_index != piece_index:
            return MoveResult(False, f"Selection {value} landed on {landing_square}, but it was not accepted.")

        if not self._is_legal_move(piece, current_x, current_y, dest_x, dest_y):
            return MoveResult(False, f"{piece.label} cannot move to {landing_square}.")

        if not self._path_is_clear(piece, occupancy, current_x, current_y, dest_x, dest_y):
            return MoveResult(False, f"Path blocked for {piece.label}.")

        piece.position = landing_square
        piece.locked = True
        if self.is_solved():
            return MoveResult(True, f"{piece.label} locked at {landing_square}. Board accepted.", self.flag())

        return MoveResult(True, f"{piece.label} locked at {landing_square}.")

    def _occupancy(self) -> np.ndarray:
        occupancy = np.full((BOARD_SIZE, BOARD_SIZE), -1, dtype=np.int16)
        for index, piece in enumerate(self.pieces):
            x, y = notation_to_coords(piece.position)
            if not piece.locked:
                occupancy[y, x] = index
        return occupancy

    def _piece_by_id(self, piece_id: str) -> PieceState | None:
        for piece in self.pieces:
            if piece.id == piece_id:
                return piece
        return None

    def _index_by_id(self, piece_id: str) -> int:
        for index, piece in enumerate(self.pieces):
            if piece.id == piece_id:
                return index
        raise KeyError(piece_id)

    @staticmethod
    def _is_legal_move(piece: PieceState, from_x: int, from_y: int, to_x: int, to_y: int) -> bool:
        dx = to_x - from_x
        dy = to_y - from_y
        abs_x = abs(dx)
        abs_y = abs(dy)

        if dx == 0 and dy == 0:
            return False

        if piece.type == "bishop":
            return abs_x == abs_y
        if piece.type == "queen":
            return dx == 0 or dy == 0 or abs_x == abs_y
        if piece.type == "knight":
            return (abs_x == 1 and abs_y == 2) or (abs_x == 2 and abs_y == 1)
        if piece.type == "king":
            return max(abs_x, abs_y) == 1
        return False

    @staticmethod
    def _path_is_clear(
        piece: PieceState,
        occupancy: np.ndarray,
        from_x: int,
        from_y: int,
        to_x: int,
        to_y: int,
    ) -> bool:
        if piece.type in {"knight", "king"}:
            return True

        step_x = int(np.sign(to_x - from_x))
        step_y = int(np.sign(to_y - from_y))
        x = from_x + step_x
        y = from_y + step_y

        while x != to_x or y != to_y:
            if occupancy[y, x] != -1:
                return False
            x += step_x
            y += step_y

        return True


class SessionStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._sessions: Dict[str, ChallengeSession] = {}

    def ensure(self, session_id: str | None) -> Tuple[str, ChallengeSession]:
        with self._lock:
            if session_id and session_id in self._sessions:
                return session_id, self._sessions[session_id]

            new_id = uuid4().hex
            session = ChallengeSession()
            self._sessions[new_id] = session
            return new_id, session

    def reset(self, session_id: str) -> ChallengeSession:
        with self._lock:
            session = self._sessions[session_id]
            session.reset()
            return session
