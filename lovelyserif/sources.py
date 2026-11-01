"""Fetch and verify the upstream fonts (SIL OFL 1.1)."""
from __future__ import annotations

import hashlib
import os
import sys
import urllib.request

SOURCES = {
    "NanumMyeongjo-Regular.ttf": {
        "url": "https://raw.githubusercontent.com/google/fonts/main/ofl/nanummyeongjo/NanumMyeongjo-Regular.ttf",
        "sha256": "7ed9e8653a8ed04285d51dc343ffea6eb3d9c73afc27383ea8929ee4ffd03205",
        "license": "licenses/OFL-NanumMyeongjo.txt",
    },
    "NanumMyeongjo-Bold.ttf": {
        "url": "https://raw.githubusercontent.com/google/fonts/main/ofl/nanummyeongjo/NanumMyeongjo-Bold.ttf",
        "sha256": "bc9ed8e60d93fe6db054b8fb988481b625f2eef8cb2317ad0e9834681b8fe3f3",
        "license": "licenses/OFL-NanumMyeongjo.txt",
    },
    "NotoSerifJP-Regular.otf": {
        "url": "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Serif/SubsetOTF/JP/NotoSerifJP-Regular.otf",
        "sha256": "2c9a12dbd4f2408c4610c7ee84a108b62d7236c3775baed618c64d9cb44b2f04",
        "license": "licenses/OFL-NotoSerifCJK.txt",
    },
    "NotoSerifJP-Medium.otf": {
        "url": "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Serif/SubsetOTF/JP/NotoSerifJP-Medium.otf",
        "sha256": "f3a906cadd27f812a8b4b18618fa750928e65339fb372bd3f825f24e3271180b",
        "license": "licenses/OFL-NotoSerifCJK.txt",
    },
}
LICENSE_URLS = {
    "licenses/OFL-NanumMyeongjo.txt": "https://raw.githubusercontent.com/google/fonts/main/ofl/nanummyeongjo/OFL.txt",
    "licenses/OFL-NotoSerifCJK.txt": "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Serif/LICENSE",
}


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(dest_dir: str, names=None, verify: bool = True) -> None:
    os.makedirs(dest_dir, exist_ok=True)
    for name, meta in SOURCES.items():
        if names and name not in names:
            continue
        path = os.path.join(dest_dir, name)
        if os.path.exists(path) and sha256(path) == meta["sha256"]:
            print(f"ok      {name}")
            continue
        print(f"fetch   {name}")
        urllib.request.urlretrieve(meta["url"], path)
        digest = sha256(path)
        if verify and digest != meta["sha256"]:
            raise SystemExit(f"checksum mismatch for {name}: {digest}")
        print(f"verified {name}")


def verify(dest_dir: str, names=None) -> bool:
    ok = True
    for name, meta in SOURCES.items():
        if names and name not in names:
            continue
        path = os.path.join(dest_dir, name)
        if not os.path.exists(path):
            print(f"missing {name}"); ok = False; continue
        if sha256(path) != meta["sha256"]:
            print(f"BAD     {name}"); ok = False
        else:
            print(f"ok      {name}")
    return ok


if __name__ == "__main__":
    fetch(sys.argv[1] if len(sys.argv) > 1 else "sources/upstream")
