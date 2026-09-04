# Tieny

Tieny is a lightweight local LLM server made for quick setup and simple local model hosting.

Add a model, start Tieny, and use it through the Web UI, CLI, or API.

## Install

```bash
pip install -e .
tieny install
```

Check Tieny is installed:

```bash
tieny --version
```

Need help with a command?

```bash
tieny --help
tieny start --help
tieny config --help
```

## Quick start

Add a model:

```bash
tieny add "path/to/model.gguf"
```

View registered models:

```bash
tieny list
```

Start Tieny:

```bash
tieny start
```

By default, Tieny starts the local server and opens the Web UI.

Default address:

```text
http://127.0.0.1:8765
```

Load a model:

```bash
tieny load MODEL
```

Unload it:

```bash
tieny unload
```

Models can be referenced by ID or name.

## Web UI

Running:

```bash
tieny start
```

starts the server and automatically opens the Web UI.

If you only want the API/server:

```bash
tieny start --no-ui
```

You can make no-UI startup automatic:

```bash
tieny config no-ui --auto true
```

Turn it back off:

```bash
tieny config no-ui --auto false
```

## Preload

Preload your configured or last-used model:

```bash
tieny start --preload
```

Preload a specific model:

```bash
tieny start --preload MODEL
```

Set a default preload model:

```bash
tieny config preload --set MODEL
```

Reset back to using the last successfully loaded model:

```bash
tieny config preload --reset
```

Automatically preload whenever Tieny starts:

```bash
tieny config preload --auto true
```

Disable it:

```bash
tieny config preload --auto false
```

View preload settings:

```bash
tieny config preload
```

## Useful commands

```bash
tieny add PATH
tieny list
tieny load MODEL
tieny unload
tieny remove MODEL
tieny name MODEL NEW_NAME
tieny start
```

For everything else:

```bash
tieny --help
```

## API

Tieny exposes a local FastAPI server.

Main endpoints:

```text
POST /chat
POST /v1/chat/completions
GET  /models
POST /models/load
POST /models/add
```

The OpenAI-compatible endpoint is:

```text
POST /v1/chat/completions
```

## What's new in v0.3.0

### Preload

Tieny can now load a model automatically when the server starts.

```bash
tieny start --preload
tieny start --preload MODEL
```

You can configure the default preload model and enable automatic preload:

```bash
tieny config preload --set MODEL
tieny config preload --auto true
```

If no preload model is configured, Tieny falls back to the last successfully loaded model.

### Config system

v0.3.0 introduces the new config command:

```bash
tieny config
```

Current config areas:

```text
preload
no-ui
```

More settings will be added here in future updates.

### No-UI startup

Start without automatically opening the Web UI:

```bash
tieny start --no-ui
```

Or make it automatic:

```bash
tieny config no-ui --auto true
```

### Persistent state

Tieny now remembers the last successfully loaded model, allowing preload to work without manually selecting the same model every time.

## Testing

Install test dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run tests:

```bash
python -m pytest -v
```


