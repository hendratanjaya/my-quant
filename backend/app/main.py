from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference

from app.model.engine import init_db
from app.modules.ohlcv.router import router as ohlcv_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ohlcv_router)


@app.get("/scalar", include_in_schema=False)
def get_scalar():
    return get_scalar_api_reference(openapi_url=app.openapi_url, title=app.title)
