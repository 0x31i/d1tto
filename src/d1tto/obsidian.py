"""Find Obsidian vaults so the CLI can offer them instead of asking for a path.

Obsidian keeps a registry of every vault you have opened in `obsidian.json`:
  macOS:   ~/Library/Application Support/obsidian/obsidian.json
  Windows: %APPDATA%/obsidian/obsidian.json
  Linux:   ~/.config/obsidian/obsidian.json   (Flatpak/Snap paths handled too)

Each entry looks like {"<id>": {"path": "/abs/vault", "ts": ..., "open": true}}.
We read that first, then fall back to scanning a few common locations for a
`.obsidian/` folder in case a vault was never registered.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Vault:
    name: str
    path: Path
    is_open: bool = False
    source: str = "registry"   # "registry" or "scan"

    @property
    def valid(self) -> bool:
        return (self.path / ".obsidian").is_dir()


def registry_paths() -> list[Path]:
    home = Path.home()
    if sys.platform == "darwin":
        return [home / "Library/Application Support/obsidian/obsidian.json"]
    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA", str(home / "AppData/Roaming"))
        return [Path(appdata) / "obsidian/obsidian.json"]
    return [  # linux, incl. flatpak + snap
        home / ".config/obsidian/obsidian.json",
        home / ".var/app/md.obsidian.Obsidian/config/obsidian/obsidian.json",
        home / "snap/obsidian/current/.config/obsidian/obsidian.json",
    ]


def from_registry() -> list[Vault]:
    out: list[Vault] = []
    for reg in registry_paths():
        if not reg.is_file():
            continue
        try:
            data = json.loads(reg.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for entry in (data.get("vaults") or {}).values():
            raw = entry.get("path", "")
            if not raw:
                continue
            p = Path(raw).expanduser()
            out.append(Vault(name=p.name, path=p, is_open=bool(entry.get("open")), source="registry"))
    return out


def _iterdir(p: Path):
    try:
        return list(p.iterdir())
    except (OSError, PermissionError):
        return []


def scan(dirs: list[Path] | None = None) -> list[Vault]:
    """Cheap fallback: check common roots and their immediate children for `.obsidian/`."""
    home = Path.home()
    roots = dirs or [home / "Documents", home / "Desktop", home,
                     home / "vaults", home / "Notes", home / "obsidian", home / "iCloud"]
    found: list[Vault] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for cand in [root, *[c for c in _iterdir(root) if c.is_dir()]]:
            rp = cand.resolve()
            if rp in seen:
                continue
            if (cand / ".obsidian").is_dir():
                seen.add(rp)
                found.append(Vault(name=cand.name, path=cand, source="scan"))
    return found


def discover() -> list[Vault]:
    """All known vaults, deduped by resolved path, open ones first then alphabetical."""
    merged: dict[Path, Vault] = {}
    for v in from_registry() + scan():
        key = v.path.resolve()
        if key not in merged:
            merged[key] = v
        elif v.is_open:
            merged[key].is_open = True
    return sorted(merged.values(), key=lambda v: (not v.is_open, v.name.lower()))
