# Local LLM Chat (Cloudera AI Workbench Application)

React chat UI with a **FastAPI** backend, **SQLite** conversation store, and an **OpenAI-compatible** local LLM (Ollama, vLLM, llama.cpp server, etc.). Supports **streaming** responses and **multimodal** (image) messages for vision models.

## Architecture

- **Frontend:** React (Vite) — served from `frontend/dist` by FastAPI on the same port
- **API:** `/api/v1/*` — conversations, messages, streaming chat (SSE)
- **State:** SQLite at `data/state.db` (override with `STATE_DB_PATH`)
- **LLM:** Configured via environment variables; uses the OpenAI Chat Completions API with `stream=True`

## Cloudera AI Workbench ports

Bind the server to **`127.0.0.1`** and the port provided by the platform:

| Variable | Use |
|----------|-----|
| `CDSW_APP_PORT` | Primary application URL (`https://{subdomain}.{domain}`) |
| `CDSW_READONLY_PORT` | Read-only URL (`https://read-only-{subdomain}.{domain}`) |

Set **`CDSW_APP_POLLING_ENDPOINT=/healthcheck`** when creating the Application.

**Script:** `entry.py`

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_BASE_URL` | `http://127.0.0.1:11434/v1` | OpenAI-compatible API base (Ollama default) |
| `LLM_API_KEY` | `not-needed` | API key if your server requires one |
| `LLM_MODEL` | `llama3.2` | Model name passed to chat completions |
| `LLM_MAX_TOKENS` | `4096` | Max tokens per completion |
| `STATE_DB_PATH` | `data/state.db` | SQLite file path (project NFS on CML) |

Point `LLM_BASE_URL` at any OpenAI-compatible endpoint reachable from the application engine (same host, sidecar, or cluster service).

## Local development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Terminal 1 — API
CDSW_APP_PORT=8090 LLM_BASE_URL=http://127.0.0.1:11434/v1 LLM_MODEL=llama3.2 python3 entry.py

# Terminal 2 — UI with hot reload
cd frontend && npm ci && npm run dev
```

Open http://localhost:5173 (Vite proxies `/api` to port 8090).

## Production build (CML deploy)

```bash
pip3 install -r requirements.txt
cd frontend && npm ci && npm run build
CDSW_APP_PORT=8090 python3 entry.py
```

Open http://127.0.0.1:8090 for the combined UI + API.

## Deploy on Cloudera AI Workbench

1. Import this Git repository as a project.
2. In a **Python 3** session: `pip3 install -r requirements.txt`.
3. Build the UI (requires Node in the session or build elsewhere and sync `frontend/dist`):
   `cd frontend && npm ci && npm run build`
4. **Applications → New Application**
   - **Script:** `entry.py`
   - **Subdomain:** your choice (DNS-safe)
   - **Environment:** `CDSW_APP_POLLING_ENDPOINT=/healthcheck`, plus `LLM_*` as needed
5. When status is **Running**, open the application URL.

## API overview

- `GET /healthcheck` — platform health
- `GET /api/v1/config` — public LLM settings
- `GET/POST /api/v1/conversations` — list / create chats
- `GET /api/v1/conversations/{id}/messages` — history
- `POST /api/v1/conversations/{id}/chat` — **SSE** stream (`data: {"type":"token","content":"..."}` … `{"type":"done","message":{...}}`)

Multimodal requests include `images: [{ "mime_type": "image/png", "data": "<base64>" }]`.

## Multimodal & streaming notes

- **Streaming:** The backend forwards token deltas from the upstream OpenAI-compatible stream to the browser via Server-Sent Events.
- **Vision:** Attach images in the UI; the backend sends OpenAI-style `image_url` parts (data URLs). Use a model that supports vision on your inference server (e.g. `llava`, `llama3.2-vision` on Ollama).
