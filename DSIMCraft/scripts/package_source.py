#!/usr/bin/env python3
"""Package the compiler, tests and tool dependencies for a clean Linux build."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ['CMakeLists.txt', 'cmake', 'README.md', 'CONTRIBUTING.md', 'src', 'include', 'parsers', 'tests', 'scripts',
          'experiments/waveform/dwf.py', 'docs']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    for name in INPUTS:
        source = ROOT / name
        if output == source or (source.is_dir() and source in output.parents):
            parser.error('output must be outside packaged source directories')
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = {}

    def clean(info):
        parts = Path(info.name).parts
        if any(p == '__pycache__' or p == '.DS_Store' or p.startswith('._') for p in parts) or info.name.endswith('.pyc'):
            return None
        info.pax_headers = {}
        if info.isfile():
            manifest[info.name] = hashlib.sha256((ROOT / info.name).read_bytes()).hexdigest()
        return info

    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        archive = Path(temporary) / 'source.tar.gz'
        with tarfile.open(archive, 'w:gz') as package:
            for name in INPUTS:
                package.add(ROOT / name, arcname=name, filter=clean)
            data = (json.dumps(dict(schema='dsim.source.v1', files=manifest), indent=2) + '\n').encode()
            info = tarfile.TarInfo('dsim-source-manifest.json')
            info.size = len(data)
            package.addfile(info, io.BytesIO(data))
        archive.replace(output)
    print(f'{output}: {len(manifest)} source files, sha256={hashlib.sha256(output.read_bytes()).hexdigest()}')


if __name__ == '__main__':
    main()
