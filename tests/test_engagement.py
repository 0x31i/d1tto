from pathlib import Path
from PIL import Image
from d1tto.engagement import Engagement, list_engagements


def test_full_flow(tmp_path: Path):
    engs = tmp_path / "Engagements"
    e = Engagement.create(engs, "Acme Corp", tester="elias", scope="- 10.0.0.0/24")
    assert e.client == "Acme Corp"                 # display name keeps the space
    assert e.root.name.endswith("_Acme_Corp")      # folder stays filesystem-safe
    for f in ["00_Admin/scope.md", "05_Evidence/img", "06_Creds/creds.md", "Acme Corp.md"]:
        assert (e.root / f).exists()

    p = e.save_image(Image.new("RGB", (10, 10)), "login page")
    assert p.suffix == ".png" and "login_page" in p.name
    assert f"![[{p.name}]]" in (e.root / "05_Evidence/evidence.md").read_text()

    p = e.save_code("id\nuid=0(root)", "bash", "root shell")
    assert p.read_text().startswith("id")

    nmap = "Nmap scan report for 10.0.0.5\nNmap scan report for web (10.0.0.9)\n"
    e.save_scan(nmap, "nmap", "top1000")
    assert (e.root / "03_Hosts/10.0.0.5.md").exists()
    assert (e.root / "03_Hosts/10.0.0.9.md").exists()

    f = e.finding("SQLi in login", "high")
    assert f.name.startswith("F01_") and "severity: high" in f.read_text()
    e.cred("admin", "Winter2026!", "10.0.0.5", "sprayed")
    assert "Winter2026!" in (e.root / "06_Creds/creds.md").read_text()
    assert list_engagements(engs)[0] == e.root
    log = e.today_log.read_text()
    assert "Screenshot" in log and "Finding" in log
