import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_user_registration_flow():
    async with AsyncClient(
        transport=ASGITransport(app=app, lifespan="on"),
        base_url="http://test",
    ) as client:
        # Test user registration
        response = await client.post(
            "/register",
            json={
                "username": "testuser",
                "password": "testpass123",
                "role": "user",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["access_token"]
        assert data["refresh_token"]
        assert data["expires_in"]

        access_token = data["access_token"]

        headers = {"Authorization": f"Bearer {access_token}"}
        auth_response = await client.get("/read_user", headers=headers)

        assert auth_response.status_code == 200
