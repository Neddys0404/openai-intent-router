# AI Gateway

An OpenAI-compatible gateway for one or more llama.cpp-compatible servers. It routes `model: "auto"` requests by keyword, proxies normal and Server-Sent Event streaming completions, saves optional conversation sessions, exposes health/metrics, and provides opt-in allowlisted Git/Docker tooling.

## Run

1. Create and activate a virtual environment, then install dependencies:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Set the model endpoints (and optional `start_command` values) in `config.yaml`.

3. Start the gateway:

   ```powershell
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```

Use `POST /v1/chat/completions`, just as with the OpenAI API. Specify `chat` or `coder`, or use `auto` to use the configured routes. Send an `X-Session-ID` header to persist recent conversation context. API documentation is at `/docs`.

The gateway never executes arbitrary user shell input. Tool execution is disabled by default and command names are allowlisted in `config.yaml`.
When enabled, `POST /tool/git` and `POST /tool/docker` accept a JSON body such as `{"command": "status"}`.
