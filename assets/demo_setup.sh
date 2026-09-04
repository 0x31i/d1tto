#!/usr/bin/env bash
# Isolated environment for the d1tto demo (sourced by assets/demo.tape).
# Uses D1TTO_CONFIG + a throwaway vault so it never touches your real setup.

# use a local editable install if one is present (dev machines)
[ -x "$PWD/.venv/bin/d1tto" ] && export PATH="$PWD/.venv/bin:$PATH"

export D1TTO_CONFIG="$(mktemp -d)/config.json"
DEMO_VAULT="$(mktemp -d)/DemoVault"
mkdir -p "$DEMO_VAULT/.obsidian"

python3 - "$DEMO_VAULT" "$D1TTO_CONFIG" <<'PY'
import json, sys, pathlib
vault, cfg = sys.argv[1], sys.argv[2]
pathlib.Path(cfg).write_text(json.dumps({
    "vault_path": vault, "vault_name": "DemoVault",
    "engagements_dir": "Engagements", "current": "",
    "tester": "eli", "open_after_create": False,   # don't launch Obsidian mid-recording
}))
PY

# a bit of command output on the clipboard so the `c` (code) flag has something to grab
_copy() {
  if command -v pbcopy >/dev/null; then pbcopy
  elif command -v xclip >/dev/null; then xclip -selection clipboard
  elif command -v wl-copy >/dev/null; then wl-copy
  else cat >/dev/null; fi
}
printf 'id\nuid=0(root) gid=0(root) groups=0(root)\nsudo -l\n(ALL) NOPASSWD: ALL' | _copy
clear
