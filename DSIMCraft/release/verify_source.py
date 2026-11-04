#!/usr/bin/env python3
"""Check release checksums and unchanged, pinned upstream source files."""

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    root = parser.parse_args().root.resolve()
    try:
        expected = {}
        for line in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
            digest, name = line.split("  ", 1)
            path = Path(name)
            if path.is_absolute() or ".." in path.parts or name in expected:
                raise ValueError("invalid checksum path: " + name)
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("invalid checksum: " + name)
            expected[name] = digest
        origin = json.loads((root / "SOURCE_ORIGIN.json").read_text(encoding="utf-8"))
        if not expected or len(origin["files"]) != origin["copied_files"]:
            raise ValueError("invalid or empty release manifest")
        for name, digest in origin["files"].items():
            if expected.get(name) != digest:
                raise ValueError("upstream identity differs: " + name)
        for name, digest in expected.items():
            if sha256(root / name) != digest:
                raise ValueError("checksum differs: " + name)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, "FAIL: " + str(error) + "\n")
    print("PASS: {} release files; {} unchanged upstream files at {}".format(
        len(expected), origin["copied_files"], origin["upstream_commit"]))


if __name__ == "__main__":
    main()
