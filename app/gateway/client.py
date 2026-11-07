import logfire
from langchain_groq import ChatGroq

from app.config import settings


def get_langchain_llm(feature: str = "rag", temperature: float = 0) -> ChatGroq:
    """
    Returns a LangChain LLM backed by Groq directly (no Portkey gateway).

    Replaces the previous Portkey-backed ChatOpenAI. Requests now go straight
    to the Groq API (https://api.groq.com/openai/v1) via the official
    langchain-groq integration.

    Parameters
    ----------
    feature : str
        Call-site label (e.g. "planner", "responder"). Kept for compatibility
        with existing callers; recorded in Logfire but no longer drives
        Portkey routing (that capability is removed with Portkey).
    temperature : float
        Sampling temperature. The planner uses 0; the responder uses 0.1 —
        both values are preserved from the original implementation.
    """
    logfire.info(
        "🦙 Groq LLM initialised",
        feature=feature,
        model=settings.GROQ_MODEL,
        temperature=temperature,
    )
    return ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=settings.GROQ_MODEL,
        temperature=temperature,
    )