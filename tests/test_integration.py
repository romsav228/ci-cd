import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from model import Base, get_db
from main import app
from schema import UserModel, TokenModel

# -----------------------------
# Один engine для всей сессии
# -----------------------------
@pytest_asyncio.fixture(scope="session")
async def test_engine():
    # In-memory SQLite для быстрого теста
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=True
    )

    # Создаем все таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


# -----------------------------
# ASGI клиент для тестов
# -----------------------------
@pytest_asyncio.fixture(scope="session")
async def async_client(test_engine):
    TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)

    # Патчим get_db() для использования тестового engine
    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # Запускаем lifespan приложения
    await app.router.startup()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client
    await app.router.shutdown()


# -----------------------------
# Тест регистрации, логина и refresh
# -----------------------------
@pytest.mark.asyncio
async def test_user_registration_flow(async_client):
    # Регистрация пользователя
    response = await async_client.post(
        "/register",
        json={"username": "testuser", "password": "testpass123", "role": "user"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]
    access_token = data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Проверка доступа к /read_user
    auth_response = await async_client.get("/read_user", headers=headers)
    assert auth_response.status_code == 200
    assert "Welcome, testuser" in auth_response.json()["message"]

    # Логин
    login_response = await async_client.post(
        "/login",
        json={"username": "testuser", "password": "testpass123", "role": "user"}
    )
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert login_data["access_token"]
    assert login_data["refresh_token"]

    # Refresh токен
    refresh_response = await async_client.post(
        "/refresh",
        json={"refresh_token": login_data["refresh_token"]}
    )
    assert refresh_response.status_code == 200
    refresh_data = refresh_response.json()
    assert refresh_data["access_token"]
    assert refresh_data["refresh_token"]
