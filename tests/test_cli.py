"""Receive-mode behaviour: trailing flags route to the right writer,
and anything unflagged becomes a note so a thought is never lost."""
from pathlib import Path

import pytest
from PIL import Image

from d1tto import cli
from d1tto import clipboard as clip
from d1tto.engagement import Engagement


@pytest.fixture
def eng(tmp_path):
    vault = tmp_path / "VAULT"
    (vault / ".obsidian").mkdir(parents=True)
    return Engagement.create(vault / "Engagements", "Acme Corp", "eli", "- 10.0.0.0/24")


@pytest.fixture
def fake_clip(monkeypatch):
    state = {"text": "", "image": None}
    monkeypatch.setattr(clip, "get_text", lambda: state["text"])
    monkeypatch.setattr(clip, "get_image", lambda: state["image"])
    return state


def test_unflagged_line_is_a_note(eng, fake_clip):
    cli.receive("box .5 runs an old jenkins", eng)
    assert "old jenkins" in (eng.root / "notes.md").read_text()


def test_flagword_without_payload_stays_a_note(eng, fake_clip):
    # ends in "image" but nothing is on the clipboard -> keep the whole line
    fake_clip["image"] = None
    cli.receive("grab a screenshot of the login image", eng)
    assert "login image" in (eng.root / "notes.md").read_text()


def test_image_flag_saves_clipboard_image_with_caption(eng, fake_clip):
    fake_clip["image"] = Image.new("RGB", (320, 200), (90, 40, 160))
    cli.receive("portal login page i", eng)
    imgs = list((eng.root / "05_Evidence" / "img").glob("*portal_login_page.png"))
    assert len(imgs) == 1


def test_code_flag_saves_clipboard_text_as_code(eng, fake_clip):
    fake_clip["text"] = "id\nuid=0(root)"
    cli.receive("bash c", eng)
    assert list((eng.root / "05_Evidence" / "raw").glob("*.sh"))


def test_multiword_client_name_is_preserved(tmp_path):
    vault = tmp_path / "VAULT"
    (vault / ".obsidian").mkdir(parents=True)
    engs = vault / "Engagements"
    e = Engagement.create(engs, "Acme Corp", "eli")
    # folder stays filesystem-safe, but the display name keeps the space
    assert e.root.name.endswith("_Acme_Corp")
    assert e.client == "Acme Corp"
    assert e.dashboard.name == "Acme Corp.md"
    assert 'client: "Acme Corp"' in e.dashboard.read_text()
    # reloading recovers the original name, not the slug
    assert Engagement(e.root).client == "Acme Corp"


def test_scan_flag_autocreates_nmap_hosts(eng, fake_clip):
    fake_clip["text"] = ("Nmap scan report for 10.0.0.5\n22/tcp open ssh\n"
                         "Nmap scan report for 10.0.0.9\n")
    cli.receive("nmap top1000 s", eng)
    assert list((eng.root / "02_Scans").glob("nmap_*top1000.txt"))
    hosts = {p.name for p in (eng.root / "03_Hosts").glob("*.md") if not p.name.startswith("_")}
    assert hosts == {"10.0.0.5.md", "10.0.0.9.md"}
