"""Utilities for Touchstone (.sNp) read/write."""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union
import re

import numpy as np


def write_touchstone(
    filename: Union[str, Path],
    freqs: np.ndarray,
    S: np.ndarray,
    *,
    freq_unit: str = "GHz",
    param_type: str = "S",
    fmt: str = "RI",
    z0: Union[float, complex, list, np.ndarray] = 50.0,
    comments: Optional[list] = None,
) -> Path:
    """Write a Touchstone file.

    Parameters
    ----------
    filename
        Output path.
    freqs
        Frequency array in Hz.
    S
        S-parameter array, shape (nfreq, N, N).
    """
    freqs = np.asarray(freqs, dtype=np.float64).ravel()
    S = np.asarray(S, dtype=np.complex128)
    if S.ndim != 3:
        raise ValueError(f"S must be 3D (nfreq, N, N), got shape {S.shape}")
    nfreq, nport, nport2 = S.shape
    if nport != nport2:
        raise ValueError(f"S matrix must be square, got {nport}x{nport2}")

    # Frequency scale from Hz to file unit.
    unit_factor = {"Hz": 1.0, "kHz": 1e-3, "MHz": 1e-6, "GHz": 1e-9}[freq_unit]
    freqs_scaled = freqs * unit_factor

    if np.isscalar(z0):
        z0_arr = np.full(nport, complex(z0))
    else:
        z0_arr = np.asarray([complex(x) for x in z0], dtype=complex)
        if len(z0_arr) != nport:
            raise ValueError(f"z0 length {len(z0_arr)} != nport {nport}")

    lines = []
    if comments:
        for c in comments:
            lines.append(f"! {c}")
    lines.append("! Created by mom Touchstone writer")
    lines.append("!")

    # Header: # freq_unit param_type fmt R z0
    r_is_scalar = np.allclose(z0_arr, z0_arr[0])
    z0_txt = f"{z0_arr[0].real}" if r_is_scalar else ""
    lines.append(f"# {freq_unit} {param_type} {fmt} {('R ' + z0_txt).strip()}".strip())

    def fmt_complex(z: complex) -> str:
        if fmt == "RI":
            return f"{z.real:.6e} {z.imag:.6e}"
        if fmt == "MA":
            return f"{np.abs(z):.6e} {np.angle(z, deg=True):.6f}"
        if fmt == "DB":
            mag_db = 20 * np.log10(np.abs(z) + 1e-30)
            return f"{mag_db:.6e} {np.angle(z, deg=True):.6f}"
        raise ValueError(f"Unsupported fmt {fmt!r}")

    # Writing policy:
    # - s2p: keep one-line form
    # - sNp (N > 2): keep row-based form, no strict row wrapping requirement.
    for fi in range(nfreq):
        parts = [f"{freqs_scaled[fi]:.6e}"]
        for r in range(nport):
            for c in range(nport):
                parts.append(fmt_complex(S[fi, r, c]))
        if nport <= 2:
            lines.append(" ".join(parts))
            continue

        row0 = [parts[0]] + [parts[1 + c] for c in range(nport)]
        lines.append(" ".join(row0))
        for r in range(1, nport):
            row_parts = [parts[1 + r * nport + c] for c in range(nport)]
            lines.append(" ".join(row_parts))

    path = Path(filename)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _infer_nport_from_filename(path: Path) -> Optional[int]:
    m = re.search(r"\.s(\d+)p$", path.name, re.IGNORECASE)
    if not m:
        return None
    n = int(m.group(1))
    return n if n > 0 else None


