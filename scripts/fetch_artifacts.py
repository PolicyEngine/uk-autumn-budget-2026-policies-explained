"""Download the artifacts a dashboard manifest lists, for build_figures.py.

With --manifest, reads a saved manifest (the pinned one in sources/) and fetches
its artifacts from --base-url. With --manifest-url, downloads the live manifest
first and saves it to --manifest-out. Saves each displayable or withdrawn entry's
receipt and listed files to <out>/<key>/. Files are checked against the
receipt's digests here as well as in build_figures.py.

  fetch_artifacts.py --manifest sources/manifest-rev17.json --base-url URL --out DIR
  fetch_artifacts.py --manifest-url URL --manifest-out FILE --out DIR
"""

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

KEEP = ("approved", "provisional", "withdrawn")


def get(url):
    with urllib.request.urlopen(url) as r:
        return r.read()


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--manifest", help="a saved manifest")
    src.add_argument("--manifest-url", help="download the live manifest")
    ap.add_argument("--base-url", help="where the artifacts live (default: the manifest URL's folder)")
    ap.add_argument("--manifest-out", help="with --manifest-url: where to save the manifest")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    if a.manifest:
        if not a.base_url:
            ap.error("--manifest needs --base-url")
        raw = Path(a.manifest).read_bytes()
        base = a.base_url.rstrip("/")
    else:
        if not a.manifest_out:
            ap.error("--manifest-url needs --manifest-out")
        raw = get(a.manifest_url)
        Path(a.manifest_out).write_bytes(raw)
        base = a.base_url.rstrip("/") if a.base_url else a.manifest_url.rsplit("/", 1)[0]
    m = json.loads(raw)
    for key, entry in {**m["measures"], **m["combined"]}.items():
        if entry.get("status") not in KEEP:
            continue
        folder = Path(a.out) / key
        folder.mkdir(parents=True, exist_ok=True)
        receipt = get(f"{base}/{entry['artifact']}/receipt.json")
        (folder / "receipt.json").write_bytes(receipt)
        for name, digest in json.loads(receipt)["dashboard"]["files"].items():
            blob = get(f"{base}/{entry['artifact']}/{name}")
            if hashlib.sha256(blob).hexdigest() != digest:
                raise SystemExit(f"{key}/{name}: digest differs from its receipt")
            (folder / name).write_bytes(blob)
        print(f"{key}: {entry['status']} {entry['artifact']}")
    print(f"revision {m['revision']} ({m['updated_at']})")


if __name__ == "__main__":
    main()
