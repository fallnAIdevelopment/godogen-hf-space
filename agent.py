"""Godogen agent harness for HF GPU Space (NVIDIA Inference, local assets, Babylon)."""
from __future__ import annotations

import os, re, subprocess, time
from pathlib import Path
from typing import Callable, Optional
from openai import OpenAI

NVIDIA_BASE = os.environ.get("OPENAI_API_BASE", "https://integrate.api.nvidia.com/v1")
NVIDIA_KEY = os.environ.get("OPENAI_API_KEY", "")
MODEL = os.environ.get("NVIDIA_MODEL", "nvidia/nemotron-3-ultra-550b-a55b")
GODOGEN_ROOT = Path(os.environ.get("GODOGEN_ROOT", "/opt/godogen"))
ASSETS_ROOT = Path(os.environ.get("GODOGEN_ASSETS", "/opt/godogen_assets"))
GAMES_ROOT = Path(os.environ.get("GAMES_ROOT", "/data/games"))
MAX_STEPS = int(os.environ.get("MAX_AGENT_STEPS", "25"))
TIMEOUT_PER_CMD = int(os.environ.get("CMD_TIMEOUT", "180"))

def get_client() -> OpenAI:
    if not NVIDIA_KEY:
        raise RuntimeError("OPENAI_API_KEY (NVIDIA key) is not set")
    return OpenAI(base_url=NVIDIA_BASE, api_key=NVIDIA_KEY)

def run_cmd(cmd: str, cwd: Path | None = None, timeout: int = TIMEOUT_PER_CMD):
    try:
        proc = subprocess.run(cmd, shell=True, cwd=str(cwd) if cwd else None, capture_output=True, text=True, timeout=timeout,
            env={**os.environ, "PATH": f"{ASSETS_ROOT}/bin:/usr/local/bin:{os.environ.get('PATH','')}"})
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, out[-8000:]
    except subprocess.TimeoutExpired:
        return 124, f"[TIMEOUT after {timeout}s] {cmd}"
    except Exception as e:
        return 1, f"[ERROR] {e}"

def extract_blocks(text: str):
    blocks = []
    for m in re.finditer(r"###\s*FILE:\s*([^\n]+)\n```(?:\w*\n)?(.*?)```", text, re.DOTALL | re.IGNORECASE):
        blocks.append(("file", m.group(1).strip(), m.group(2).strip()))
    for m in re.finditer(r"###\s*RUN:\s*(.+?)(?=\n###|\n*$)", text, re.DOTALL | re.IGNORECASE):
        cmd = m.group(1).strip().split("\n")[0].strip()
        if cmd:
            blocks.append(("run", cmd, ""))
    return blocks

def apply_blocks(game_dir: Path, blocks, log: Callable[[str], None]):
    for kind, target, content in blocks:
        if kind == "file":
            full = game_dir / target.lstrip("/")
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content + "\n")
            log(f"Wrote file: {full.relative_to(game_dir)}")
        elif kind == "run":
            log(f"$ {target}")
            code, out = run_cmd(target, cwd=game_dir)
            log(f"[exit {code}]\n{out[-2000:]}")

def publish_babylon_game(slug: str = "webgame") -> Path:
    game_dir = GAMES_ROOT / slug
    if game_dir.exists():
        import shutil
        shutil.rmtree(game_dir, ignore_errors=True)
    marker = GODOGEN_ROOT / ".godogen_assets"
    marker.write_text(str(ASSETS_ROOT.resolve()) + "\n")
    code, out = run_cmd(f"./publish.sh --engine babylon --agent claude --out {game_dir} --force", cwd=GODOGEN_ROOT, timeout=120)
    if code != 0:
        raise RuntimeError(f"publish.sh failed:\n{out}")
    return game_dir

SYSTEM_TEMPLATE = """You are an autonomous game development agent using godogen.
You are building a Babylon.js 3D web game that must be playable in the browser.

Project directory: {game_dir}
Local free asset tools (PREFERRED): {assets_dir}/bin/
  qwen-image, gen3d, mia-rig, add-moves, gen-moves, grip-prop, stable-audio, qwen-tts, lipsync, asset-blender

ASSET RULES: Prefer LOCAL free tools. Only use paid APIs if a local tool is missing/fails. Always pass -o into the project.

GAME GOAL:
{user_goal}

ENGINE: Babylon.js web. Need scene, camera, lights, player control, basic collision, playable loop. Photorealistic as far as assets allow; keep scope small.

OUTPUT FORMAT (strict):
### FILE: relative/path.ext
```
content
```
### RUN: shell command
Work in small steps. Environment will execute FILE/RUN blocks and return results.
"""

def try_build_web(game_dir: Path, log: Callable[[str], None]) -> Optional[str]:
    pkg = game_dir / "package.json"
    if pkg.exists():
        log("Found package.json – npm install + build…")
        code, out = run_cmd("npm install", cwd=game_dir, timeout=300)
        log(out[-1500:])
        for script in ("build", "build:web", "dist"):
            code, out = run_cmd(f"npm run {script}", cwd=game_dir, timeout=180)
            if code == 0:
                log(f"npm run {script} succeeded")
                break
    for candidate in [game_dir/"index.html", game_dir/"dist"/"index.html", game_dir/"public"/"index.html", game_dir/"build"/"index.html"]:
        if candidate.exists():
            rel = candidate.relative_to(GAMES_ROOT)
            log(f"Playable entry found: {rel}")
            return f"/games/{rel.parent if candidate.name == 'index.html' else rel}"
    log("No index.html found yet.")
    return None
