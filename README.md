# mcp-orchestrator-v2
# MCP Orchestrator

Runs the RAG MCP tool and exposes an `answer_question` MCP tool plus a streaming HTTP endpoint.

## Setup

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Environment (.env)

| Variable | Description |
|----------|-------------|
| `MCP_TOOL_RAG_URL` | RAG MCP server URL |
| `OPENAI_API_KEY` | Required for LLM |
| `OPENAI_MODEL` | Model name (default: `gpt-4o-mini`) |
| `REWRITE_QUERY` | `true` to rewrite questions before RAG |
| `TOOLS_TIMEOUT_S` | MCP tools timeout (default: 60) |
| `INVOKE_TIMEOUT_S` | Agent invoke timeout (default: 120) |

## Run

```bash
uvicorn main:app --reload --port 8000
```

### Docker
<!-- Build and run with .env; port 8000. -->
```bash
docker build -t mcp-server .
docker run -p 8000:8000 --env-file .env mcp-server
```

## Health

```bash
curl http://127.0.0.1:8000/health
```


## MCP tool (tools/call)
# MCP RAG tool (answer_question)
```bash
curl -s -X POST "http://localhost:8000/mcp/" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "answer_question",
      "arguments": {
        "question": "What is your taixing status? Do they require sponsorship?",
        "request_id": "12345678",
        "session_id": "123456"
      }
    }
  }'
```

```bash
curl -s -X POST http://localhost:8000/orchestrator/stream-answer \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "123456",
    "request_id": "12345678",
    "question": "what is taixing visa status?"
  }'
```

## Feedback

Submit feedback on an agent response. Use `agent_graph_run_id` from the answer SSE event of `/stream-answer` (or `request_id` from the first event) to attach feedback to the agent_graph run in LangSmith.

**Thumbs up (with agent_graph_run_id):**
```bash
curl -s -X POST http://localhost:8000/feedback \
  -H "Content-Type: application/json" \
  -d '{"agent_graph_run_id":"c111d890-55c2-40ec-ba23-84a18ffa91f1","rating":"thumbs_up"}'
```

**Thumbs down (with type and comment):**
```bash
curl -s -X POST http://localhost:8000/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "agent_graph_run_id": "019c5f54-0667-7531-9b48-62a65710fd2c",
    "rating": "thumbs_down",
    "feedback_type": "not_factual",
    "comment": "Only returned 3 titles"
  }'
```

`feedback_type` (optional): `not_relevant`, `biased`, `not_factual`, `incomplete_instructions`, `unsafe`, `style_tone`, `other`

## Fly.io

**Apps:** `mcp-orchestrator-v2-{dev|qa|prod}` · **URLs:** `https://mcp-orchestrator-v2-{env}.fly.dev`

CI deploys: `main` → prod, `qa` → qa, `feature/**` → dev.

### One-time setup
```bash
brew install flyctl
fly auth login
fly auth token   # → set as GitHub secret FLY_API_TOKEN for CI
```

### Create apps (once per env)
```bash
fly launch --name mcp-orchestrator-v2-dev
fly launch --name mcp-orchestrator-v2-qa
fly launch --name mcp-orchestrator-v2-prod
```

### Set secrets
Sync `.env` to an app:
```bash
fly secrets set OPENAI_API_KEY=xxx MCP_TOOL_RAG_URL=xxx ... --app mcp-orchestrator-v2-dev
```

### Deploy
```bash
fly deploy --app mcp-orchestrator-v2-dev
```
Pushes to `main`, `qa`, or `feature/**` auto-deploy via GitHub Actions when `FLY_API_TOKEN` is set.

### Fly health and tool (example)

**Health:**
```bash
curl https://mcp-orchestrator-v2-dev.fly.dev/health
```

## call orchestrator_stream_answer
```bash
curl -s -X POST https://mcp-orchestrator-v2-dev.fly.dev/orchestrator/stream-answer \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "123456",
    "request_id": "12345678",
    "question": "what is taixing visa status?"
  }'
```


**Thumbs up (with agent_graph_run_id):**
```bash
curl -s -X POST https://mcp-orchestrator-v2-dev.fly.dev/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "agent_graph_run_id":"lc_2038042c-2ed5-4444-afeb-3c2fac830ed2",
    "rating":"thumbs_up"
    }'
```

**Thumbs down (with type and comment):**
```bash
curl -s -X POST https://mcp-orchestrator-v2-dev.fly.dev/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "agent_graph_run_id": "lc_2038042c-2ed5-4444-afeb-3c2fac830ed2",
    "rating": "thumbs_down",
    "feedback_type": "not_factual",
    "comment": "not truth"
  }'
```