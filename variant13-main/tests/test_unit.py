from fastapi.testclient import TestClient

from api import hash_password, verify_password
from main import app

client = TestClient(app)


def test_hash_password():
    """Ensure hashing produces different salts and verification works"""
    password = "s3cret-password"

    h1 = hash_password(password)
    h2 = hash_password(password)
    assert isinstance(h1, str) and isinstance(h2, str)
    assert h1 != h2

    assert verify_password(password, h1) is True
    assert verify_password(password, h2) is True

    assert verify_password("wrong-pass", h1) is False
