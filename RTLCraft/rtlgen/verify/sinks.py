"""Reusable trace sinks for streaming verification."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import TextIO

from rtlgen.verify.directed import TraceSample


class JsonlTraceSink:
    """Append sampled trace points as JSON lines."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle: TextIO = self.path.open("w", encoding="utf-8")

    def __call__(self, sample: TraceSample) -> None:
        self._handle.write(json.dumps(asdict(sample), separators=(",", ":")))
        self._handle.write("\n")

    def close(self) -> None:
        self._handle.close()


class CsvTraceSink:
    """Append sampled trace points as a flat CSV record."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle: TextIO = self.path.open("w", encoding="utf-8")
        self._handle.write("cycle,inputs_json,outputs_json,expected_json\n")

    def __call__(self, sample: TraceSample) -> None:
        fields = [
            str(sample.cycle),
            json.dumps(sample.inputs, separators=(",", ":")),
            json.dumps(sample.outputs, separators=(",", ":")),
            json.dumps(sample.expected, separators=(",", ":")),
        ]
        escaped = ['"' + field.replace('"', '""') + '"' for field in fields]
        self._handle.write(",".join(escaped))
        self._handle.write("\n")

    def close(self) -> None:
        self._handle.close()
