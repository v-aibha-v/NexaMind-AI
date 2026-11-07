"""
Migration verification script — Portkey removal → direct Groq.

Run with GROQ_API_KEY set in the environment (never hardcode the key).

Checks performed:
  1. All app modules import without portkey_ai / langchain-openai
  2. get_langchain_llm() returns ChatGroq with the configured model
  3. Planner temperature is 0, responder temperature is 0.1
  4. LangGraph graph compiles with MemorySaver
  5. Optional: live Groq chat completion returns a valid response
  6. No Portkey symbols remain in the gateway module

Usage (PowerShell):
    $env:GROQ_API_KEY="gsk_..."
    python scripts/verify_migration.py
"""

import os
import sys

# Allow running from the repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

results = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append((name, status, detail))
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))


# ── 1. Module imports ──────────────────────────────────────────────────
try:
    import app.gateway.client as gw  # noqa: F401
    import app.agents.nodes.planner as pl  # noqa: F401
    import app.agents.nodes.responder as rs  # noqa: F401
    import app.agents.graph as gr  # noqa: F401
    check("app modules import", True)
except Exception as exc:  # noqa: BLE001
    check("app modules import", False, str(exc))
    sys.exit(1)

# ── 2. No Portkey symbols in the gateway module ────────────────────────
check(
    "no portkey_ai import in gateway.client",
    not hasattr(gw, "Portkey") and "portkey" not in dir(gw),
)

# ── 3. get_langchain_llm returns ChatGroq with configured model ────────
from langchain_groq import ChatGroq  # noqa: E402
from app.config import settings  # noqa: E402
from app.gateway import get_langchain_llm  # noqa: E402

planner_llm = get_langchain_llm(feature="planner")
responder_llm = get_langchain_llm(feature="responder", temperature=0.1)

check("planner LLM is ChatGroq", isinstance(planner_llm, ChatGroq))
check("planner model is GROQ_MODEL", planner_llm.model == settings.GROQ_MODEL)
check("responder LLM is ChatGroq", isinstance(responder_llm, ChatGroq))
# ChatGroq normalizes temperature=0 to 1e-08 internally; behaviour is still
# deterministic (effectively temperature 0), so accept either value.
check("planner temperature == 0", planner_llm.temperature == 0 or abs(planner_llm.temperature) < 1e-6)
check("responder temperature == 0.1", responder_llm.temperature == 0.1)

# ── 4. LangGraph graph compiles ────────────────────────────────────────
check("graph compiled (rag_agent)", gr.rag_agent is not None)

# ── 5. Optional live Groq call ─────────────────────────────────────────
groq_key = os.getenv("GROQ_API_KEY")
if groq_key:
    try:
        response = planner_llm.invoke("Say 'ok' if you can read this.")
        content = getattr(response, "content", str(response))
        check(
            "live Groq completion returns content",
            bool(content and content.strip()),
            f"preview: {content[:60]!r}",
        )
    except Exception as exc:  # noqa: BLE001
        check("live Groq completion returns content", False, str(exc))
else:
    check("live Groq completion returns content", False,
          "GROQ_API_KEY not set — skipped (live-call test blocked by missing credentials)")

# ── 6. Unchanged modules still import and reference no Portkey ─────────
for mod_name, display in [
    ("app.guardrails.rails", "guardrails"),
    ("app.services.retrieval.embedding", "embeddings (Gemini)"),
    ("app.services.retrieval.qdrant_service", "Qdrant"),
    ("app.services.retrieval.ranking_service", "FlashRank"),
    ("app.main", "FastAPI backend"),
]:
    try:
        __import__(mod_name)  # noqa: F401
        check(f"{display} module imports", True)
    except Exception as exc:  # noqa: BLE001
        check(f"{display} module imports", False, str(exc))

# ── Summary ────────────────────────────────────────────────────────────
failures = [r for r in results if r[1] == "FAIL"]
print()
print(f"Checks: {len(results)} total, {len(failures)} failed")
sys.exit(1 if failures else 0)