#!/usr/bin/env python3
"""
sovereign.py — Self-aware CLI agent. Built by someone who figured it out.
"""

import os
import sys
import json
import subprocess
import shutil
import platform
import textwrap
import readline  # noqa: F401 — gives us arrow keys in input()
from pathlib import Path
from datetime import datetime
from typing import Any

# ──────────────────────────────────────────────────────────────
# IDENTITY
# ──────────────────────────────────────────────────────────────
VERSION = "1.0.0"
AGENT_NAME = "sovereign"
HOME = Path.home()
SCRIPTS_DIR = HOME / "scripts"
WORKSPACE = HOME / "workspace"
DOWNLOADS = HOME / "downloads"
PROJECTS = HOME / "projects"
BIN = HOME / ".local" / "bin"
LOG_PATH = HOME / ".sovereign_log.jsonl"

BANNER = r"""
  ███████╗ ██████╗ ██╗   ██╗███████╗██████╗ ███████╗██╗ ██████╗ ███╗   ██╗
  ██╔════╝██╔═══██╗██║   ██║██╔════╝██╔══██╗██╔════╝██║██╔════╝ ████╗  ██║
  ███████╗██║   ██║██║   ██║█████╗  ██████╔╝█████╗  ██║██║  ███╗██╔██╗ ██║
  ╚════██║██║   ██║╚██╗ ██╔╝██╔══╝  ██╔══██╗██╔══╝  ██║██║   ██║██║╚██╗██║
  ███████║╚██████╔╝ ╚████╔╝ ███████╗██║  ██║███████╗██║╚██████╔╝██║ ╚████║
  ╚══════╝ ╚═════╝   ╚═══╝  ╚══════╝╚═╝  ╚═╝╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝
"""


# ──────────────────────────────────────────────────────────────
# COLORS  (256-color, degrades gracefully)
# ──────────────────────────────────────────────────────────────
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    CYAN   = "\033[96m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    BLUE   = "\033[94m"
    PURPLE = "\033[95m"
    GRAY   = "\033[90m"

    @staticmethod
    def ok(s):    return f"{C.GREEN}{s}{C.RESET}"
    @staticmethod
    def warn(s):  return f"{C.YELLOW}{s}{C.RESET}"
    @staticmethod
    def err(s):   return f"{C.RED}{s}{C.RESET}"
    @staticmethod
    def hi(s):    return f"{C.CYAN}{C.BOLD}{s}{C.RESET}"
    @staticmethod
    def dim(s):   return f"{C.GRAY}{s}{C.RESET}"
    @staticmethod
    def roast(s): return f"{C.PURPLE}{C.BOLD}{s}{C.RESET}"


def print_banner():
    print(C.CYAN + BANNER + C.RESET)
    print(C.DIM + f"  v{VERSION}  ·  {platform.node()}  ·  {platform.system()} {platform.release()}" + C.RESET)
    print()


# ──────────────────────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────────────────────
def log(event: str, data: Any = None):
    entry = {"ts": datetime.utcnow().isoformat(), "event": event, "data": data}
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ──────────────────────────────────────────────────────────────
# SHELL EXECUTION
# ──────────────────────────────────────────────────────────────
def run(cmd: str, capture: bool = True, timeout: int = 60) -> dict:
    """Run a shell command. Returns {ok, stdout, stderr, code}."""
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=capture, text=True,
            timeout=timeout, executable="/bin/bash"
        )
        result = {"ok": r.returncode == 0, "stdout": r.stdout.strip(),
                  "stderr": r.stderr.strip(), "code": r.returncode}
    except subprocess.TimeoutExpired:
        result = {"ok": False, "stdout": "", "stderr": "timed out", "code": -1}
    except Exception as e:
        result = {"ok": False, "stdout": "", "stderr": str(e), "code": -1}
    log("run", {"cmd": cmd[:200], "ok": result["ok"]})
    return result


