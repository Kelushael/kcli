"""
File, system, and shell tools for GesherEl.
Workspace: ~/workspace. Logs: ~/.sovereign/tool_log.jsonl
"""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path.home() / "workspace"
LOG_PATH = Path.home() / ".sovereign" / "tool_log.jsonl"


def _log(tool: str, args: dict, result: Any) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "tool": tool,
        "args": args,
        "ok": result.get("ok", True) if isinstance(result, dict) else True,
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _resolve(path: str) -> Path:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = WORKSPACE / p
    return p


# ── File tools ──────────────────────────────────────────────────

def list_directory(path: str = "~") -> list[dict]:
    p = Path(path).expanduser() if path != "~" else Path.home()
    if not p.exists():
        return [{"error": f"{path} does not exist"}]
    items = []
    for child in sorted(p.iterdir()):
        items.append({
            "name": child.name,
            "type": "dir" if child.is_dir() else "file",
            "size": child.stat().st_size if child.is_file() else None,
        })
    _log("list_directory", {"path": path}, {"ok": True})
    return items


def read_file(path: str) -> str:
    p = _resolve(path)
    if not p.exists():
        return f"ERROR: {path} not found"
    try:
        return p.read_text(errors="replace")
    except Exception as e:
        return f"ERROR: {e}"


def write_file(path: str, content: str) -> str:
    p = _resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    _log("write_file", {"path": path}, {"ok": True})
    return f"Written {len(content)} bytes to {p}"


def edit_block(path: str, old: str, new: str) -> str:
    p = _resolve(path)
    if not p.exists():
        return f"ERROR: {path} not found"
    src = p.read_text(errors="replace")
    if old not in src:
        return f"ERROR: block not found in {path}"
    p.write_text(src.replace(old, new, 1))
    _log("edit_block", {"path": path}, {"ok": True})
    return f"Block replaced in {p}"


def search_text(needle: str, path: str = "~") -> list[dict]:
    p = Path(path).expanduser()
    results = []
    if p.is_file():
        files = [p]
    else:
        files = [f for f in p.rglob("*") if f.is_file()]
    for f in files:
        try:
            for i, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
                if needle in line:
                    results.append({"file": str(f), "line": i, "text": line.strip()})
        except Exception:
            pass
    _log("search_text", {"needle": needle, "path": path}, {"ok": True, "matches": len(results)})
    return results


def create_directory(path: str) -> str:
    p = _resolve(path)
    p.mkdir(parents=True, exist_ok=True)
    _log("create_directory", {"path": path}, {"ok": True})
    return f"Directory ready: {p}"


def delete_file(path: str) -> str:
    p = _resolve(path)
    if not p.exists():
        return f"ERROR: {path} not found"
    if p.is_dir():
        import shutil
        shutil.rmtree(p)
        kind = "directory"
    else:
        p.unlink()
        kind = "file"
    _log("delete_file", {"path": path}, {"ok": True})
    return f"Deleted {kind}: {p}"


# ── Shell ────────────────────────────────────────────────────────

def run_command(command: str, timeout: int = 60) -> dict:
    try:
        r = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=timeout, executable="/bin/bash"
        )
        result = {
            "ok": r.returncode == 0,
            "stdout": r.stdout.strip(),
            "stderr": r.stderr.strip(),
            "code": r.returncode,
        }
    except subprocess.TimeoutExpired:
        result = {"ok": False, "stdout": "", "stderr": "timed out", "code": -1}
    except Exception as e:
        result = {"ok": False, "stdout": "", "stderr": str(e), "code": -1}
    _log("run_command", {"command": command[:200]}, result)
    return result


# ── System ───────────────────────────────────────────────────────

def scan_environment() -> dict:
    def _v(cmd: str) -> str:
        r = run_command(cmd, timeout=10)
        return r["stdout"].split("\n")[0] if r["ok"] else "not found"

    return {
        "python":  _v("python3 --version"),
        "node":    _v("node --version"),
        "npm":     _v("npm --version"),
        "git":     _v("git --version"),
        "docker":  _v("docker --version"),
        "ffmpeg":  _v("ffmpeg -version | head -1"),
        "whisper": _v("whisper --help 2>&1 | head -1"),
        "ollama":  _v("ollama --version"),
        "disk":    _v("df -h / | tail -1 | awk '{print $4\" free of \"$2}'"),
        "mem":     _v("free -h | awk '/^Mem:/{print $7\" free of \"$2}'"),
    }


def install_package(package: str, manager: str = "pip") -> dict:
    managers = {
        "pip":  f"pip3 install --quiet {package}",
        "apt":  f"apt-get install -y {package}",
        "npm":  f"npm install -g {package}",
    }
    cmd = managers.get(manager, f"pip3 install --quiet {package}")
    return run_command(cmd, timeout=120)
