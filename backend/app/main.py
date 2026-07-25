from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference

from app.core.chroma_client import get_chroma
from app.model.engine import init_db
from app.modules.chat.router import router as chat_router
from app.modules.fundamental.router import router as fundamental_router
from app.modules.ohlcv.router import router as ohlcv_router
from app.modules.portfolio.router import router as portfolio_router
from app.modules.screen.router import router as screen_router
from app.modules.seed.router import router as seed_router
from app.modules.telegram.router import router as telegram_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    get_chroma()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ohlcv_router)
app.include_router(fundamental_router)
app.include_router(seed_router)
app.include_router(portfolio_router)
app.include_router(chat_router)
app.include_router(screen_router)
app.include_router(telegram_router)


@app.get("/scalar", include_in_schema=False)
def get_scalar():
    return get_scalar_api_reference(openapi_url=app.openapi_url, title=app.title)
