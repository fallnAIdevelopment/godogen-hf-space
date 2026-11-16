---
title: Godogen Babylon Web Agent
emoji: 🎮
colorFrom: indigo
colorTo: purple
sdk: docker
pinned: false
license: mit
---

# Godogen · Babylon.js Web Game Agent

GPU-backed Hugging Face Space that uses **godogen** + **local godogen_assets** to turn a text description into a playable 3D web game.

## Features

- Gradio UI: enter a game description → live agent log → final playable URL
- Engine: **Babylon.js** (browser-playable 3D)
- LLM: NVIDIA Inference (`nvidia/nemotron-3-ultra-550b-a55b` free endpoint by default)
- Assets: local free generators from `godogen_assets` preferred over paid APIs
- Agent writes real files and runs shell commands (including local asset tools)

## Required Space secrets

| Secret | Value |
|--------|-------|
| `OPENAI_API_KEY` | Your NVIDIA API key (`nvapi-…`) |
| `OPENAI_API_BASE` | (optional) `https://integrate.api.nvidia.com/v1` |
| `NVIDIA_MODEL` | (optional) override model id |

## Hardware

Use a **GPU** Space (T4 or better). Local asset tools (Qwen-Image, TRELLIS.2, etc.) need VRAM; lighter tools still work on smaller GPUs.

## How it works

1. `publish.sh --engine babylon` creates a thin runtime repo.
2. Agent loop (NVIDIA model) inspects guides/skills and emits `### FILE` / `### RUN` blocks.
3. Blocks are applied (files written, commands executed, including local asset tools).
4. When a playable `index.html` appears, the Space surfaces a URL.

## Local development

```bash
export OPENAI_API_KEY=nvapi-...
docker build -t godogen-space .
docker run --gpus all -p 7860:7860 -e OPENAI_API_KEY -e OPENAI_API_BASE godogen-space
```

## Notes

- Full photorealistic asset pipelines are heavy; on smaller GPUs the agent may fall back to simpler materials while still producing a playable game.
- Rate limits on the free NVIDIA endpoint apply.
- This Space is for prototyping the godogen workflow, not production traffic.
