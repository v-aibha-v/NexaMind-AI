# 16 — Direct Groq Integration (Portkey Removed)

> **One-line summary:** The backend now calls the Groq API directly through the
> official `langchain-groq` integration (`ChatGroq`). The Portkey LLM gateway
> has been removed from the LLM request path.

---

## Architecture

Frontend (Streamlit)
        |
Backend (FastAPI)
        |
LangGraph Workflow
        |
LangChain LLM Integration (`ChatGroq`)
        |
Groq API (Direct Connection)

Every LLM call now goes straight to Groq (https://api.groq.com/openai/v1)
through `langchain-groq`. There is no gateway, proxy, or fallback service in
the middle.

## What changed

| Before (Portkey) | After (direct Groq) |
|------------------|---------------------|
| `app/gateway/client.py` used `portkey_ai` (`Portkey` client + `ChatOpenAI` pointed at `PORTKEY_GATEWAY_URL`) | `app/gateway/client.py` uses `langchain_groq.ChatGroq` pointed directly at Groq |
| `PORTKEY_API_KEY`, `GROQ_SLUG`, `GROQ_SLUG_2` settings | Removed; only `GROQ_API_KEY` and `GROQ_MODEL` are used |
| Automatic fallback: primary `llama-3.3-70b-versatile` → fallback `llama-3.1-8b-instant` | Removed. A single `GROQ_API_KEY` serves both planner and responder |
| Gateway cache (semantic/simple) + `x-portkey-cache-status` reads | Removed; no `"Cache: Hit ⚡"` plan step |
| Gateway retry (2 attempts on 429/503) | Removed; errors surface to the existing `app/main.py` error handler |
| Portkey dashboard observability | Removed; Logfire + LangSmith tracing preserved |

## Why ChatGroq (not ChatOpenAI + base_url)

`ChatGroq` is the official LangChain Groq integration. It speaks Groq’s API
directly and exposes the standard LangChain `.invoke()` / `.content` interface,
so the planner and responder nodes needed no logic changes — only the client
underneath was swapped.

## LLM consumers and parameters (preserved)

| Consumer | File | Model | Temperature |
|----------|------|-------|-------------|
| Planner | `app/agents/nodes/planner.py` | `llama-3.3-70b-versatile` (`GROQ_MODEL`) | 0 |
| Responder | `app/agents/nodes/responder.py` | `llama-3.3-70b-versatile` (`GROQ_MODEL`) | 0.1 |
| Guardrails | `app/guardrails/rails.py` | `llama-3.1-8b-instant` | 0 |

The guardrails LLM already called Groq directly via `ChatGroq`; it is
unchanged.

## Code

`app/gateway/client.py`:

```python
from langchain_groq import ChatGroq
from app.config import settings


def get_langchain_llm(feature: str = "rag", temperature: float = 0) -> ChatGroq:
    return ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=settings.GROQ_MODEL,
        temperature=temperature,
    )
```

Planner (`app/agents/nodes/planner.py`) — unchanged call site:

```python
from app.gateway import get_langchain_llm
llm = get_langchain_llm(feature="planner")   # temperature 0
decision = llm.invoke(prompt).content
```

Responder (`app/agents/nodes/responder.py`) — unchanged temperature:

```python
llm = get_langchain_llm(feature="responder", temperature=0.1)
response = llm.invoke(prompt)
content = response.content
```

## Fallback behavior — documented change

Portkey provided automatic fallback from the primary model to a secondary
model/key on failure. That capability is **removed** with Portkey. No new
gateway or paid service replaces it. `GROQ_FALLBACK_API_KEY` remains listed in
`.env.example` for documentation but is not consumed by code. If the single
Groq key/endpoint is unavailable, the error is surfaced through the existing
graceful error path in `app/main.py` rather than silently failing.

## Environment variables

Set `GROQ_API_KEY` in `.env` (copied from `.env.example`). `PORTKEY_API_KEY`
is no longer used and has been removed from configuration.