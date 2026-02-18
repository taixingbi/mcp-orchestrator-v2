"""Application settings loaded from environment."""

import os
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()

# Lazy LLM singleton (import lazily to avoid loading langchain at config import)
_llm = None


class Settings:
    """Settings from env (and .env)."""

    # App
    mcp_name: str = os.getenv("MCP_NAME", "mcp-orchestrator")
    app_version: str = os.getenv("APP_VERSION", "0.1.0")

    # LangChain / LangSmith
    langchain_project: Optional[str] = os.getenv("LANGCHAIN_PROJECT")
    langchain_api_key: Optional[str] = os.getenv("LANGCHAIN_API_KEY")
    langsmith_api_key: Optional[str] = os.getenv("LANGSMITH_API_KEY")
    langchain_endpoint: Optional[str] = os.getenv("LANGCHAIN_ENDPOINT")
    langsmith_tracing: bool = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"

    # MCP tool URL (no trailing slash in env; code adds / when needed)
    mcp_tool_rag_url: Optional[str] = os.getenv("MCP_TOOL_RAG_URL")

    # OpenAI (used by orchestrator; often set by LangChain)
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Default timeouts for MCP tool calls (seconds)
    tools_timeout_s: float = float(os.getenv("TOOLS_TIMEOUT_S", "60"))
    invoke_timeout_s: float = float(os.getenv("INVOKE_TIMEOUT_S", "120"))

    @staticmethod
    def _server_dict(name: str, url: str) -> dict:
        """Build a single-server config for MultiServerMCPClient."""
        return {name: {"transport": "http", "url": url.rstrip("/") + "/"}} if url else {}

    @property
    def rag_server_config(self) -> dict:
        """RAG MCP server config from env; empty dict if not set."""
        url = (self.mcp_tool_rag_url or "").rstrip("/")
        return self._server_dict("tool_rag", url)


settings = Settings()


def get_llm():
    """Return a shared ChatOpenAI instance (lazy init)."""
    global _llm
    if _llm is None:
        from langchain_openai import ChatOpenAI
        _llm = ChatOpenAI(model=settings.openai_model, temperature=0)
    return _llm


def has_langsmith_credentials() -> bool:
    """True if we have an API key to call LangSmith (LANGCHAIN_API_KEY or LANGSMITH_API_KEY)."""
    return bool(settings.langchain_api_key or settings.langsmith_api_key)


def get_langsmith_tags(
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> List[str]:
    """Build tags for LangSmith traces (key:value format). Optionally include request_id and session_id."""
    tags = [
        f"mcp_name:{settings.mcp_name}",
        f"agent_model:{settings.openai_model}",
        f"agent_has_rag:{bool(settings.mcp_tool_rag_url)}",
    ]
    if settings.langchain_project:
        tags.append(f"langchain_project:{settings.langchain_project}")
    if settings.langsmith_tracing:
        tags.append("langsmith_tracing:true")
    if request_id:
        tags.append(f"request_id:{request_id}")
    if session_id:
        tags.append(f"session_id:{session_id}")
    return tags


