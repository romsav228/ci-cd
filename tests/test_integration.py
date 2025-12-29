import os
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from model import Base, User, get_db
from main import app

@pytest.mark.asyncio
async def test_user_registration_flow(tmp_path):
    # 🔹 Создаем отдельный файл БД для теста
    db_file = tmp_path / "test.db"
    test_db_url = f"sqlite+aiosqlite:///{db_file}"
    os.environ["DATABASE_URL"] = test_db_url

    # 🔹 Создаем тестовый engine и session
    engine = create_async_engine(test_db_url, echo=True)
    TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    # 🔹 Создаем все таблицы в тестовой БД
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 🔹 Патчим get_db() в main для теста
    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # 🔹 Запускаем lifespan приложения
    await app.router.startup()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:

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

            headers = {"Authorization": f"Bearer {data['access_token']}"}
            auth_response = await client.get("/read_user", headers=headers)
            assert auth_response.status_code == 200
    finally:
        await app.router.shutdown()
