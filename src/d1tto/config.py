"""Config: where the Obsidian vault lives and which engagement is active.

Stored as JSON in the OS-appropriate config dir:
  Windows: %APPDATA%\\d1tto\\config.json
  macOS:   ~/Library/Application Support/d1tto/config.json
  Linux:   ~/.config/d1tto/config.json
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path

from platformdirs import user_config_dir

CONFIG_DIR = Path(user_config_dir("d1tto"))
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class Config:
    vault_path: str = ""            # absolute path to the Obsidian vault root
    vault_name: str = ""            # name Obsidian shows (folder name by default)
    engagements_dir: str = "Engagements"  # subfolder inside the vault
    current: str = ""               # folder name of the active engagement
    tester: str = ""                # your name, goes into frontmatter
    open_after_create: bool = True  # fire obsidian:// URI after creating files
    extra: dict = field(default_factory=dict)

    # ---- persistence -------------------------------------------------
    @classmethod
    def load(cls) -> "Config":
        if CONFIG_FILE.exists():
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        return cls()

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    # ---- helpers -----------------------------------------------------
    @property
    def vault(self) -> Path:
        return Path(self.vault_path).expanduser().resolve()

    @property
    def engagements(self) -> Path:
        return self.vault / self.engagements_dir

    @property
    def is_configured(self) -> bool:
        return bool(self.vault_path) and self.vault.exists()
