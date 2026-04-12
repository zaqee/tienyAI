# local-llm

A local LLM server prototype. Meant for easy and quick use

## What it does

- `local-llm start` opens a terminal flow
- You paste either:
  - a local model path, or
  - a direct download URL
- It saves the model into a local registry so you do not need to enter it again
- It starts a FastAPI server and opens the web UI in your browser
- You can manage models via:
  - CLI (on first run)
  - Web UI (add, load, switch models)

## Features:
- view installed models
- load/switch models
- adjust runtime settings
- add models via:
  - file upload (.gguf)
  - direct URL

## API

- `POST /chat`
- `POST /v1/chat/completions`
- `GET /models`
- `POST /models/load`
- `POST /models/add`
---
# Setup
## Install

```
pip install -e .
```
## Start
```
local-llm start
```

## Help
```
local-llm --help
```

## Web UI

Accessible at:
```
home -> http://127.0.0.1:8000
settings -> -> http://127.0.0.1:8000/web/settings
```

---

# Notes

Models are stored in:
```
~/.local-llm/models/
```
Registry data:
```
~/.local-llm/registry.toml
```
Settings:
```
~/.local-llm/config.toml
```