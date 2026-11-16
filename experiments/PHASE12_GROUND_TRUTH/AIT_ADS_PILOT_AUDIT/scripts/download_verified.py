"""Download only the two pinned AIT-ADS Zenodo files and verify publisher MD5."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parents[1]
RAW = HERE / "data" / "raw"
RECORD = "https://zenodo.org/api/records/8263181"
EXPECTED = {"ait_ads.zip", "labels.csv"}


def main():
    response = requests.get(RECORD, timeout=30)
    response.raise_for_status()
    record = response.json()
    license_id = record["metadata"]["license"]["id"]
    files = {f["key"]: f for f in record["files"]}
    if license_id != "cc-by-4.0" or set(files) != EXPECTED:
        raise ValueError("Zenodo license or file set changed; re-audit before download")
    if any(f["size"] > 100_000_000 for f in files.values()):
        raise ValueError("File-size gate changed")
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = {"dataset": "AIT Alert Data Set", "record": RECORD,
        "zenodo_record_id": record["id"], "zenodo_version": record["metadata"].get("version"),
        "license": license_id, "attribution": "Landauer, Skopik, Wurzenberger; AIT Alert Data Set; DOI 10.5281/zenodo.8263181",
        "missing_dependencies": [
            "AIT-LDSv2 original labeled source logs (approximately 130.6 GB packed; not downloaded)",
            "AIT-NDS original netflows (size not established in this audit; not downloaded)"],
        "files": []}
    for name in sorted(EXPECTED):
        info = files[name]
        path = RAW / name
        if path.exists():
            raise FileExistsError(path)
        md5 = hashlib.md5()
        sha = hashlib.sha256()
        size = 0
        try:
            with requests.get(info["links"]["self"], stream=True, timeout=(30, 120)) as data:
                data.raise_for_status()
                with path.open("xb") as output:
                    for chunk in data.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            size += len(chunk)
                            if size > info["size"]:
                                raise ValueError("Download exceeded published size")
                            md5.update(chunk)
                            sha.update(chunk)
                            output.write(chunk)
            if size != info["size"] or "md5:" + md5.hexdigest() != info["checksum"]:
                raise ValueError("Download size or publisher checksum mismatch")
        except Exception:
            # Keep the file for forensic inspection; do not mark it verified.
            raise
        manifest["files"].append({"name": name, "source_url": info["links"]["self"],
            "published_size_bytes": info["size"], "downloaded_size_bytes": size,
            "published_md5": info["checksum"], "verified_md5": md5.hexdigest(),
            "sha256": sha.hexdigest(), "downloaded": True,
            "downloaded_at_utc": datetime.now(timezone.utc).isoformat()})
    (HERE / "AIT_ADS_DOWNLOAD_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"status": "verified", "files": [(f["name"], f["downloaded_size_bytes"]) for f in manifest["files"]]}))


if __name__ == "__main__":
    main()
