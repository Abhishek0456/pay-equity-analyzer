"""Part 8 — deterministic export manifest with SHA-256 checksums."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

def checksum(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def build_manifest(directory: str | Path) -> dict:
    root = Path(directory)
    files = [{"path": str(path.relative_to(root)).replace("\\", "/"), "sha256": checksum(path), "bytes": path.stat().st_size}
             for path in sorted(root.rglob("*")) if path.is_file() and path.name != "manifest.json"]
    return {"files": files}

def write_manifest(directory: str | Path) -> Path:
    root = Path(directory); root.mkdir(parents=True, exist_ok=True)
    target = root / "manifest.json"
    target.write_text(json.dumps(build_manifest(root), indent=2), encoding="utf-8")
    return target
