# AI Gateway

An OpenAI-compatible gateway for one or more llama.cpp-compatible servers. It routes `model: "auto"` requests through a configured LLM classifier (with keyword fallback), proxies normal and Server-Sent Event streaming completions, saves optional conversation sessions, exposes health/metrics, and provides opt-in allowlisted Git/Docker tooling.

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

Set `gateway.classifier_model` to a configured model name. That model receives the available route names and the latest conversation turns, and must return one route name. If it cannot be reached or replies with an invalid route, the gateway uses the configured keyword fallback.

## Idle VRAM release

Set `gateway.idle_timeout_seconds` to the desired idle period. The gateway checks once per minute and stops model servers that it started through a model `start_command`, which releases their VRAM. For safety, model servers you started yourself are not terminated by the gateway; configure their `start_command` if you want lifecycle management.

When the gateway needs to start a different managed model, it also stops its currently managed model first. This keeps a single automatically managed model resident in VRAM at a time.

The gateway never executes arbitrary user shell input. Tool execution is disabled by default and command names are allowlisted in `config.yaml`.
When enabled, `POST /tool/git` and `POST /tool/docker` accept a JSON body such as `{"command": "status"}`.