def _infer_nport_from_flat(
    flat_tokens: list[float],
    data_lines: list[list[str]],
    max_pairs_in_line: int,
) -> int:
    """Infer port count from data token count and line-wrap structure."""
    nlines = len(data_lines)
    if nlines == 0:
        return 0
    if max_pairs_in_line <= 0:
        max_pairs_in_line = 1

    total_tokens = len(flat_tokens)
    if total_tokens < 3:
        return 1 if total_tokens == 3 else 0

    max_n = int(np.sqrt((total_tokens - 1) / 2)) + 2
    candidates = []
    for n in range(1, max_n + 1):
        nvals_per_freq = 1 + 2 * n * n
        if total_tokens % nvals_per_freq != 0:
            continue
        nfreq = total_tokens // nvals_per_freq
        if nfreq < 1:
            continue
        if nlines % nfreq != 0:
            continue
        lines_per_freq = nlines // nfreq

        # Support full row-per-frequency and row-wrap formats
        wrapped_rows = n * ((n + max_pairs_in_line - 1) // max_pairs_in_line)
        if lines_per_freq not in (n, wrapped_rows):
            continue
        candidates.append(n)

    if not candidates:
        # Best effort fallback for tiny files
        return int(np.sqrt((total_tokens - 1) // 2))
    # prefer larger N when multiple candidates exist
    return max(candidates)


def read_touchstone(filename: Union[str, Path]):
    """Read Touchstone file.

    Returns
    -------
    freqs_hz : np.ndarray, shape (nfreq,)
    S : np.ndarray, shape (nfreq, N, N)
    z0 : float
    """
    path = Path(filename)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    freq_unit = "GHz"
    fmt = "RI"
    z0 = 50.0
    data_lines = []
    data_tokens_raw = []

    for line in lines:
        s = line.strip()
        if not s or s.startswith("!"):
            continue
        if s.startswith("#"):
            tokens = s[1:].split()
            for i, t in enumerate(tokens):
                tl = t.lower()
                if tl in {"hz", "khz", "mhz", "ghz"}:
                    freq_unit = {"hz": "Hz", "khz": "kHz", "mhz": "MHz", "ghz": "GHz"}[tl]
                elif tl in {"ri", "ma", "db"}:
                    fmt = tl.upper()
                elif tl == "r" and i + 1 < len(tokens):
                    z0 = float(tokens[i + 1])
            continue

        split = s.split()
        data_lines.append(split)
        data_tokens_raw.extend(split)

    if not data_lines:
        return np.zeros(0), np.zeros((0, 1, 1), complex), z0

    unit_factor = {"Hz": 1.0, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9}[freq_unit]

    # Split into numeric values, keep track of per-line pair counts.
    line_pairs = []
    for i, tokens in enumerate(data_lines):
        pair_tokens = len(tokens) - (1 if i == 0 else 0)
        if pair_tokens < 0 or pair_tokens % 2 != 0:
            raise ValueError("Invalid Touchstone format: odd numeric token count in data line.")
        line_pairs.append(pair_tokens // 2)

    max_pairs_in_line = max(line_pairs) if line_pairs else 1
    flat_tokens = [float(x) for x in data_tokens_raw]

    # Prefer explicit N from filename suffix first.
    nport = _infer_nport_from_filename(path)
    if nport is not None:
        nvals_per_freq = 1 + 2 * nport * nport
        if len(flat_tokens) % nvals_per_freq != 0:
            # fallback to structure inference if suffix is inconsistent with payload
            nport = None

    if nport is None:
        nport = _infer_nport_from_flat(flat_tokens, data_lines, max_pairs_in_line)

    if nport <= 0:
        return np.zeros(0), np.zeros((0, 1, 1), complex), z0

    nvals_per_freq = 1 + 2 * nport * nport
    if len(flat_tokens) % nvals_per_freq != 0:
        raise ValueError(
            f"Touchstone parse failed: total data tokens={len(flat_tokens)} "
            f"not divisible by 1+2*N*N for N={nport}"
        )

    nfreq = len(flat_tokens) // nvals_per_freq
    freqs = np.empty(nfreq, dtype=float)
    all_s = []
    for k in range(nfreq):
        base = k * nvals_per_freq
        freqs[k] = flat_tokens[base] * unit_factor
        cvals = []
        for j in range(nport * nport):
            x = flat_tokens[base + 1 + 2 * j]
            y = flat_tokens[base + 1 + 2 * j + 1]
            if fmt == "MA":
                cvals.append(complex(x * np.cos(np.radians(y)), x * np.sin(np.radians(y))))
            elif fmt == "DB":
                mag = 10 ** (x / 20)
                cvals.append(complex(mag * np.cos(np.radians(y)), mag * np.sin(np.radians(y))))
            else:
                cvals.append(complex(x, y))
        all_s.append(np.array(cvals, dtype=complex).reshape(nport, nport))

    S = np.array(all_s, dtype=complex) if all_s else np.zeros((0, 1, 1), complex)
    return freqs, S, z0
