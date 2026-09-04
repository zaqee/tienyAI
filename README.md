# Tieny

A simple local LLM server built for easy and quick use.

Tieny lets you run local **GGUF models** through a CLI, Web UI, Python, or an OpenAI-compatible API.

> Current version: **v0.2.1**

## Features

*  Run local GGUF models with llama.cpp
*  Simple Web UI
*  CLI model management
*  OpenAI-compatible API
*  Usable as a Python package
*  Add, load, unload, rename, switch and remove models
*  Models stay in their original location — no duplicate files
*  Built-in Developer Mode and logging

## Install

Requires **Python 3.10+**.

```bash
git clone https://github.com/zaqee/local-llm.git
cd local-llm

python -m venv .venv
pip install -e .

tieny install
```

## Quick Start

Add a GGUF model:

```bash
tieny add "/path/to/model.gguf"
```

See your models:

```bash
tieny list
```

Start Tieny:

```bash
tieny start
```

The Web UI will open automatically.

Then, from another terminal:

```bash
tieny load <model-name>
```

That's it. You're running a local LLM. 🎉

## API

Tieny includes a local API, including an OpenAI-compatible endpoint:

```text
POST /v1/chat/completions
```

Default server:

```text
http://127.0.0.1:8765
```

## Help

```bash
tieny --help
```

```bash
tieny --version
```

## Current Support

**v0.2.1**

* LLM: GGUF
* Runtime: llama.cpp
* One active model at a time

Tieny is still early in development. More runtimes and model types will come in future releases.
