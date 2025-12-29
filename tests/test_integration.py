import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from model import Base, get_db
from main import app
from schema import UserModel, TokenModel

@pytest_asyncio.fixture
async def async_client(tmp_path):
    # 🔹 Создаем отдельный файл SQLite для теста
    db_file = tmp_path / "test.db"
    test_db_url = f"sqlite+aiosqlite:///{db_file}"

    # 🔹 Создаем test engine и session
    engine = create_async_engine(test_db_url, echo=True)
    TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    # 🔹 Создаем таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 🔹 Патчим get_db() в FastAPI
    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # 🔹 Запускаем lifespan приложения
    await app.router.startup()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    await app.router.shutdown()


@pytest.mark.asyncio
async def test_user_registration_flow(async_client):
    # 🔹 Регистрируем пользователя
    response = await async_client.post(
        "/register",
        json={"username": "testuser", "password": "testpass123", "role": "user"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["expires_in"]

    access_token = data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 🔹 Проверяем доступ к /read_user
    auth_response = await async_client.get("/read_user", headers=headers)
    assert auth_response.status_code == 200
    auth_data = auth_response.json()
    assert "Welcome, testuser" in auth_data["message"]

    # 🔹 Проверяем login
    login_response = await async_client.post(
        "/login",
        json={"username": "testuser", "password": "testpass123", "role": "user"},
    )
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert login_data["access_token"]
    assert login_data["refresh_token"]

    # 🔹 Проверяем refresh токен
    refresh_response = await async_client.post(
        "/refresh",
        json={"refresh_token": login_data["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    refresh_data = refresh_response.json()
    assert refresh_data["access_token"]
    assert refresh_data["refresh_token"]
