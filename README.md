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
| `MODEL_TOKEN_ENCRYPTION_KEY` | _(required to save tokens)_ | Fernet key for encrypting model tokens in SQLite |
| `LLM_BASE_URL` | `http://127.0.0.1:11434/v1` | Initial endpoint until configured in the UI |
| `LLM_API_KEY` | `not-needed` | Optional seed token (encrypted on first boot if key is set) |
| `LLM_MODEL` | `llama3.2` | Initial model id until configured in the UI |
| `LLM_MAX_TOKENS` | `4096` | Max tokens per completion |
| `STATE_DB_PATH` | `data/state.db` | SQLite file path (project NFS on CML) |

Generate an encryption key:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Model settings (persisted in SQLite)

Configure via **Model** in the sidebar or `PUT /api/v1/model-settings`:

- **model_endpoint_url** — OpenAI-compatible base URL
- **model_id** — model name for chat completions
- **model_token** — write-only; stored **encrypted**; API responses expose **`model_token_masked`** (`••••••••••••`) only, never plaintext

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
- `GET/PUT /api/v1/model-settings` — persisted endpoint, model id, masked token indicator
- `GET/POST /api/v1/conversations` — list / create chats
- `GET /api/v1/conversations/{id}/messages` — history
- `POST /api/v1/conversations/{id}/chat` — **SSE** stream (`data: {"type":"token","content":"..."}` … `{"type":"done","message":{...}}`)

Multimodal requests include `images: [{ "mime_type": "image/png", "data": "<base64>" }]`.

## Multimodal & streaming notes

- **Streaming:** The backend forwards token deltas from the upstream OpenAI-compatible stream to the browser via Server-Sent Events.
- **Vision:** Attach images in the UI; the backend sends OpenAI-style `image_url` parts (data URLs). Use a model that supports vision on your inference server (e.g. `llava`, `llama3.2-vision` on Ollama).
