"""Gradio UI for godogen on HF GPU Space – Babylon web game agent."""
from __future__ import annotations
import os, time
from pathlib import Path
import gradio as gr
from agent import (
    ASSETS_ROOT, GAMES_ROOT, MAX_STEPS, MODEL, NVIDIA_BASE,
    SYSTEM_TEMPLATE, apply_blocks, extract_blocks, get_client,
    publish_babylon_game, try_build_web,
)

_log_buffer: list[str] = []
_running = False

def log(msg: str) -> None:
    _log_buffer.append(msg)
    if len(_log_buffer) > 500:
        del _log_buffer[:150]
    print(msg, flush=True)

def get_log() -> str:
    return "\n".join(_log_buffer[-250:])

def run_development(game_description: str, progress=gr.Progress(track_tqdm=False)):
    global _running
    if not game_description or not game_description.strip():
        yield "Enter a game description first.", "", get_log()
        return
    if _running:
        yield "A job is already running.", "", get_log()
        return
    _running = True
    _log_buffer.clear()
    try:
        log("=== Godogen HF Space – Babylon.js web game ===")
        log(f"Model : {MODEL}")
        log(f"Base  : {NVIDIA_BASE}")
        log(f"Goal  : {game_description[:400]}")
        progress(0.05, desc="Publishing Babylon project…")
        log("\nPublishing fresh Babylon.js project via godogen…")
        game_dir = publish_babylon_game(slug="webgame")
        log(f"Published → {game_dir}")
        yield None, "", get_log()
        progress(0.12, desc="Agent starting…")
        client = get_client()
        system = SYSTEM_TEMPLATE.format(game_dir=game_dir, assets_dir=ASSETS_ROOT, user_goal=game_description)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": (
                "Start now. Inspect the published project and the asset-gen skill. "
                "Then build the Babylon.js game. Prefer local godogen_assets tools. "
                "Emit real ### FILE and ### RUN blocks."
            )},
        ]
        for step in range(1, MAX_STEPS + 1):
            progress(0.12 + 0.75 * (step / MAX_STEPS), desc=f"Agent step {step}/{MAX_STEPS}")
            log(f"\n===== AGENT STEP {step}/{MAX_STEPS} =====")
            try:
                resp = client.chat.completions.create(model=MODEL, messages=messages, temperature=0.2, max_tokens=4096)
                reply = resp.choices[0].message.content or ""
            except Exception as e:
                log(f"[LLM ERROR] {e}")
                time.sleep(4)
                yield None, "", get_log()
                continue
            preview = reply if len(reply) < 2800 else reply[:2800] + "\n…[truncated]"
            log(preview)
            messages.append({"role": "assistant", "content": reply})
            blocks = extract_blocks(reply)
            if blocks:
                apply_blocks(game_dir, blocks, log)
            else:
                log("(No FILE/RUN blocks this step)")
            yield None, "", get_log()
            lower = reply.lower()
            if any(p in lower for p in ("game is playable", "ready to play", "build succeeded", "i am done", "core loop is complete")):
                log("Agent indicated the game is ready.")
                break
            messages.append({"role": "user", "content": (
                f"Step {step} results applied. Continue toward a playable Babylon.js web game. "
                "When the core loop is playable, say so clearly."
            )})
        progress(0.92, desc="Looking for playable build…")
        rel_url = try_build_web(game_dir, log)
        space_host = os.environ.get("SPACE_HOST") or os.environ.get("SPACE_ID", "your-space.hf.space")
        if "hf.space" not in space_host and "/" in space_host:
            space_host = f"{space_host.replace('/', '-')}.hf.space"
        if rel_url:
            full = f"https://{space_host}{rel_url}"
            log(f"\n✅ Playable game URL: {full}")
            iframe_html = f'<iframe src="{rel_url}" width="100%" height="480" style="border:1px solid #444;border-radius:8px;"></iframe>'
            yield full, iframe_html, get_log()
        else:
            log("\n⚠️ No index.html found yet. Inspect /data/games/webgame or continue the agent.")
            yield "", "", get_log()
        progress(1.0, desc="Done")
        log("=== Job finished ===")
    except Exception as e:
        log(f"\n[FATAL] {type(e).__name__}: {e}")
        yield "", "", get_log()
    finally:
        _running = False

def clear_all():
    _log_buffer.clear()
    return "", "", ""

def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Godogen Babylon Web Agent", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# Godogen · Babylon.js Web Game Agent\nType a game description. Agent builds a 3D browser game using godogen + local assets. You get a playable URL.")
        description = gr.Textbox(label="Game description", placeholder="A small photorealistic first-person exploration game in a rainy neo-noir alley...", lines=5)
        with gr.Row():
            start_btn = gr.Button("Start development", variant="primary")
            clear_btn = gr.Button("Clear")
        game_url = gr.Textbox(label="Playable game URL", interactive=False)
        preview = gr.HTML(label="Preview")
        log_box = gr.Textbox(label="Live agent log", lines=26, max_lines=40, interactive=False, autoscroll=True)
        start_btn.click(fn=run_development, inputs=[description], outputs=[game_url, preview, log_box])
        clear_btn.click(fn=clear_all, outputs=[game_url, preview, log_box])
        gr.Markdown(f"**Model**: `{MODEL}` · **Engine**: Babylon.js · **Assets**: local godogen_assets preferred · Set secret `OPENAI_API_KEY` to your NVIDIA key.")
    return demo

if __name__ == "__main__":
    GAMES_ROOT.mkdir(parents=True, exist_ok=True)
    demo = build_ui()
    demo.queue().launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)), show_error=True)
