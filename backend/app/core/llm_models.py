from agents.extensions.models.any_llm_model import AnyLLMModel
from openai import AsyncOpenAI

from app.core.settings import settings

_BASE_URL = "https://openrouter.ai/api/v1"

analysis_model = AnyLLMModel(
    api_key=settings.open_router_key,
    base_url=_BASE_URL,
    model="openrouter/deepseek/deepseek-v4-pro",
)

embedding_model = AnyLLMModel(
    api_key=settings.open_router_key,
    base_url=_BASE_URL,
    model="openrouter/openai/text-embedding-3-small",
)

# Shared client for direct embedding calls (AnyLLMModel doesn't expose embeddings API)
embed_client = AsyncOpenAI(api_key=settings.open_router_key, base_url=_BASE_URL)
EMBED_MODEL = "openai/text-embedding-3-small"