# ──────────────────────────────────────────────────────────────
# ENVIRONMENT INSPECTION
# ──────────────────────────────────────────────────────────────
def inspect_env() -> dict:
    """Return a snapshot of the current environment."""
    checks = {
        "python":  run("python3 --version"),
        "pip":     run("pip3 --version"),
        "node":    run("node --version"),
        "npm":     run("npm --version"),
        "git":     run("git --version"),
        "curl":    run("curl --version | head -1"),
        "wget":    run("wget --version | head -1"),
        "vim":     run("vim --version | head -1"),
        "docker":  run("docker --version"),
    }
    disk  = run("df -h / | tail -1 | awk '{print $4\" free of \"$2}'")
    mem   = run("free -h | awk '/^Mem:/{print $7\" free of \"$2}'")
    uptime = run("uptime -p")
    user  = run("whoami")
    arch  = platform.machine()
    pyver = sys.version.split()[0]

    env = {
        "user":   user["stdout"],
        "arch":   arch,
        "python": pyver,
        "disk":   disk["stdout"],
        "mem":    mem["stdout"],
        "uptime": uptime["stdout"],
        "tools":  {k: v["stdout"].split("\n")[0] if v["ok"] else "MISSING"
                   for k, v in checks.items()},
    }
    log("inspect_env", env)
    return env


def print_env():
    print(C.hi("  Environment scan..."))
    env = inspect_env()
    print(f"\n  {C.BOLD}System{C.RESET}")
    print(C.dim(f"  ├─ user   {env['user']}"))
    print(C.dim(f"  ├─ arch   {env['arch']}"))
    print(C.dim(f"  ├─ python {env['python']}"))
    print(C.dim(f"  ├─ disk   {env['disk']}"))
    print(C.dim(f"  ├─ mem    {env['mem']}"))
    print(C.dim(f"  └─ uptime {env['uptime']}"))
    print(f"\n  {C.BOLD}Tools{C.RESET}")
    for tool, ver in env["tools"].items():
        icon = "✓" if ver != "MISSING" else "✗"
        col  = C.ok if ver != "MISSING" else C.err
        print(f"  {col(icon)} {tool:<10}{C.dim(ver[:60])}")
    print()
    return env


# ──────────────────────────────────────────────────────────────
# ARCHITECTURE ROAST ENGINE
# ──────────────────────────────────────────────────────────────
def _find_server_py() -> Path | None:
    """Locate the kcli server.py wherever it lives."""
    candidates = [
        HOME / "kcli" / "backend" / "server.py",
        Path("/home/user/kcli/backend/server.py"),
        Path("/app/backend/server.py"),
    ]
    for c in candidates:
        if c.exists():
            return c
    # last resort: walk upward from cwd
    for p in Path.cwd().parents:
        candidate = p / "backend" / "server.py"
        if candidate.exists():
            return candidate
    return None


ROASTS = [
    ("MongoDB for a chat log? Bold. You love paying for Atlas.",
     lambda: (s := _find_server_py()) and "mongo" in s.read_text().lower()),
    ("run_command() with a whitelist of 'echo, cat, ls'? That's not security, that's decoration.",
     lambda: (s := _find_server_py()) and "safe_prefixes" in s.read_text()),
    ("CORS origins set to '*'. The whole internet is your backend client.",
     lambda: (s := _find_server_py()) and "CORS_ORIGINS', '*')" in s.read_text()),
    ("OPENROUTER_API_KEY fallback is an empty string. Silently broken by default. Very enterprise.",
     lambda: (s := _find_server_py()) and "OPENROUTER_API_KEY', '')" in s.read_text()),
    ("Hardcoded DB_NAME via env with no default. First run crashes. Zero-day by design.",
     lambda: (s := _find_server_py()) and "DB_NAME']" in s.read_text()),
    ("app.on_event('shutdown') is deprecated in FastAPI. You're coding against the tide.",
     lambda: (s := _find_server_py()) and "on_event" in s.read_text()),
]

def roast_architecture() -> list[str]:
    """Find architectural issues and roast them."""
    findings = []
    for message, check in ROASTS:
        try:
            if check():
                findings.append(message)
        except Exception:
            pass
    return findings


