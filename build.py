"""Rebuildable dependency-free portable OS bundles. Does not install anything."""
import argparse
import hashlib
import shutil
import tempfile
import zipapp
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERSION = "1.0.0"


def archive(folder, destination):
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                z.write(path, path.relative_to(folder.parent))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT/"dist")
    out = parser.parse_args().out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="prediction-cli-build-") as temporary:
        temporary = Path(temporary)
        app = temporary/"app"
        app.mkdir()
        shutil.copytree(ROOT/"prediction_cli", app/"prediction_cli", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (app/"__main__.py").write_text("from prediction_cli.cli import main\nraise SystemExit(main())\n", encoding="utf-8")
        pyz = out/"prediction-cli.pyz"
        zipapp.create_archive(app, pyz, interpreter="/usr/bin/env python3", compressed=True)
        pyz.chmod(0o755)
        for platform in ("macos", "linux", "windows"):
            folder = temporary/f"prediction-cli-{platform}"
            folder.mkdir()
            shutil.copy2(pyz, folder/pyz.name)
            for name in ("README.md", "LICENSE"):
                shutil.copy2(ROOT/name, folder/name)
            launchers = ("Prediction CLI.cmd",) if platform == "windows" else ("Prediction CLI.command", "prediction-cli")
            for name in launchers:
                shutil.copy2(ROOT/"launchers"/name, folder/name)
                if platform != "windows":
                    (folder/name).chmod(0o755)
            archive(folder, out/f"prediction-cli-{VERSION}-{platform}-portable.zip")
        folder = temporary/"prediction-cli-source"
        folder.mkdir()
        for name in ("prediction_cli", "tests", "examples", "launchers"):
            shutil.copytree(ROOT/name, folder/name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for name in ("README.md", "LICENSE", "build.py", ".gitignore"):
            shutil.copy2(ROOT/name, folder/name)
        archive(folder, out/f"prediction-cli-{VERSION}-source.zip")
    files = [p for p in sorted(out.iterdir()) if p.is_file() and p.suffix in (".pyz", ".zip")]
    (out/"SHA256SUMS.txt").write_text("".join(hashlib.sha256(p.read_bytes()).hexdigest()+"  "+p.name+"\n" for p in files), encoding="ascii")
    for path in files:
        print(path)


if __name__ == "__main__":
    main()
