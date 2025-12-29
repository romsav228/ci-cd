from contextlib import asynccontextmanager

from fastapi import FastAPI

from api import api_router
from model import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown (если понадобится)
    # await close_db()


app = FastAPI(
    title="Auth Service",
    lifespan=lifespan,
)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}


app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # только для локальной разработки
    )
