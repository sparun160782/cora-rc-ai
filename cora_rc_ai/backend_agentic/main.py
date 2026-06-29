"""
CORA Agentic AI Backend - Google ADK Runner wrapped in FastAPI with SSE streaming.
Exposes: POST /v1/agent/chat/stream  and  POST /v1/agent/chat
"""
import os

# Load environment variables from .env (DB credentials, Ollama, etc.)
# BEFORE importing any module that reads them at import time.
from dotenv import load_dotenv, find_dotenv
# .env lives at cora_rc_ai/.env (two levels up from this file).
_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(_env_path if os.path.exists(_env_path) else find_dotenv(usecwd=True))

# Force HuggingFace offline BEFORE any transformers/sentence-transformers import,
# so cached models load without blocked network HEAD requests (corporate proxy
# causes SSL: CERTIFICATE_VERIFY_FAILED against huggingface.co).
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
# Force CPU-only device enumeration to prevent PyTorch from hanging on Windows
# while probing CUDA/GPU drivers at startup (no GPU on this machine).
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
# google-genai calls google.auth.default() (→ GCE metadata probe at 169.254.169.254)
# when GOOGLE_API_KEY is absent. That request hangs on a corporate network.
# We use Ollama locally so this value is never sent to Google.
os.environ.setdefault("GOOGLE_API_KEY", "local-ollama-no-google-api")

import uuid
import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai.types import Content, Part
from cora_rc_ai.backend_agentic.agents.compliance_agent import compliance_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Session Service ────────────────────────────────────────────────────────────
session_service = InMemorySessionService()

# ── ADK Runner ────────────────────────────────────────────────────────────────
runner = Runner(
    app_name="cora_agentic",
    agent=compliance_agent,
    session_service=session_service,
)

# ── FastAPI lifespan ──────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("CORA Agentic backend starting up...")
    yield
    logger.info("CORA Agentic backend shutting down.")

app = FastAPI(
    title="CORA Agentic AI Backend",
    description="Google ADK multi-agent compliance reasoning engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request / Response Schemas ─────────────────────────────────────────────────
class AgentChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    user_id: str = "default_user"

# ── Helpers ───────────────────────────────────────────────────────────────────
async def _ensure_session(user_id: str, session_id: str) -> None:
    existing = await session_service.get_session(
        app_name="cora_agentic",
        user_id=user_id,
        session_id=session_id,
    )
    if existing is None:
        await session_service.create_session(
            app_name="cora_agentic",
            user_id=user_id,
            session_id=session_id,
        )

# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "cora-agentic-backend"}

@app.post("/v1/agent/chat/stream")
async def agent_chat_stream(request: AgentChatRequest):
    """SSE streaming endpoint — streams ADK agent tokens as they are generated."""
    session_id = request.session_id or str(uuid.uuid4())
    await _ensure_session(request.user_id, session_id)

    user_message = Content(
        role="user",
        parts=[Part.from_text(text=request.message)],
    )

    async def event_generator():
        emitted_any_token = False
        emitted_done = False
        try:
            yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\n\n"

            async for event in runner.run_async(
                user_id=request.user_id,
                session_id=session_id,
                new_message=user_message,
            ):
                # Stream text chunks
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            emitted_any_token = True
                            payload = json.dumps(
                                {"type": "token", "content": part.text, "author": event.author}
                            )
                            yield f"data: {payload}\n\n"

                # Surface model/runtime errors explicitly when available.
                error_code = getattr(event, "error_code", None)
                error_message = getattr(event, "error_message", None)
                if error_code or error_message:
                    payload = json.dumps(
                        {
                            "type": "error",
                            "code": error_code,
                            "message": error_message or "Agent failed to generate a response.",
                            "author": event.author,
                        }
                    )
                    yield f"data: {payload}\n\n"

                # Detect tool call events
                if event.get_function_calls():
                    for fc in event.get_function_calls():
                        payload = json.dumps(
                            {"type": "tool_call", "tool": fc.name, "author": event.author}
                        )
                        yield f"data: {payload}\n\n"

                # Signal final response
                if event.is_final_response():
                    if not emitted_any_token:
                        # Avoid blank UI bubbles when a turn completes without text.
                        fallback = "I could not generate a final response from the model. Please try again."
                        yield f"data: {json.dumps({'type': 'token', 'content': fallback, 'author': event.author})}\n\n"
                    yield f"data: {json.dumps({'type': 'done', 'author': event.author})}\n\n"
                    emitted_done = True

            # if stream ends unexpectedly, still terminate client stream.
            if not emitted_done:
                if not emitted_any_token:
                    fallback = "I could not generate a final response from the model. Please try again."
                    yield f"data: {json.dumps({'type': 'token', 'content': fallback, 'author': 'compliance_agent'})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'author': 'compliance_agent'})}\n\n"

        except Exception as e:
            logger.error(f"Agent streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'author': 'compliance_agent'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@app.post("/v1/agent/chat")
async def agent_chat(request: AgentChatRequest):
    """Non-streaming endpoint — returns the complete response after full generation."""
    session_id = request.session_id or str(uuid.uuid4())
    await _ensure_session(request.user_id, session_id)

    user_message = Content(
        role="user",
        parts=[Part.from_text(text=request.message)],
    )

    full_response = ""
    try:
        async for event in runner.run_async(
            user_id=request.user_id,
            session_id=session_id,
            new_message=user_message,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                full_response = "".join(p.text for p in event.content.parts if p.text)
    except Exception as e:
        logger.error(f"Agent chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "session_id": session_id,
        "response": full_response,
        "author": "compliance_agent",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "cora_rc_ai.backend_agentic.main:app",
        host=os.getenv("AGENT_API_HOST", "0.0.0.0"),
        port=int(os.getenv("AGENT_API_PORT", 8080)),
        reload=False,
        workers=1,
    )
