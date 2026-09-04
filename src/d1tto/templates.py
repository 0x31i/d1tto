"""Note templates. Edit freely: these are plain strings with {placeholders}.

Frontmatter fields are chosen so Obsidian's Dataview / Bases plugins can
build tables from them (e.g. all findings with severity == high).
"""
from __future__ import annotations

TEMPLATES: dict[str, str] = {}

TEMPLATES["dashboard"] = """---
type: engagement
client: "{client}"
tester: "{tester}"
start: {date}
status: active
tags: [pentest, engagement]
---
# {client}: Engagement Dashboard

> Created by d1tto on {date}.

## Admin
- [[00_Admin/scope|Scope]] · [[00_Admin/roe|Rules of Engagement]] · [[00_Admin/contacts|Contacts]]

## Working Notes
- [[05_Evidence/evidence|Evidence log]]
- [[06_Creds/creds|Credentials]]
- [[07_Report/draft|Report draft]]
- Daily logs: `_log/`

## Findings
```dataview
TABLE severity, status, cvss FROM "{folder}/04_Findings" SORT severity ASC
```

## Hosts
```dataview
TABLE hostname, os, status FROM "{folder}/03_Hosts" SORT file.name ASC
```

## Scans
- `02_Scans/`: raw tool output (nmap, nessus, etc.)
"""

TEMPLATES["scope"] = """---
type: scope
client: "{client}"
---
# Scope: {client}

## In scope
{scope}

## Out of scope
- 

## Testing window
- Start: {date}
- End: 

## Notes
- 
"""

TEMPLATES["roe"] = """---
type: roe
client: "{client}"
---
# Rules of Engagement: {client}

- Authorised by: 
- Emergency contact: 
- Allowed hours: 
- Forbidden: DoS, social engineering, ... (edit)
- Source IPs to whitelist: 
"""

TEMPLATES["contacts"] = """---
type: contacts
client: "{client}"
---
# Contacts: {client}

| Name | Role | Email | Phone | Notes |
|------|------|-------|-------|-------|
|      |      |       |       |       |
"""

TEMPLATES["creds"] = """---
type: creds
client: "{client}"
tags: [creds, sensitive]
---
# Credentials: {client}

> Sensitive. Scrub before sharing the vault.

| Captured | User | Secret | Host / Service | Context |
|----------|------|--------|----------------|---------|
"""

TEMPLATES["evidence"] = """---
type: evidence
client: "{client}"
---
# Evidence Log: {client}

Screenshots live in `img/`, raw pastes in `raw/`. Entries appended by d1tto.
"""

TEMPLATES["report"] = """---
type: report
client: "{client}"
status: draft
---
# {client}: Penetration Test Report (draft)

## Executive Summary

## Scope & Methodology

## Findings Summary
```dataview
TABLE severity, cvss, status FROM "04_Findings" SORT cvss DESC
```

## Detailed Findings
<!-- embed: ![[F01_Example]] -->

## Remediation Roadmap
"""

TEMPLATES["daylog"] = """---
type: daylog
client: "{client}"
date: {date}
tester: "{tester}"
---
# {date}: {client}

"""

TEMPLATES["host"] = """---
type: host
client: "{client}"
ip: "{ip}"
hostname: "{hostname}"
os: 
status: discovered
first_seen: {date}
tags: [host]
---
# {ip} {hostname}

Source: {source}

## Ports / Services
| Port | Proto | Service | Version | Notes |
|------|-------|---------|---------|-------|

## Enumeration

## Access / Foothold

## Findings on this host
"""

TEMPLATES["finding"] = """---
type: finding
id: {num}
client: "{client}"
title: "{title}"
severity: {severity}
cvss: 
cvss_vector: 
status: open
found: {date}
tester: "{tester}"
tags: [finding, {severity}]
---
# {num}: {title}

**Severity:** {severity}  **CVSS:** 

## Affected Assets
- 

## Description

## Proof of Concept
<!-- paste evidence embeds here: ![[20260903-101500_login_bypass.png]] -->

## Impact

## Remediation
- **Short term:** 
- **Long term:** 

## References
- 
"""


def render(name: str, ctx: dict) -> str:
    """format() but tolerant of missing keys (leaves them blank)."""
    class _Safe(dict):
        def __missing__(self, k):
            return ""
    return TEMPLATES[name].format_map(_Safe(ctx))
