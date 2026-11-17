"""Record immutable image pairs from the first catalogue CI run (one-time only).

Each byte stream is checked against Git commit 6fffdb4 before SHA256 provenance
is written. The collector later binds only matching SKUs confirmed in a new
public listing. This is not part of daily catalogue refreshes.
"""
import hashlib
import importlib.util
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("catalog18", ROOT / "scripts/collect-catalog18.py")
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)


def main():
    commit = subprocess.check_output(["git", "rev-parse", "6fffdb4^{commit}"], cwd=ROOT, text=True).strip()
    raw = subprocess.check_output(["git", "ls-tree", "-r", "--format=%(objectname) %(path)", commit, "--", "tights-guide/assets/catalog"], cwd=ROOT, text=True)
    blobs = dict((path, object_id) for object_id, path in (line.split(" ", 1) for line in raw.splitlines()))
    Image, _ = catalog.pillow_runtime()
    rows = []
    for path in sorted((ROOT / "tights-guide/assets/catalog").glob("*.webp")):
        if not re.fullmatch(r"loretta-[0-9]+", path.stem):
            continue
        thumb = path.with_name(path.stem + "-320.webp")
        pair = []
        for photo in (path, thumb):
            relative = photo.relative_to(ROOT).as_posix()
            body = photo.read_bytes()
            blob_hash = hashlib.sha1(b"blob " + str(len(body)).encode("ascii") + b"\0" + body).hexdigest()
            if blobs.get(relative) != blob_hash:
                raise ValueError(f"File differs from the first CI commit: {relative}")
            pair.append((hashlib.sha256(body).hexdigest(), blob_hash))
        size = catalog.existing_image_size(path, thumb, Image)
        if not size:
            raise ValueError(f"Invalid first-run image pair: {path.name}")
        rows.append({"id": path.stem, "image": path.relative_to(ROOT / "tights-guide").as_posix(), "thumbnail": thumb.relative_to(ROOT / "tights-guide").as_posix(), "width": size[0], "height": size[1], "sha256": pair[0][0], "thumbnailSha256": pair[1][0], "gitBlob": pair[0][1], "thumbnailGitBlob": pair[1][1]})
    output = {"version": 1, "purpose": "one-time-initial-ci-image-adoption", "createdAt": catalog.utc_now(), "provenance": {"githubRunId": "44085884185", "gitCommit": commit, "evidence": "Public Loretta photographs downloaded and optimized by the first catalogue CI. Each local file matches the Git blob committed by that run. Its JSON/URL manifest was not retained after timeout; source URLs will be bound explicitly by SKU and source product ID from the next successful listing."}, "count": len(rows), "items": rows}
    target = ROOT / "qa/catalog18-import/initial-images-manifest.json"
    catalog.atomic_json(target, output)
    print(f"Verified {len(rows)} immutable first-CI image pairs; wrote {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
