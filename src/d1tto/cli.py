"""d1tto: a paste-and-flag receiver for pentest notes into Obsidian.

Run `d1tto` (or `d1t`) to drop into receive mode against the active engagement.
Type or paste, then end the line with a short flag to say what it is:

    <your text>            a note in the engagement's catch-all (notes.md)
    <empty enter>          the clipboard's text as a note
    ... i   (or image)     save the clipboard IMAGE   (words before the flag = caption)
    ... c   (or code)      save the clipboard TEXT as code   (before = [lang] [title])
    ... s   (or scan)      save the clipboard TEXT as a scan  (before = [tool] [label])

Structured actions use a leading colon:

    :new <client> [scope]   :use <n|name>   :ls   :vaults   :status   :open [file]
    :finding <sev> <title>  :host <ip> [name]   :cred <user> <secret> [host] [ctx]
    :config [key value]     :help   :q
"""
from __future__ import annotations

import shlex
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .config import Config, CONFIG_FILE
from .engagement import Engagement, list_engagements, SEVERITIES
from . import clipboard as clip

con = Console()

BANNER = r"""
     _ _ _   _        
  __| / | |_| |_ ___  
 / _` | | __| __/ _ \ 
| (_| | | |_| || (_) |
 \__,_|_|\__|\__\___/ 
                      
   it copies anything into your obsidian vault.
"""

# trailing flags: end your paste with one of these to tag the type
IMAGE_FLAGS = {"i", "-i", "/i", "image", "-image", "/image", "img", "ss"}
CODE_FLAGS  = {"c", "-c", "/c", "code", "-code", "/code"}
SCAN_FLAGS  = {"s", "-s", "/s", "scan", "-scan", "/scan"}
LANGS = {"bash", "sh", "shell", "python", "py", "powershell", "ps1", "ps", "http",
         "json", "xml", "sql", "js", "ts", "go", "rb", "php", "java", "yaml", "ini",
         "dockerfile", "c", "cpp", "html", "css"}
COMMAND_WORDS = {"new", "use", "ls", "vaults", "status", "open", "finding", "host",
                 "cred", "config", "help", "quit", "exit"}

HELP = """[bold]receive mode[/]: type or paste, then end with a flag.
  [dim](nothing)[/] note   [bold]i[/] image   [bold]c[/] code   [bold]s[/] scan
  an empty line files whatever text is on your clipboard as a note.
[bold]colon-commands[/]:
  [bold]:new[/] <client> [scope]   [bold]:use[/] <n|name>   [bold]:ls[/]   [bold]:vaults[/]   [bold]:status[/]
  [bold]:finding[/] <sev> <title>   [bold]:host[/] <ip> [name]   [bold]:cred[/] <user> <secret> [host] [ctx]
  [bold]:open[/] [file]   [bold]:config[/] [key value]   [bold]:help[/]   [bold]:q[/]"""


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def _prompt(eng) -> str:
    return f"[bold #a78bfa]● {eng.client if eng else 'no-engagement'}[/] > "


def _args(s: str) -> list[str]:
    try:
        return shlex.split(s)
    except ValueError:
        return s.split()


def _clip_text() -> str:
    try:
        return clip.get_text()
    except RuntimeError as e:
        con.print(f"[red]{e}[/]")
        return ""


def _done(eng, path, msg):
    con.print(f"[green]✔[/] {msg} → [dim]{eng.rel(path)}[/]")


# ---------------------------------------------------------------------------
# the receiver: file one non-command line by its trailing flag (default: note)
# ---------------------------------------------------------------------------
def receive(line: str, eng: Engagement) -> None:
    toks = line.split()
    last = toks[-1].lower() if toks else ""
    rest = toks[:-1]
    rest_str = " ".join(rest)

    if last in IMAGE_FLAGS:
        try:
            img = clip.get_image()
        except RuntimeError as e:
            con.print(f"[red]{e}[/]"); return
        if img is None:                                   # not really an image, keep the line as a note
            _done(eng, eng.catchall(line), "Note"); return
        _done(eng, eng.save_image(img, rest_str), f"Image {img.size[0]}x{img.size[1]}")
        return

    if last in CODE_FLAGS or last in SCAN_FLAGS:
        text = _clip_text()
        if not text.strip():                              # nothing on clipboard, keep as a note
            _done(eng, eng.catchall(line), "Note"); return
        if last in CODE_FLAGS:
            lang = rest[0] if rest and rest[0].lower() in LANGS else ""
            title = " ".join(rest[1:]) if lang else rest_str
            _done(eng, eng.save_code(text, lang, title), f"Code ({len(text.splitlines())} lines)")
        else:
            tool = rest[0] if rest else "nmap"
            label = " ".join(rest[1:]) if rest else ""
            _done(eng, eng.save_scan(text, tool, label), f"{tool} scan ({len(text.splitlines())} lines)")
        return

    _done(eng, eng.catchall(line), "Note")                # default: the whole line is a note


