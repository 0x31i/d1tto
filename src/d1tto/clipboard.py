"""Clipboard (image + text) and Obsidian URI helpers, cross-platform.

Image grabbing:
  Windows / macOS : Pillow's ImageGrab.grabclipboard() works natively.
  Linux (Kali)    : Pillow shells out to `xclip` (X11) or `wl-paste` (Wayland).
                    -> sudo apt install xclip wl-clipboard
Text grabbing:
  pyperclip; on Linux it also wants xclip/xsel.
"""
from __future__ import annotations

import subprocess
import sys
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Optional

import pyperclip


def get_text() -> str:
    try:
        return pyperclip.paste() or ""
    except pyperclip.PyperclipException as e:
        raise RuntimeError(f"Clipboard text unavailable: {e}") from e


def get_image():
    """Return a PIL Image from the clipboard, or None if there isn't one."""
    from PIL import ImageGrab, Image
    try:
        data = ImageGrab.grabclipboard()
    except Exception as e:  # pragma: no cover - platform specific
        raise RuntimeError(f"Clipboard image unavailable: {e}") from e
    if data is None:
        return None
    # On Windows, copying a file in Explorer yields a list of paths
    if isinstance(data, list):
        for item in data:
            p = Path(item)
            if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}:
                return Image.open(p).convert("RGB")
        return None
    return data


def obsidian_uri(vault: str, file_rel: Optional[str] = None) -> str:
    """obsidian://open?vault=<vault>&file=<path-without-.md>"""
    q = {"vault": vault}
    if file_rel:
        q["file"] = file_rel[:-3] if file_rel.endswith(".md") else file_rel
    return "obsidian://open?" + urllib.parse.urlencode(q, quote_via=urllib.parse.quote)


def open_in_obsidian(vault: str, file_rel: Optional[str] = None) -> bool:
    uri = obsidian_uri(vault, file_rel)
    try:
        if sys.platform.startswith("linux"):
            subprocess.Popen(["xdg-open", uri], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", uri])
        else:  # windows
            webbrowser.open(uri)
        return True
    except Exception:
        return False
