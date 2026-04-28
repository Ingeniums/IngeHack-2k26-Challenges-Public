import importlib.util
import os
import tempfile
import unittest
import uuid
from pathlib import Path

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


REPO_ROOT = Path(__file__).resolve().parents[2]
APP_MAIN_PATH = REPO_ROOT / "backend" / "app" / "main.py"


def load_app_module():
    os.environ["JWT_SECRET"] = "test-secret"

    spec = importlib.util.spec_from_file_location(
        f"board_puzzles_main_{uuid.uuid4().hex}",
        APP_MAIN_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class AuthTokenBindingTests(unittest.TestCase):
    def test_token_resolves_current_user_when_account_matches(self):
        module = load_app_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "app.db"
            module.DATABASE_PATH = db_path
            module._init_db()

            alice = module._create_user("alice@example.com", "password123")
            token = module._create_access_token(alice)

            resolved = module._get_current_user(
                HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
            )

        self.assertEqual(resolved.id, alice.id)
        self.assertEqual(resolved.email, alice.email)

    def test_token_is_rejected_when_user_id_is_reused_by_another_account(self):
        module = load_app_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "app.db"
            module.DATABASE_PATH = db_path
            module._init_db()

            alice = module._create_user("alice@example.com", "password123")
            token = module._create_access_token(alice)

            db_path.unlink()
            module._init_db()

            bob = module._create_user("bob@example.com", "password123")
            self.assertEqual(alice.id, bob.id)

            with self.assertRaises(HTTPException) as raised:
                module._get_current_user(
                    HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
                )

        self.assertEqual(raised.exception.status_code, 401)
        self.assertEqual(raised.exception.detail, "Token user mismatch")