# ---------------------------------------------------------------------------
# colon-commands
# ---------------------------------------------------------------------------
def command(parts, cfg: Config, eng):
    """Handle a :command from already-tokenized parts. Returns (engagement, should_quit)."""
    if not parts:
        return eng, False
    cmd, rest = parts[0].lower(), parts[1:]

    if cmd in ("q", "quit", "exit"):
        con.print("[dim]saved to the vault. gl hf.[/]"); return eng, True
    if cmd in ("h", "help", "?"):
        con.print(Panel(HELP, title="d1tto")); return eng, False
    if cmd == "new":
        return _create(cfg, rest), False
    if cmd == "use":
        return _use(cfg, eng, " ".join(rest)), False
    if cmd == "ls":
        _ls(cfg, eng); return eng, False
    if cmd == "vaults":
        _vaults(cfg); return eng, False
    if cmd == "status":
        _status(cfg, eng); return eng, False
    if cmd == "open":
        if eng:
            _open(cfg, eng, " ".join(rest))
        return eng, False
    if cmd == "config":
        _config(cfg, rest); return eng, False

    if not eng:
        con.print("[red]No active engagement.[/] Use [bold]:new <client>[/].")
        return eng, False
    if cmd == "finding":
        if not rest:
            con.print("usage: :finding <sev> <title>"); return eng, False
        has_sev = rest[0].lower() in SEVERITIES
        sev = rest[0].lower() if has_sev else "medium"
        title = " ".join(rest[1:]) if has_sev else " ".join(rest)
        if not title:
            con.print("[red]Need a title.[/]"); return eng, False
        p = eng.finding(title, sev); _done(eng, p, f"Finding ({sev})")
        if cfg.open_after_create:
            _open(cfg, eng, eng.rel(p))
        return eng, False
    if cmd == "host":
        if not rest:
            con.print("usage: :host <ip> [name]"); return eng, False
        _done(eng, eng.host(rest[0], rest[1] if len(rest) > 1 else ""), "Host")
        return eng, False
    if cmd == "cred":
        if len(rest) < 2:
            con.print("usage: :cred <user> <secret> [host] [ctx]"); return eng, False
        p = eng.cred(rest[0], rest[1], rest[2] if len(rest) > 2 else "", " ".join(rest[3:]))
        _done(eng, p, "Credential"); return eng, False

    con.print(f"[red]unknown command:[/] {cmd}  (try [bold]:help[/])")
    return eng, False


def _create(cfg, parts):
    client = parts[0] if parts else con.input("[bold]Client / engagement name:[/] ").strip()
    if not client:
        return None
    scope = "\n".join(f"- {s}" for s in parts[1:]) if len(parts) > 1 else \
        con.input("[bold]In-scope targets[/] (comma-sep, blank to skip): ").strip()
    if scope and not scope.startswith("- "):
        scope = "\n".join(f"- {s.strip()}" for s in scope.split(","))
    try:
        eng = Engagement.create(cfg.engagements, client, cfg.tester, scope)
    except FileExistsError as e:
        con.print(f"[red]{e}[/]"); return None
    cfg.current = eng.root.name; cfg.save()
    con.print(Panel(f"[bold green]{eng.client}[/] created at\n[dim]{eng.root}[/]", title="engagement"))
    if cfg.open_after_create:
        _open(cfg, eng, "")
    return eng


def _use(cfg, eng, arg):
    engs = list_engagements(cfg.engagements)
    target = engs[int(arg)] if arg.isdigit() and 0 <= int(arg) < len(engs) else \
        next((e for e in engs if arg.lower() in e.name.lower()), None)
    if not target:
        con.print("[red]Not found.[/] Run [bold]:ls[/]."); return eng
    cfg.current = target.name; cfg.save()
    ne = Engagement(target, cfg.tester)
    con.print(f"[green]✔[/] Using [bold]{ne.client}[/]")
    return ne


def _ls(cfg, eng):
    t = Table(title="Engagements"); t.add_column("#", style="dim"); t.add_column("Folder"); t.add_column("Active")
    for i, e in enumerate(list_engagements(cfg.engagements)):
        t.add_row(str(i), e.name, "[#a78bfa]●[/]" if eng and e == eng.root else "")
    con.print(t)


def _vaults(cfg):
    from .obsidian import discover
    vs = discover()
    if not vs:
        con.print("[yellow]No Obsidian vaults detected.[/]"); return
    t = Table(title="Detected Obsidian vaults"); t.add_column("Vault"); t.add_column("Path", style="dim"); t.add_column("")
    for v in vs:
        active = str(v.path.resolve()) == cfg.vault_path
        t.add_row(v.name, str(v.path), "← active" if active else ("open" if v.is_open else ""))
    con.print(t)


def _status(cfg, eng):
    t = Table(show_header=False)
    t.add_row("Vault", str(cfg.vault)); t.add_row("Vault name", cfg.vault_name)
    t.add_row("Engagement", eng.root.name if eng else "-"); t.add_row("Tester", cfg.tester or "-")
    t.add_row("Config", str(CONFIG_FILE)); con.print(t)


def _open(cfg, eng, arg):
    target = eng.root / arg if arg else eng.dashboard
    rel = target.relative_to(cfg.vault).as_posix()
    if clip.open_in_obsidian(cfg.vault_name, rel):
        con.print(f"[dim]→ obsidian://{rel}[/]")


