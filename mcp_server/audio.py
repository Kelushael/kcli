"""
Audio tools for GesherEl — FFmpeg and Whisper operations.
Clip directory: ~/workspace/clips/
"""

import shutil
import subprocess
from pathlib import Path
from typing import Union

CLIPS_DIR = Path.home() / "workspace" / "clips"


def _run(cmd: str, timeout: int = 120) -> dict:
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, executable="/bin/bash"
        )
        return {
            "ok": r.returncode == 0,
            "stdout": r.stdout.strip(),
            "stderr": r.stderr.strip(),
            "code": r.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": "timed out", "code": -1}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e), "code": -1}


def _resolve(path: str) -> Path:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = CLIPS_DIR / path
    return p


def trim_audio(path: str, end_ms: int, output: str = "") -> str:
    src = _resolve(path)
    if not output:
        output = str(src.parent / f"{src.stem}_trimmed{src.suffix}")
    end_sec = end_ms / 1000
    r = _run(f'ffmpeg -y -i "{src}" -t {end_sec} "{output}"')
    if not r["ok"]:
        return f"ERROR: {r['stderr'][:200]}"
    return output


def normalize_audio(paths: list[str], output: str) -> str:
    if not paths:
        return "ERROR: no input paths"
    inputs = " ".join(f'-i "{_resolve(p)}"' for p in paths)
    filter_complex = ";".join(f"[{i}:a]loudnorm[a{i}]" for i in range(len(paths)))
    mix = "".join(f"[a{i}]" for i in range(len(paths)))
    r = _run(f'ffmpeg -y {inputs} -filter_complex "{filter_complex};{mix}amix=inputs={len(paths)}[out]" -map "[out]" "{output}"')
    if not r["ok"]:
        return f"ERROR: {r['stderr'][:200]}"
    return output


def stitch_takes(take_paths: list[str], output: str) -> str:
    if not take_paths:
        return "ERROR: no takes provided"
    list_file = Path("/tmp/gesherel_concat.txt")
    lines = "\n".join(f"file '{_resolve(p)}'" for p in take_paths)
    list_file.write_text(lines)
    r = _run(f'ffmpeg -y -f concat -safe 0 -i "{list_file}" -c copy "{output}"')
    if not r["ok"]:
        return f"ERROR: {r['stderr'][:200]}"
    return output


def transcribe_audio(path: str, model: str = "base") -> str:
    src = _resolve(path)
    if not src.exists():
        return f"ERROR: {path} not found"
    r = _run(f'whisper "{src}" --model {model} --output_format txt --output_dir /tmp', timeout=300)
    if not r["ok"]:
        return f"ERROR: {r['stderr'][:200]}"
    txt = Path("/tmp") / (src.stem + ".txt")
    if txt.exists():
        return txt.read_text().strip()
    return r["stdout"] or "Transcription complete (output file not found)"


def check_services() -> dict:
    def _has(cmd: str) -> bool:
        return shutil.which(cmd) is not None

    def _running(svc: str) -> bool:
        r = _run(f"curl -s --max-time 2 http://localhost:11434/api/tags", timeout=5)
        return r["ok"] and "models" in r["stdout"]

    status = {
        "ffmpeg":  _has("ffmpeg"),
        "whisper": _has("whisper"),
        "ollama":  _running("ollama"),
    }
    return status
