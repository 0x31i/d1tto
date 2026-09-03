"""Engagement = one client folder inside the vault.

Layout created by `new`:

    Engagements/2026-09-03_AcmeCorp/
    ├── AcmeCorp.md            <- dashboard / home note (links to everything)
    ├── 00_Admin/              scope.md, roe.md, contacts.md
    ├── 01_Recon/              OSINT, subdomains, wayback, etc.
    ├── 02_Scans/              raw nmap / nessus / other tool output
    ├── 03_Hosts/              one note per host
    ├── 04_Findings/           one note per finding (CVSS, PoC, remediation)
    ├── 05_Evidence/
    │   ├── img/               screenshots (image command)
    │   └── raw/               pasted code / output (code command)
    ├── 06_Creds/              creds.md (table)
    ├── 07_Report/             draft.md
    └── _log/                  YYYY-MM-DD.md daily activity log

Every writer method returns the Path it wrote so the CLI can link/open it.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from .templates import render, TEMPLATES

FOLDERS = [
    "00_Admin", "01_Recon", "02_Scans", "03_Hosts", "04_Findings",
    "05_Evidence/img", "05_Evidence/raw", "06_Creds", "07_Report", "_log",
]

# Obsidian hides empty folders, so drop a small index note in the ones that
# would otherwise start empty. Doubles as inline documentation of the layout.
FOLDER_NOTES = {
    "01_Recon": "OSINT, subdomains, wayback, exposure. Notes and screenshots go here.",
    "02_Scans": "Raw tool output. End a paste with `s` (scan); nmap auto-creates host notes.",
    "03_Hosts": "One note per host. Auto-created from nmap output, or `:host <ip> [name]`.",
    "04_Findings": "One note per finding. Use `:finding <severity> <title>`.",
    "05_Evidence/img": "Screenshots. End a line with `i` (image) to save the clipboard image.",
    "05_Evidence/raw": "Pasted code / command output. End a paste with `c` (code).",
}

SEVERITIES = ["critical", "high", "medium", "low", "info"]


def slugify(text: str) -> str:
    """Filesystem-and-wikilink safe name. 'Acme Corp!' -> 'Acme_Corp'."""
    text = re.sub(r"[^\w\s.-]", "", text.strip())
    return re.sub(r"\s+", "_", text) or "untitled"


def safe_filename(text: str) -> str:
    """Keep spaces (Obsidian-friendly) but drop path-illegal characters.
    'Acme Corp' -> 'Acme Corp', 'A/B:C' -> 'ABC'."""
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", text).strip().rstrip(".")
    return text or "untitled"


def stamp(fmt: str = "%Y%m%d-%H%M%S") -> str:
    return datetime.now().strftime(fmt)


class Engagement:
    def __init__(self, root: Path, tester: str = ""):
        self.root = root
        self.tester = tester
        self.client = self._load_client()

    def _load_client(self) -> str:
        """Original display name: from .d1tto metadata, else best-effort from the folder."""
        meta = self.root / ".d1tto"
        if meta.exists():
            try:
                name = json.loads(meta.read_text(encoding="utf-8")).get("client")
                if name:
                    return name
            except (ValueError, OSError):
                pass
        # legacy engagements: "2026-09-03_Acme_Corp" -> "Acme Corp"
        stem = self.root.name.split("_", 1)[1] if "_" in self.root.name else self.root.name
        return stem.replace("_", " ")

    # ---------------------------------------------------------------- create
    @classmethod
    def create(cls, engagements_dir: Path, client: str, tester: str = "",
               scope: str = "") -> "Engagement":
        folder = f"{stamp('%Y-%m-%d')}_{slugify(client)}"
        root = engagements_dir / folder
        if root.exists():
            raise FileExistsError(f"Engagement already exists: {root}")
        for f in FOLDERS:
            (root / f).mkdir(parents=True, exist_ok=True)
        # persist the original display name so reloads don't fall back to the slug
        (root / ".d1tto").write_text(
            json.dumps({"client": client, "created": stamp("%Y-%m-%d")}), encoding="utf-8")

        eng = cls(root, tester)
        ctx = dict(client=eng.client, tester=tester, date=stamp("%Y-%m-%d"),
                   scope=scope or "- ", folder=folder)
        eng._write(eng.dashboard, render("dashboard", ctx))
        eng._write(root / "00_Admin" / "scope.md", render("scope", ctx))
        eng._write(root / "00_Admin" / "roe.md", render("roe", ctx))
        eng._write(root / "00_Admin" / "contacts.md", render("contacts", ctx))
        eng._write(root / "06_Creds" / "creds.md", render("creds", ctx))
        eng._write(root / "07_Report" / "draft.md", render("report", ctx))
        eng._write(root / "05_Evidence" / "evidence.md", render("evidence", ctx))
        # index note in each otherwise-empty folder so Obsidian actually shows it
        for folder, blurb in FOLDER_NOTES.items():
            d = root / folder
            if not any(f.suffix == ".md" for f in d.iterdir()):
                eng._write(d / "_index.md", f"# {folder}\n\n{blurb}\n")
        eng.log(f"Engagement **{eng.client}** created by d1tto.")
        return eng

    # ---------------------------------------------------------------- paths
    @property
    def dashboard(self) -> Path:
        return self.root / f"{safe_filename(self.client)}.md"

    @property
    def today_log(self) -> Path:
        p = self.root / "_log" / f"{stamp('%Y-%m-%d')}.md"
        if not p.exists():
            self._write(p, render("daylog", dict(client=self.client,
                                                 date=stamp("%Y-%m-%d"),
                                                 tester=self.tester)))
        return p

    def rel(self, path: Path) -> str:
        """Path relative to engagement root, forward slashes (Obsidian style)."""
        return path.relative_to(self.root).as_posix()

    # ---------------------------------------------------------------- writers
    def log(self, text: str) -> Path:
        """Append a timestamped bullet to today's log."""
        p = self.today_log
        self._append(p, f"- `{stamp('%H:%M:%S')}` {text}\n")
        return p

    def note(self, text: str) -> Path:
        return self.log(text)

    def catchall(self, text: str) -> Path:
        """Append a timestamped line to the engagement's catch-all note (notes.md).
        This is where unflagged text lands in receive mode."""
        p = self.root / "notes.md"
        if not p.exists():
            self._write(p, f"# {self.client} notes\n\nUnflagged text dropped in with d1tto lands here.\n\n")
        self._append(p, f"- `{stamp('%Y-%m-%d %H:%M:%S')}` {text}\n")
        self.log(f"Note: {text[:80]}")
        return p

    def save_image(self, image, caption: str = "") -> Path:
        """image: a PIL.Image. Saves PNG, links it in evidence.md + daily log."""
        name = f"{stamp()}{'_' + slugify(caption) if caption else ''}.png"
        p = self.root / "05_Evidence" / "img" / name
        image.save(p, "PNG")
        embed = f"![[{name}]]"
        self._append(self.root / "05_Evidence" / "evidence.md",
                     f"\n### {caption or name}\n{stamp('%Y-%m-%d %H:%M')}\n\n{embed}\n")
        self.log(f"Screenshot: {embed} {caption}".rstrip())
        return p

    def save_code(self, text: str, lang: str = "", title: str = "") -> Path:
        """Pasted text -> raw file + fenced block in evidence.md + log link."""
        ext = {"bash": "sh", "shell": "sh", "sh": "sh", "python": "py", "py": "py",
               "powershell": "ps1", "ps1": "ps1", "http": "http", "json": "json",
               "xml": "xml", "sql": "sql", "js": "js"}.get(lang.lower(), "txt")
        name = f"{stamp()}{'_' + slugify(title) if title else ''}.{ext}"
        p = self.root / "05_Evidence" / "raw" / name
        p.write_text(text, encoding="utf-8")
        block = f"```{lang}\n{text.rstrip()}\n```"
        self._append(self.root / "05_Evidence" / "evidence.md",
                     f"\n### {title or name}\n{stamp('%Y-%m-%d %H:%M')} (raw: [[{name}]])\n\n{block}\n")
        self.log(f"Code/output saved: [[{name}]] {title}".rstrip())
        return p

    def save_scan(self, text: str, tool: str = "nmap", label: str = "") -> Path:
        """Raw tool output -> 02_Scans/<tool>_<stamp>_<label>.txt"""
        name = f"{slugify(tool)}_{stamp()}{'_' + slugify(label) if label else ''}.txt"
        p = self.root / "02_Scans" / name
        p.write_text(text, encoding="utf-8")
        self.log(f"Scan output ({tool}): [[{name}]] {label}".rstrip())
        # cheap auto-host extraction for nmap output
        if tool.lower() == "nmap":
            for ip in sorted(set(re.findall(r"Nmap scan report for (?:\S+ \()?(\d+\.\d+\.\d+\.\d+)", text))):
                self.host(ip, source=name)
        return p

    def host(self, ip: str, hostname: str = "", source: str = "") -> Path:
        """Create (or return existing) host note in 03_Hosts."""
        p = self.root / "03_Hosts" / f"{slugify(ip)}.md"
        if not p.exists():
            self._write(p, render("host", dict(ip=ip, hostname=hostname or "",
                                               client=self.client, date=stamp("%Y-%m-%d"),
                                               source=f"[[{source}]]" if source else "")))
            self.log(f"Host added: [[{slugify(ip)}]] {hostname}".rstrip())
        return p

    def finding(self, title: str, severity: str = "medium") -> Path:
        severity = severity.lower() if severity.lower() in SEVERITIES else "medium"
        existing = list((self.root / "04_Findings").glob("F*.md"))
        num = len(existing) + 1
        name = f"F{num:02d}_{slugify(title)}.md"
        p = self.root / "04_Findings" / name
        self._write(p, render("finding", dict(num=f"F{num:02d}", title=title,
                                              severity=severity, client=self.client,
                                              date=stamp("%Y-%m-%d"), tester=self.tester)))
        self.log(f"Finding: [[{p.stem}]] ({severity})")
        return p

    def cred(self, user: str, secret: str, host: str = "", ctx: str = "") -> Path:
        p = self.root / "06_Creds" / "creds.md"
        self._append(p, f"| {stamp('%Y-%m-%d %H:%M')} | `{user}` | `{secret}` | {host} | {ctx} |\n")
        self.log(f"Cred captured for `{user}`{' on ' + host if host else ''}")
        return p

    # ---------------------------------------------------------------- io
    @staticmethod
    def _write(p: Path, content: str) -> None:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    @staticmethod
    def _append(p: Path, content: str) -> None:
        with p.open("a", encoding="utf-8") as fh:
            fh.write(content)


def list_engagements(engagements_dir: Path) -> list[Path]:
    if not engagements_dir.exists():
        return []
    return sorted((p for p in engagements_dir.iterdir() if p.is_dir()), reverse=True)