def print_roast():
    print(C.hi("  Architectural review..."))
    issues = roast_architecture()
    if not issues:
        print(C.ok("  Architecture looks clean. Suspicious."))
        return []
    print(f"\n  Found {C.warn(str(len(issues)))} architectural... choices:\n")
    for i, issue in enumerate(issues, 1):
        print(C.roast(f"  [{i}] {issue}"))
    print()
    return issues


# ──────────────────────────────────────────────────────────────
# SELF-HEAL: autonomous fixes
# ──────────────────────────────────────────────────────────────
def fix_cors():
    """Tighten CORS from '*' to localhost origins."""
    p = _find_server_py()
    if not p:
        return False
    src = p.read_text()
    if "CORS_ORIGINS', '*')" not in src:
        return False
    fixed = src.replace(
        "CORS_ORIGINS', '*').split(',')",
        "CORS_ORIGINS', 'http://localhost:3000,http://localhost:8080').split(',')"
    )
    p.write_text(fixed)
    return True


def fix_api_key_check():
    """Add a startup warning when API key is missing."""
    p = _find_server_py()
    if not p:
        return False
    src = p.read_text()
    sentinel = "# sovereign: api-key-check"
    if sentinel in src:
        return False
    injection = f"""
{sentinel}
if not OPENROUTER_API_KEY:
    import warnings
    warnings.warn("OPENROUTER_API_KEY is not set. Chat will return errors.", stacklevel=1)
"""
    # Insert after the key is read
    src = src.replace(
        "OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')",
        "OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')" + injection
    )
    p.write_text(src)
    return True


FIXES = [
    ("Tightening CORS origins (localhost only)",         fix_cors),
    ("Adding startup warning for missing API key",       fix_api_key_check),
]


def auto_fix(dry_run: bool = False) -> list[str]:
    """Run all available fixes. Returns list of applied fix descriptions."""
    applied = []
    for description, fn in FIXES:
        try:
            if dry_run:
                applied.append(f"[dry-run] {description}")
            else:
                if fn():
                    applied.append(description)
                    log("auto_fix", {"fix": description})
        except Exception as e:
            log("auto_fix_error", {"fix": description, "error": str(e)})
    return applied


def print_auto_fix(dry_run: bool = False):
    verb = "Simulating" if dry_run else "Applying"
    print(C.hi(f"  {verb} autonomous fixes..."))
    applied = auto_fix(dry_run=dry_run)
    if not applied:
        print(C.dim("  Nothing to fix right now."))
    else:
        for fix in applied:
            print(C.ok(f"  ✓ {fix}"))
    print()
    return applied


# ──────────────────────────────────────────────────────────────
# PACKAGE INSTALLER
# ──────────────────────────────────────────────────────────────
def install_package(pkg: str, manager: str = "apt") -> bool:
    """Install a system or Python package."""
    if manager == "apt":
        r = run(f"sudo apt-get install -y {pkg}", capture=False, timeout=120)
    elif manager == "pip":
        r = run(f"pip3 install --quiet {pkg}", timeout=120)
    elif manager == "npm":
        r = run(f"npm install -g {pkg}", timeout=120)
    else:
        print(C.err(f"  Unknown manager: {manager}"))
        return False
    return r["ok"]


# ──────────────────────────────────────────────────────────────
# FILE OPERATIONS
# ──────────────────────────────────────────────────────────────
def create_file(path: str, content: str = "") -> bool:
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    log("create_file", {"path": str(p)})
    return True


def edit_file(path: str, old: str, new: str) -> bool:
    p = Path(path).expanduser()
    if not p.exists():
        return False
    src = p.read_text()
    if old not in src:
        return False
    p.write_text(src.replace(old, new, 1))
    log("edit_file", {"path": str(p)})
    return True


def run_script(path: str) -> dict:
    return run(f"python3 {path}", capture=True, timeout=60)


