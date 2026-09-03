<p align="center">
  <img src="assets/d1tto-logo.jpg" alt="d1tto" width="820">
</p>

<h1 align="center">d1tto</h1>

<p align="center">Your clipboard, copied straight into an Obsidian pentest engagement.</p>

<p align="center">
  <a href="https://github.com/0x31i/d1tto/actions/workflows/ci.yml"><img src="https://github.com/0x31i/d1tto/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/license-MIT-a78bfa" alt="MIT license">
  <img src="https://img.shields.io/badge/python-3.10%2B-a78bfa" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/notes-obsidian-a78bfa" alt="Obsidian">
  <img src="https://img.shields.io/badge/platforms-win%20%7C%20mac%20%7C%20linux-a78bfa" alt="cross-platform">
</p>

---

d1tto is a small cross-platform CLI (Windows, macOS, Kali) that turns an Obsidian vault into your
pentest notebook. It finds your vault on its own, scaffolds a standard engagement folder tree, and
copies whatever is on your clipboard (a screenshot, nmap output, a finding, a credential) into the
right note, wikilinked so Obsidian picks it up instantly. Like the Pokémon, it copies anything into
whatever shape you need.

The command is `d1tto` (not `ditto`, which macOS already uses for a file-copy utility).

## Auto-detects your Obsidian vault

Obsidian keeps a registry of every vault you have opened. d1tto reads it, so `d1tto init` just lists
your vaults and you pick one. No path typing.

```console
$ d1tto init
      Detected Obsidian vaults
  # │ Vault          │ Path                         │
  0 │ MAIN VAULT     │ /Users/you/Documents/MAIN…   │ open
  1 │ Obsidian Vault │ /Users/you/Documents/Obsid…  │
  Pick a vault # (or m to enter a path):
```

If nothing is registered it falls back to scanning common locations for a `.obsidian/` folder, or you
can type a path by hand.

## Install

```bash
# all platforms (Python 3.10+)
pipx install git+https://github.com/0x31i/d1tto.git
#   or, for dev:  git clone https://github.com/0x31i/d1tto.git && cd d1tto && pip install -e .
```

Kali / Debian extras for clipboard access:

```bash
sudo apt install xclip wl-clipboard   # X11 + Wayland
```

## First run

```bash
d1tto init      # pick your vault from the detected list, set your name
d1tto           # open the shell; it prompts for a client if none is active
```

Config lives at `~/.config/d1tto/config.json` (Windows: `%APPDATA%\d1tto`, macOS:
`~/Library/Application Support/d1tto`).

## Folder tree per engagement

```
Engagements/2026-09-03_AcmeCorp/
├── AcmeCorp.md        dashboard (links to everything)
├── 00_Admin/          scope.md · roe.md · contacts.md
├── 01_Recon/
├── 02_Scans/          raw nmap / nessus output      <- scan
├── 03_Hosts/          one note per host             <- host  (nmap auto-creates)
├── 04_Findings/       F01_*.md CVSS / PoC / fix     <- finding
├── 05_Evidence/
│   ├── evidence.md    running log of every capture
│   ├── img/           screenshots                   <- image
│   └── raw/           pasted output / code          <- code
├── 06_Creds/creds.md  table                         <- cred
├── 07_Report/draft.md
└── _log/2026-09-03.md timestamped daily log         <- note (everything logs here)
```

Obsidian hides empty folders, so d1tto drops a small `_index.md` into the ones that start empty. The
whole tree shows up in the file explorer from the moment you create it.

## Paste and flag

Run `d1tto` to drop into receive mode against the active engagement. Type or paste, then end the line
with a short flag that says what it is. Nothing else to learn.

| you type | what lands |
|---|---|
| `box .5 runs an old jenkins` | a note in the engagement's catch-all `notes.md` |
| *(empty enter)* | whatever text is on your clipboard, saved as a note |
| `portal login i` | the clipboard image to `05_Evidence/img/`, caption "portal login" |
| `bash c` | the clipboard text as a fenced code block plus a raw file |
| `nmap top1000 s` | the clipboard text to `02_Scans/`; nmap output auto-creates host notes |

The flags are forgiving. Image is `i`, `-i`, `/i`, or `image`. Code is `c`, `-c`, or `code`. Scan is
`s`, `-s`, or `scan`. If the last word looks like a flag but there is nothing to file (no image on the
clipboard, no text), d1tto just keeps the whole line as a note, so you never lose a thought.

Structured actions use a leading colon:

| command | what it does |
|---|---|
| `:new <client> [scope]` | scaffold a new engagement |
| `:use <n\|name>` · `:ls` | switch or list engagements |
| `:finding <sev> <title>` | new finding note (critical / high / medium / low / info) |
| `:host <ip> [name]` | new host note |
| `:cred <user> <secret> [host] [ctx]` | row in the creds table |
| `:open [file]` · `:vaults` · `:status` · `:config` · `:help` · `:q` | housekeeping |

It works one-shot from any terminal too, so you can bind it to a hotkey:

```bash
d1tto "started internal"        # a quick note
d1tto portal login i            # grab the clipboard screenshot
d1tto :finding high SQLi in login
```

## Typical flow

```console
$ d1tto
💜 Acme_Corp > box .5 is running jenkins 2.426, no auth
✔ Note -> notes.md
💜 Acme_Corp > portal login i            # screenshot on the clipboard
✔ Image 1440x900 -> 05_Evidence/img/20260903-093140_portal_login.png
💜 Acme_Corp > bash c                    # command output on the clipboard
✔ Code (2 lines) -> 05_Evidence/raw/20260903-093205.sh
💜 Acme_Corp > nmap top1000 s            # nmap output on the clipboard
✔ nmap scan (212 lines) -> 02_Scans/nmap_20260903-093012_top1000.txt
💜 Acme_Corp > :finding high SQLi in portal login
✔ Finding (high) -> 04_Findings/F01_SQLi_in_portal_login.md
```

## Recommended Obsidian plugins

- **Dataview** for findings and hosts tables on the dashboard.
- **Templater** if you want richer templates than the built-in ones.
- Set *Settings > Files & Links > Default location for new attachments* to "same folder as current
  file" so manual drag-drops land next to your notes.

## Dev

```bash
pip install -e . pytest
pytest
```

CI runs the test suite on Ubuntu, Windows, and macOS (`.github/workflows/ci.yml`).

## Roadmap

- `report` command to stitch findings into `07_Report/draft.md`.
- Nessus `.nessus` and Burp XML importers that create findings.
- Watch-folder mode: drop a file anywhere and d1tto files it.
- Redact command for `06_Creds` before archiving.

MIT © Elias Sims. Use it on engagements you are authorized to run.