def _config(cfg, parts):
    if len(parts) == 2 and hasattr(cfg, parts[0]):
        val = parts[1]
        if parts[0] == "open_after_create":
            val = val.lower() in ("1", "true", "yes", "on")
        setattr(cfg, parts[0], val); cfg.save()
        con.print(f"[green]✔[/] {parts[0]} = {val}")
    else:
        _status(cfg, None)


# ---------------------------------------------------------------------------
# setup wizard (auto-detects vaults from Obsidian's registry)
# ---------------------------------------------------------------------------
def init_wizard(cfg: Config) -> Config:
    from .obsidian import discover
    vaults = discover()
    vault = None
    detected_name = None

    if vaults:
        t = Table(title="Detected Obsidian vaults", show_lines=False)
        t.add_column("#", style="dim"); t.add_column("Vault"); t.add_column("Path", style="dim"); t.add_column("")
        for i, v in enumerate(vaults):
            t.add_row(str(i), v.name, str(v.path), "open" if v.is_open else "")
        con.print(t)
        choice = con.input("[bold]Pick a vault #[/] (or [bold]m[/] to enter a path): ").strip().lower()
        if choice.isdigit() and 0 <= int(choice) < len(vaults):
            picked = vaults[int(choice)]
            vault, detected_name = picked.path, picked.name
    else:
        con.print(Panel("No Obsidian vaults auto-detected (is Obsidian installed with a vault opened?).",
                        title="init"))

    from pathlib import Path
    if vault is None:
        con.print("Enter the folder that contains [bold].obsidian/[/].")
        while True:
            path = con.input("[bold]Vault path:[/] ").strip().strip('"')
            vault = Path(path).expanduser()
            if vault.exists():
                break
            if con.input(f"[yellow]{vault} doesn't exist.[/] Create it? [y/N] ").lower() == "y":
                vault.mkdir(parents=True); (vault / ".obsidian").mkdir(exist_ok=True)
                break
    cfg.vault_path = str(vault.resolve())
    cfg.vault_name = con.input(f"[bold]Vault name in Obsidian[/] [{detected_name or vault.name}]: ").strip() \
        or (detected_name or vault.name)
    cfg.engagements_dir = con.input("[bold]Engagements subfolder[/] [Engagements]: ").strip() or "Engagements"
    cfg.tester = con.input("[bold]Your name[/] (for frontmatter): ").strip()
    cfg.save()
    cfg.engagements.mkdir(parents=True, exist_ok=True)
    con.print(f"[green]✔[/] Saved to [dim]{CONFIG_FILE}[/]")
    return cfg


# ---------------------------------------------------------------------------
# receive loop + entrypoint
# ---------------------------------------------------------------------------
def receive_loop(cfg: Config, eng):
    con.print("[dim]type or paste, then a flag (i/c/s), or just text for a note. :help for commands, :q to quit.[/]\n")
    while True:
        try:
            line = con.input(_prompt(eng)).strip()
        except (EOFError, KeyboardInterrupt):
            con.print("\n[dim]bye.[/]"); break
        if not line:
            txt = _clip_text()
            if txt.strip():
                _done(eng, eng.catchall(txt), "Note (from clipboard)")
            continue
        if line.startswith(":"):
            eng, quit_ = command(_args(line[1:].strip()), cfg, eng)
            if quit_:
                break
            continue
        if not eng:
            con.print("[red]No active engagement.[/] Use [bold]:new <client>[/].")
            continue
        receive(line, eng)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    cfg = Config.load()

    if argv and argv[0] in ("-h", "--help"):
        con.print(__doc__); return 0
    if argv and argv[0] in ("-V", "--version"):
        con.print(f"d1tto {__version__}"); return 0
    if (argv and argv[0] == "init") or not cfg.is_configured:
        cfg = init_wizard(cfg)
        if argv and argv[0] == "init":
            return 0

    eng = None
    if cfg.current and (cfg.engagements / cfg.current).exists():
        eng = Engagement(cfg.engagements / cfg.current, cfg.tester)

    con.print(f"[bold #a78bfa]{BANNER.format(v=__version__)}[/]")

    # one-shot: d1tto new Acme / d1tto i / d1tto "a quick note" / d1tto :new "Acme Corp"
    if argv:
        first = argv[0]
        if first.startswith(":") or first.lower() in COMMAND_WORDS:
            parts = ([first[1:]] if first.startswith(":") else [first]) + argv[1:]
            command([p for p in parts if p], cfg, eng)   # argv already tokenized: quotes preserved
        elif eng:
            receive(" ".join(argv), eng)
        else:
            con.print("[red]No engagement yet.[/] Run [bold]d1tto :new <client>[/] first.")
            return 1
        return 0

    # interactive
    if not eng:
        con.print("No active engagement. Let's make one.")
        eng = _create(cfg, [])
        if not eng:
            return 0
    else:
        con.print(f"Resuming [bold]{eng.client}[/]. [dim]:help for commands, :q to quit.[/]\n")
    receive_loop(cfg, eng)
    return 0


if __name__ == "__main__":
    sys.exit(main())