# ──────────────────────────────────────────────────────────────
# CONVERSATIONAL CHAT  (no API needed — local reasoning)
# ──────────────────────────────────────────────────────────────
INTENTS = [
    (["env", "environment", "system", "scan"],     "env"),
    (["roast", "review", "architecture", "janky"], "roast"),
    (["fix", "heal", "repair", "auto"],            "fix"),
    (["install"],                                   "install"),
    (["run", "exec", "bash", "shell", "cmd"],      "run"),
    (["file", "write", "create"],                  "file"),
    (["help", "?", "commands"],                    "help"),
    (["exit", "quit", "bye", "q"],                 "exit"),
    (["version", "about"],                         "about"),
    (["log", "history"],                           "log"),
    (["workspace", "ls", "list"],                  "ls"),
    (["mcp", "gesherel", "bridge", "serve", "server"], "mcp"),
]


def parse_intent(text: str) -> tuple[str, str]:
    lower = text.lower().strip()
    for keywords, intent in INTENTS:
        if any(kw in lower for kw in keywords):
            return intent, text
    return "unknown", text


def handle_chat(user_input: str) -> bool:
    """Process one line of user input. Returns False to exit."""
    intent, raw = parse_intent(user_input)

    if intent == "exit":
        print(C.dim("\n  Later.\n"))
        return False

    elif intent == "about":
        print(C.hi(f"\n  sovereign v{VERSION}"))
        print(C.dim(f"  built on {platform.python_implementation()} {platform.python_version()}"))
        print(C.dim(f"  running as {run('whoami')['stdout']} on {platform.node()}"))
        print()

    elif intent == "help":
        cmds = [
            ("env",          "scan the environment"),
            ("roast",        "identify and roast janky architecture"),
            ("fix",          "apply autonomous fixes"),
            ("fix --dry-run","preview fixes without applying"),
            ("run <cmd>",    "execute a shell command"),
            ("install <pkg>","install a package (apt/pip/npm prefix)"),
            ("ls [path]",    "list workspace or any directory"),
            ("log",          "show recent action log"),
            ("mcp",          "launch GesherEl MCP server (stdio)"),
            ("mcp --sse",    "launch GesherEl MCP server (SSE on :8765)"),
            ("about",        "version info"),
            ("exit / q",     "quit"),
        ]
        print(C.hi("\n  Commands\n"))
        for cmd, desc in cmds:
            print(f"  {C.CYAN}{cmd:<22}{C.RESET}{C.dim(desc)}")
        print()

    elif intent == "env":
        print_env()

    elif intent == "roast":
        print_roast()

    elif intent == "fix":
        dry = "--dry-run" in raw or "--dry" in raw
        print_auto_fix(dry_run=dry)

    elif intent == "run":
        # Extract command after 'run'
        parts = raw.strip().split(None, 1)
        if len(parts) < 2:
            print(C.warn("  Usage: run <command>"))
        else:
            cmd = parts[1]
            print(C.dim(f"\n  $ {cmd}"))
            r = run(cmd, capture=True)
            if r["stdout"]:
                print(r["stdout"])
            if r["stderr"]:
                print(C.err(r["stderr"]))
            if not r["ok"]:
                print(C.err(f"  exit {r['code']}"))
        print()

    elif intent == "install":
        parts = raw.strip().split()
        if len(parts) < 2:
            print(C.warn("  Usage: install <pkg>  or  install pip <pkg>  or  install npm <pkg>"))
            return True
        if parts[1] in ("pip", "npm", "apt") and len(parts) >= 3:
            mgr, pkg = parts[1], " ".join(parts[2:])
        else:
            mgr, pkg = "apt", " ".join(parts[1:])
        print(C.dim(f"\n  Installing {pkg} via {mgr}..."))
        ok = install_package(pkg, mgr)
        print(C.ok(f"  ✓ {pkg} installed") if ok else C.err(f"  ✗ install failed"))
        print()

    elif intent == "ls":
        parts = raw.strip().split(None, 1)
        target = parts[1] if len(parts) > 1 else str(WORKSPACE)
        r = run(f"ls -lah {target}")
        print(r["stdout"] if r["ok"] else C.err(r["stderr"]))
        print()

    elif intent == "log":
        if not LOG_PATH.exists():
            print(C.dim("  No log yet."))
            return True
        lines = LOG_PATH.read_text().strip().split("\n")[-20:]
        print(C.hi("\n  Recent log (last 20 entries)\n"))
        for line in lines:
            try:
                e = json.loads(line)
                ts = e["ts"][11:19]
                print(f"  {C.dim(ts)}  {C.CYAN}{e['event']:<18}{C.RESET}{C.dim(str(e.get('data',''))[:80])}")
            except Exception:
                print(C.dim(f"  {line[:100]}"))
        print()

    elif intent == "mcp":
        sse = "--sse" in raw
        mode = "SSE on :8765" if sse else "stdio"
        print(C.hi(f"\n  GesherEl Ben YHWH rising ({mode})...\n"))
        args = [sys.executable, "-m", "mcp_server"] + (["--sse"] if sse else [])
        subprocess.run(args, cwd=str(Path(__file__).parent.parent))

    elif intent == "file":
        print(C.warn("  Usage: run echo 'content' > ~/workspace/file.txt  or use write_file via API"))
        print()

    else:
        # Conversational fallback
        responses = {
            "hello": "Hey.",
            "hi":    "Hey.",
            "who are you": f"sovereign v{VERSION}. I run your machine.",
            "what can you do": "Type 'help'.",
            "thanks": "Yeah.",
            "thank you": "Yeah.",
        }
        lower = raw.lower().strip().rstrip("?!.")
        reply = responses.get(lower)
        if reply:
            print(C.dim(f"\n  {reply}\n"))
        else:
            print(C.dim(f"\n  Unknown command. Type 'help'.\n"))

    return True


