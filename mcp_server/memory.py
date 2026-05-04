"""
Shared persistent memory for GesherEl — ~/.sovereign/memory.json
All apps (kcli, NeonForge Voice, NeonForge Vocal, sovereign) read/write here.
"""

import json
import threading
from pathlib import Path
from typing import Any

_MEMORY_PATH = Path.home() / ".sovereign" / "memory.json"
_lock = threading.Lock()


class Memory:
    def __init__(self, path: Path = _MEMORY_PATH):
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, data: dict) -> None:
        self._path.write_text(json.dumps(data, indent=2))

    def get(self, key: str, default: Any = None) -> Any:
        with _lock:
            return self._load().get(key, default)

    def set(self, key: str, value: Any) -> None:
        with _lock:
            data = self._load()
            data[key] = value
            self._save(data)

    def delete(self, key: str) -> bool:
        with _lock:
            data = self._load()
            if key not in data:
                return False
            del data[key]
            self._save(data)
            return True

    def list_keys(self) -> list[str]:
        with _lock:
            return list(self._load().keys())

    def dump(self) -> dict:
        with _lock:
            return dict(self._load())


memory = Memory()
