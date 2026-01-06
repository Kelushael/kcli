"""Configuration management for KCLI."""

import os
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

# Default paths
KCLI_HOME = Path.home() / ".kcli"
CONFIG_FILE = KCLI_HOME / "config.json"
WORKSPACE_DIR = KCLI_HOME / "workspace"
LOGS_DIR = KCLI_HOME / "logs"
DATA_DIR = KCLI_HOME / "data"


@dataclass
class KCLIConfig:
    """KCLI Configuration settings."""
    provider: str = "openrouter"
    model: str = "cognitivecomputations/dolphin-mistral-24b-venice-edition:free"
    api_key: str = ""
    base_url: str = "https://openrouter.ai/api/v1"
    workspace: str = str(WORKSPACE_DIR)
    ollama_host: str = "http://127.0.0.1:11434"
    llamacpp_url: str = "http://127.0.0.1:8080"
    auto_approve: bool = False
    max_context: int = 25
    
    @classmethod
    def load(cls) -> "KCLIConfig":
        """Load config from file or create default."""
        # Ensure directories exist
        for d in [KCLI_HOME, WORKSPACE_DIR, LOGS_DIR, DATA_DIR]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Load from file if exists
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                return cls(**data)
            except Exception:
                pass
        
        # Try environment variables
        config = cls(
            provider=os.getenv("KCLI_PROVIDER", "openrouter"),
            model=os.getenv("KCLI_MODEL", "cognitivecomputations/dolphin-mistral-24b-venice-edition:free"),
            api_key=os.getenv("KCLI_API_KEY") or os.getenv("OPENROUTER_API_KEY", ""),
            base_url=os.getenv("KCLI_BASE_URL", "https://openrouter.ai/api/v1"),
            ollama_host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
            llamacpp_url=os.getenv("LLAMACPP_BASE_URL", "http://127.0.0.1:8080"),
        )
        config.save()
        return config
    
    def save(self):
        """Save config to file."""
        with open(CONFIG_FILE, 'w') as f:
            json.dump(asdict(self), f, indent=2)
    
    def set_api_key(self, key: str):
        """Set and save API key."""
        self.api_key = key
        self.save()
