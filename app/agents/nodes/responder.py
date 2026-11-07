import logfire
from app.agents.state import AgentState
from app.gateway import get_langchain_llm


def generate_node(state: AgentState):
    """
    Synthesizes a response using both Documentation Context AND Conversation History.
    Uses LangChain ChatGroq connected directly to the Groq API (no Portkey
    gateway). Temperature 0.1 matches the original responder configuration.
    """
    query = state["current_query"]

    history_str = ""
    for msg in state["messages"][:-1]:
        role = "User" if msg["role"] == "user" else "Assistant"
        history_str += f"{role}: {msg['content']}\n"

    user_msg = state["messages"][-1]["content"] if state["messages"] else ""

    if query == "CONVERSATIONAL":
        logfire.info("Generating conversational response using memory.")
        prompt = f"""
        You are a friendly and helpful Enterprise AI Assistant.
        Answer the user's latest message using the CONVERSATION HISTORY below.

        CONVERSATION HISTORY:
        {history_str}

        LATEST MESSAGE:
        "{user_msg}"
        """
    else:
        logfire.info("Generating technical RAG response.")
        max_context_chars = 25000
        full_context = ""

        for doc in state["documents"]:
            if len(full_context) + len(doc) < max_context_chars:
                full_context += doc + "\n\n"
            else:
                logfire.warning("Context truncated to fit Groq TPM limits.")
                break

        prompt = f"""
        You are a Senior Technical Architect.
        Answer the question using the TECHNICAL CONTEXT provided.

        TECHNICAL CONTEXT:
        {full_context}

        CONVERSATION HISTORY:
        {history_str}

        USER QUESTION:
        "{user_msg}"
        """

    with logfire.span("✍️ LLM Synthesis"):
        try:
            llm = get_langchain_llm(feature="responder", temperature=0.1)
            response = llm.invoke(prompt)
            content = response.content

            # Direct Groq connection: no Portkey gateway cache, so there is no
            # x-portkey-cache-status header to read. The "Cache: Hit ⚡" plan
            # step is removed (see PORTKEY_REMOVAL_PLAN.md and FALLBACK_IMPACT.md).
            logfire.info("✅ Response synthesised via direct Groq connection.")
            plan_update = state["plan"]
            status = "Response generated."

            return {
                "final_answer": content,
                "status": status,
                "plan": plan_update,
                "messages": [{"role": "assistant", "content": content}]
            }

        except Exception as e:
            logfire.error(f"LLM Generation failed: {e}")
            raise e
