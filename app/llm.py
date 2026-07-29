import logging

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError

from app.config import settings

looger = logging.getLogger(__name__)

# Ordered by free-tier headroom, most available first.
# Each model has its own separate daily quota, so rotating through them
# effectively combines multiple 20/day limits into one larger pool.
MODEL_FALLBACK_ORDER = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]


class RotatingLLM:
    """Wraps several Gemini models and falls back to the next one whenever
    a model's free-tier daily quota is exhausted (429 RESOURCE_EXHAUSTED)."""

    def __init__(self, model_names: list[str], **kwargs):
        self._model_names = model_names
        self._kwargs = kwargs
        self._models = [
            ChatGoogleGenerativeAI(model=name, **kwargs) for name in model_names
        ]

    async def ainvoke(self, *args, **kwargs):
        last_error = None
        for name, model in zip(self._model_names, self._models):
            try:
                result = await model.ainvoke(*args, **kwargs)
                logger.info(f"LLM call succeeded using model: {name}")
                return result
            except ChatGoogleGenerativeAIError as e:
                if "RESOURCE_EXHAUSTED" in str(e):
                    logger.warning(
                        f"Model {name} quota exhausted, trying next model..."
                    )
                    last_error = e
                    continue
                raise
        raise last_error

    def bind_tools(self, tools):
        bound = RotatingLLM.__new__(RotatingLLM)
        bound._model_names = self._model_names
        bound._kwargs = self._kwargs
        bound._models = [m.bind_tools(tools) for m in self._models]
        return bound


llm = RotatingLLM(MODEL_FALLBACK_ORDER, google_api_key=settings.google_api_key)

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=settings.google_api_key,
)
