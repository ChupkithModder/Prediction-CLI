"""Offline frontend and OS launcher checks. No backend or network access."""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def invoke(prefix: list[str], args: list[str], *, expect: int = 0) -> str:
    command = [*prefix, *args]
    if os.name == "nt" and prefix[0].endswith(".cmd"):
        # Only fixed test arguments and generated temporary paths reach this shell.
        proc = subprocess.run(subprocess.list2cmdline(command), shell=True, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    else:
        proc = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=30)
    if expect == 0:
        assert proc.returncode == 0, (command, proc.returncode, proc.stdout, proc.stderr)
    else:
        assert proc.returncode != 0, (command, "invalid operation incorrectly succeeded")
    return proc.stdout


def check(prefix: list[str], folder: Path) -> None:
    folder.mkdir()
    assert "Prediction CLI" in invoke(prefix, ["--version"])
    disconnected = json.loads(invoke(prefix, ["status", "--json"]))
    assert disconnected["status"] == "disconnected" and disconnected["events"] == []
    demo = json.loads(invoke(prefix, ["--demo", "status", "--json"]))
    assert demo["mode"] == "synthetic" and demo["events"]
    snapshot = folder / "snapshot.json"
    snapshot.write_text(json.dumps(demo), encoding="utf-8")
    before = snapshot.read_bytes()
    readback = json.loads(invoke(prefix, ["--snapshot", str(snapshot), "status", "--json"]))
    assert readback == demo and snapshot.read_bytes() == before
    output = folder / "events.csv"
    invoke(prefix, ["--demo", "export", "--format", "csv", "--output", str(output)])
    with output.open(encoding="utf-8-sig", newline="") as f:
        assert len(list(csv.DictReader(f))) == len(demo["events"])
    invoke(prefix, ["start"], expect=1)
    requests = folder / "requests.jsonl"
    invoke(prefix, ["--requests", str(requests), "start"])
    invoke(prefix, ["--requests", str(requests), "stop"])
    rows = [json.loads(line) for line in requests.read_text().splitlines()]
    assert [r["command"] for r in rows] == ["start", "stop"]
    assert all(r["schema"] == "prediction-cli-control-v1" for r in rows)
    invoke(prefix, ["invalid-command-for-test"], expect=1)


def main() -> None:
    for line in (DIST / "SHA256SUMS.txt").read_text().splitlines():
        digest, name = line.split("  ", 1)
        assert hashlib.sha256((DIST / name).read_bytes()).hexdigest() == digest, name
    forbidden = {"engine.py", "data.py", "adapter.py", "store.py", "core.py", "locking.py", "memory.py", "deadlines.py", "exporting.py"}
    with zipfile.ZipFile(DIST / "prediction-cli.pyz") as z:
        assert not forbidden.intersection(Path(name).name for name in z.namelist())
    system = {"Darwin": "macos", "Linux": "linux", "Windows": "windows"}[platform.system()]
    with tempfile.TemporaryDirectory(prefix="prediction-frontend-smoke-") as temp:
        temp = Path(temp)
        check([sys.executable, str(DIST / "prediction-cli.pyz")], temp / "direct")
        archive = next(DIST.glob(f"prediction-cli-*-{system}-portable.zip"))
        with zipfile.ZipFile(archive) as z:
            z.extractall(temp / "bundle")
            if os.name != "nt":
                for member in z.infolist():
                    mode = member.external_attr >> 16
                    if mode and not member.is_dir():
                        (temp / "bundle" / member.filename).chmod(mode & 0o777)
        folder = temp / "bundle" / f"prediction-cli-{system}"
        launcher = folder / ("Prediction CLI.cmd" if system == "windows" else
                             "Prediction CLI.command" if system == "macos" else "prediction-cli")
        check([str(launcher)], temp / "launcher")
    print(f"PASS: {system}/{platform.machine()} frontend pyz, launcher, demo, read-only JSON, CSV, explicit control requests, error exits, hashes, no backend modules")


if __name__ == "__main__":
    main()
