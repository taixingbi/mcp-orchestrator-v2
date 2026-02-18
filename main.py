# main.py — MCP HTTP server exposing RAG tools
import asyncio
import contextlib
import json
import logging
import sys
from pathlib import Path
from typing import AsyncIterator, Optional

# Ensure project root is on sys.path (fixes ModuleNotFoundError when running via uvicorn --reload)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from config import has_langsmith_credentials, settings
from langsmith_feedback import FEEDBACK_TYPES, FeedbackBody, submit_langsmith_feedback
from mcp_server import mcp, mcp_app
from orchestrator import stream_answer_query

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


def _sse_stream_answer_gen(
    question: str,
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> AsyncIterator[str]:
    """Async generator for POST stream-answer. Yields SSE events from stream_answer_query."""
    async def _gen():
        async for chunk in stream_answer_query(
            question, session_id=session_id, request_id=request_id
        ):
            yield f"data: {json.dumps(chunk)}\n\n"
    return _gen()


@contextlib.asynccontextmanager
async def _lifespan(_app: FastAPI):
    async with mcp.session_manager.run():
        yield


app = FastAPI(
    title=settings.mcp_name,
    version=settings.app_version or "0.1.0",
    lifespan=_lifespan,
)


class StreamAnswerBody(BaseModel):
    question: str
    session_id: Optional[str] = Field(None, description="Optional session id for LangSmith tags")
    request_id: Optional[str] = Field(None, description="Optional request id; if provided, used as stream request_id")


@app.post("/orchestrator/stream-answer")
async def orchestrator_stream_answer_(body: StreamAnswerBody):
    """Stream the agent's answer as Server-Sent Events. Body: {"question": "..."}.
    Events: request_id, state, rewrite, route, answer, error."""
    return StreamingResponse(
        _sse_stream_answer_gen(
            body.question, session_id=body.session_id, request_id=body.request_id
        ),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@app.post("/feedback")
async def submit_feedback(body: FeedbackBody):
    """Submit feedback on an agent response (thumbs up/down, type, optional comment)."""
    if body.feedback_type and body.feedback_type not in FEEDBACK_TYPES:
        return {"status": "error", "message": f"feedback_type must be one of: {', '.join(sorted(FEEDBACK_TYPES))}"}
    agent_graph_run_id = body.agent_graph_run_id or body.request_id
    logging.info(
        "feedback: rating=%s type=%s run_id=%s question=%s comment=%s",
        body.rating,
        body.feedback_type,
        agent_graph_run_id or None,
        (body.question or "")[:50] or None,
        (body.comment or "")[:50] or None,
    )
    if agent_graph_run_id and has_langsmith_credentials():
        await asyncio.to_thread(
            submit_langsmith_feedback,
            agent_graph_run_id=agent_graph_run_id,
            rating=body.rating,
            feedback_type=body.feedback_type,
            comment=body.comment,
        )
    return {"status": "ok", "message": "Feedback received"}


@app.get("/health")
def health() -> dict:
    """Return app and LangSmith config for health checks."""
    return {
        "status": "ok",
        "app_version": settings.app_version,
        "mcp_name": settings.mcp_name,
        "langchain_project": settings.langchain_project,
        "langsmith_tracing": settings.langsmith_tracing,
        "langchain_endpoint": settings.langchain_endpoint,
    }

app.mount("/mcp", mcp_app)