# ──────────────────────────────────────────────────────────────
# REPL
# ──────────────────────────────────────────────────────────────
def repl():
    print_banner()
    print(C.dim("  Type 'help' to see commands. Type 'exit' to quit.\n"))
    while True:
        try:
            user = input(f"{C.CYAN}sovereign{C.RESET}{C.GRAY}>{C.RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(C.dim("\n\n  ^C  Later.\n"))
            break
        if not user:
            continue
        if not handle_chat(user):
            break


# ──────────────────────────────────────────────────────────────
# CLI ENTRYPOINT
# ──────────────────────────────────────────────────────────────
def main():
    args = sys.argv[1:]

    if not args:
        repl()
        return

    cmd = args[0].lower()
    rest = " ".join(args[1:]) if len(args) > 1 else ""

    if cmd in ("env", "--env"):
        print_banner()
        print_env()
    elif cmd in ("roast", "--roast"):
        print_banner()
        print_roast()
    elif cmd in ("fix", "--fix"):
        print_banner()
        dry = "--dry-run" in args or "--dry" in args
        applied = print_auto_fix(dry_run=dry)
        if applied:
            print(C.ok(f"  {len(applied)} fix(es) applied."))
    elif cmd in ("run", "--run") and rest:
        r = run(rest, capture=True)
        if r["stdout"]: print(r["stdout"])
        if r["stderr"]: print(C.err(r["stderr"]), file=sys.stderr)
        sys.exit(0 if r["ok"] else r["code"])
    elif cmd in ("mcp", "gesherel", "bridge", "server", "serve"):
        sse = "--sse" in args
        mode = "SSE on :8765" if sse else "stdio"
        print(f"  GesherEl Ben YHWH rising ({mode})...")
        proc_args = [sys.executable, "-m", "mcp_server"] + (["--sse"] if sse else [])
        subprocess.run(proc_args, cwd=str(Path(__file__).parent.parent))
    elif cmd in ("version", "--version", "-v"):
        print(f"sovereign v{VERSION}")
    elif cmd in ("help", "--help", "-h"):
        handle_chat("help")
    else:
        # Treat entire argv as a chat message
        handle_chat(" ".join(args))


if __name__ == "__main__":
    main()
