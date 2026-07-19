# Local AI Router

A self-hosted OpenAI-compatible AI gateway for routing requests between local llama.cpp model servers. It lets an OpenAI-compatible client such as Odysseus use one stable API endpoint while the gateway selects, starts, stops, and proxies the appropriate local model.

> This project was generated with **GPT 5.6 Terra**.

## Project intention

The project is designed for a local AI workstation that serves multiple specialised models without keeping every large model in VRAM.

- Present one OpenAI-compatible endpoint to clients.
- Use a lightweight, persistent classifier to select the best route for ambiguous requests.
- Start answer models only when needed and release their VRAM after an idle period.
- Preserve optional conversation context with local session files.
- Keep model servers private on loopback while exposing only the authenticated gateway.

## Architecture

```text
Odysseus or another OpenAI-compatible client
                  |
                  | POST /v1/chat/completions
                  v
       AI Gateway (FastAPI, port 8000)
                  |
        +---------+----------+
        |                    |
        v                    v
LLM intent classifier    Explicit model selection
Qwen2.5-3B-Instruct      (chat or coder)
CPU, persistent                 |
        |                       |
        +----------+------------+
                   v
          Model lifecycle manager
                   |
          +--------+--------+
          |                 |
          v                 v
   Chat llama-server   Coder llama-server
   GPU, on demand      GPU, on demand
```

The classifier chooses a configured route when the client sends `"model": "auto"` or omits the model. An explicit `"model": "chat"` or `"model": "coder"` bypasses routing.

## Key behavior

- The gateway serializes model-serving requests, so it never unloads a model while it is generating a response.
- The CPU classifier can remain loaded without consuming GPU VRAM.
- Only one non-persistent, gateway-managed answer model is kept in VRAM at a time.
- Gateway-owned llama.cpp processes are stopped after the configured idle timeout and during graceful shutdown.
- Normal and streaming OpenAI-compatible chat completions are supported.
- Sessions are stored locally under `ai-gateway/sessions/` when the caller includes `X-Session-ID`.

## Project layout

```text
router/
├── README.md                 # This project overview
└── ai-gateway/               # Gateway application
    ├── app.py                # FastAPI application entry point
    ├── config.yaml           # Models, routes, lifecycle, and security settings
    ├── api/                  # OpenAI, health, and tool endpoints
    ├── managers/             # Model lifecycle, sessions, routing
    ├── llm/                  # Classifier and upstream client
    ├── models/               # Model registry
    ├── tools/                # Opt-in allowlisted local tools
    └── sessions/             # Runtime conversation data (not committed)
```

## Security model

- Set `AI_GATEWAY_API_KEY` before starting the service.
- Bind llama.cpp servers to `127.0.0.1`.
- Keep `tools.enabled: false` unless local tooling is explicitly needed.
- Use a TLS reverse proxy before exposing the gateway outside a trusted LAN.
- Grant the runtime account read access to model files and write access only to the session directory.

## Running the gateway

Refer to [the gateway README](ai-gateway/README.md) for Linux environment setup, model configuration, API-key configuration, and launch commands.
