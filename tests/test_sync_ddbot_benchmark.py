from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


def test_sync_tracks_tip_pins_commits_and_detects_drift(tmp_path: Path) -> None:
    upstream = tmp_path / "upstream"
    upstream.mkdir()

    def git(*args: str) -> str:
        return subprocess.check_output(
            ["git", "-C", str(upstream), *args], text=True
        ).strip()

    git("init", "--quiet", "--initial-branch=master")
    source = upstream / "src" / "dwis_validation"
    source.mkdir(parents=True)
    (source / "schemas.py").write_text("# first snapshot\n")
    (source / "removed.py").write_text("# removed upstream later\n")

    def commit() -> str:
        git("add", "-A")
        git("-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-qm", "snapshot")
        return git("rev-parse", "HEAD")

    first = commit()
    (source / "schemas.py").write_text("# latest snapshot\n")
    (source / "removed.py").unlink()
    (source / "added.py").write_text("# added upstream\n")
    latest = commit()

    checkout = tmp_path / "toolkit"
    scripts = checkout / "scripts"
    scripts.mkdir(parents=True)
    script = scripts / "sync_ddbot_benchmark.sh"
    shutil.copyfile(Path(__file__).resolve().parents[1] / "scripts" / script.name, script)
    subprocess.run(["git", "init", "--quiet", str(checkout)], check=True)
    env = {**os.environ, "DDBOT_BENCHMARK_URL": str(upstream)}

    def sync(*args: str, success: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["bash", str(script), *args], cwd=tmp_path, env=env,
            capture_output=True, text=True,
        )
        assert (result.returncode == 0) == success, result.stdout + result.stderr
        return result

    mirror = checkout / "model-dwis-config/scripts/ddbot_toolkit/validation"
    adapter = mirror.parent / "services.py"
    adapter.parent.mkdir(parents=True)
    adapter.write_text("# toolkit adapter\n")
    sync("--check", success=False)
    sync()
    provenance = json.loads((scripts / ".ddbot-benchmark-sync.json").read_text())
    assert provenance["sha"] == latest
    assert (mirror / "added.py").exists()
    assert not (mirror / "removed.py").exists()
    assert adapter.read_text() == "# toolkit adapter\n"

    sync(first)
    assert (mirror / "removed.py").exists()
    assert not (mirror / "added.py").exists()
    (mirror / "schemas.py").write_text("# local drift\n")
    sync("--check", success=False)
    sync(first)
    assert (mirror / "schemas.py").read_text() == "# first snapshot\n"
    upstream.rename(tmp_path / "offline-upstream")
    sync("--check")
