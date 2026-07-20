# AI Gateway

An OpenAI-compatible gateway for one or more llama.cpp-compatible servers. It routes `model: "auto"` requests through a configured LLM classifier (with keyword fallback), proxies normal and Server-Sent Event streaming completions, saves optional conversation sessions, exposes health/metrics, and provides opt-in allowlisted Git/Docker tooling.

## Run

1. Create and activate a Python 3.10+ virtual environment, then install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

2. Set the model endpoints (and optional `start_command` values) in `config.yaml`.

3. Set a strong API key and start the gateway:

   ```bash
   export AI_GATEWAY_API_KEY="replace-with-a-long-random-secret"
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```

Use `POST /v1/chat/completions`, just as with the OpenAI API. Specify `chat` or `coder`, or use `auto` to use the configured routes. Send an `X-Session-ID` header to persist recent conversation context. API documentation is at `/docs`.

Set `gateway.classifier_model` to a configured model name. That model receives the available route names and the latest conversation turns, and must return one route name. If it cannot be reached or replies with an invalid route, the gateway uses the configured keyword fallback.

## Idle VRAM release

Set `gateway.idle_timeout_seconds` to the desired idle period. The gateway checks once per minute and stops model servers that it started through a model `start_command`, which releases their VRAM. For safety, model servers you started yourself are not terminated by the gateway; configure their `start_command` if you want lifecycle management.

When the gateway needs to start a different managed model, it also stops its currently managed non-persistent model first. This keeps a single answer model resident in VRAM at a time. Mark a small CPU classifier as `persistent: true` (as in the sample configuration) so it stays available without evicting the answer model.

Run a single Uvicorn worker. Each worker owns its own lifecycle state and multiple workers would conflict over the same model ports and processes.

## Hosting safely

Keep every llama.cpp server bound to `127.0.0.1`; the gateway is the only service that needs network exposure. It requires the `AI_GATEWAY_API_KEY` environment variable by default. For access outside a trusted LAN, place the gateway behind a TLS reverse proxy and do not expose the model-server ports.

During graceful gateway shutdown, every model process started by the gateway is stopped and releases its VRAM. A `start_command` that exits immediately now fails fast with its exit code instead of waiting for the whole startup timeout.

## Start automatically with tmux

Create a private environment file for the required key, then restrict it to your account:

```bash
mkdir -p ~/.config/local-ai
printf 'export AI_GATEWAY_API_KEY="replace-with-a-long-random-secret"\n' > ~/.config/local-ai/gateway.env
chmod 600 ~/.config/local-ai/gateway.env
```

Add this line to `~/.bashrc` (change the path if you installed the project elsewhere):

```bash
source ~/router/ai-gateway/scripts/ensure-local-ai.sh
```

Each interactive Bash session then starts the gateway only if a tmux session called `local-ai` does not already exist. Inspect its live output with `tmux attach -t local-ai`, detach with `Ctrl-b d`, and read persistent output with `tail -f ~/router/ai-gateway/logs/gateway.log`.

The gateway never executes arbitrary user shell input. Tool execution is disabled by default and command names are allowlisted in `config.yaml`.
When enabled, `POST /tool/git` and `POST /tool/docker` accept a JSON body such as `{"command": "status"}`.
