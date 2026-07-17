"""Academic-style matplotlib configuration (P4.1).

The 3rd-generation TCAD plots were reported to lack the academic style of the
2nd-generation figures (comments.docx). This module provides a centralized
``rcParams`` configuration (serif fonts, inward ticks, thin axes, compact
layout) plus a ``science()`` context manager so every published figure has a
consistent, paper-ready appearance.

Usage
-----
::

    from tcad.viz.style import set_academic_style, science

    # Global — apply once at the top of a script / notebook
    set_academic_style()

    # Or as a context manager (restores prior rcParams on exit)
    with science():
        fig, ax = plt.subplots()
        ...

The style targets the conventions of semiconductor-device journals (IEEE EDL /
TED, Applied Physics Letters): Times-like serif body, matplotlib classic colour
cycle, minor ticks on both axes, gridlines only when requested, and a font size
readable at single-column width.
"""

from __future__ import annotations
from contextlib import contextmanager
from typing import Dict, Iterator


# The rcParams applied by set_academic_style / science. Kept as a module-level
# dict so it can be inspected and partially overridden by callers.
_ACADEMIC_RCPARAMS: Dict[str, object] = {
    # --- Fonts: serif body (Times-like) ---
    "font.family": "serif",
    "font.serif": [
        "Times New Roman", "Times", "DejaVu Serif", "Liberation Serif",
        "Nimbus Roman", "serif",
    ],
    "font.size": 11,
    "mathtext.fontset": "stix",         # STIX matches Times for math labels
    "mathtext.rm": "serif",
    # --- Axes ---
    "axes.labelsize": 12,
    "axes.titlesize": 12,
    "axes.linewidth": 0.8,               # thin axis spines
    "axes.grid": False,
    "axes.grid.which": "major",
    # --- Ticks: inward-pointing, small, on all four sides ---
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.top": True,
    "ytick.right": True,
    "xtick.major.size": 4,
    "ytick.major.size": 4,
    "xtick.minor.size": 2,
    "ytick.minor.size": 2,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "xtick.minor.width": 0.6,
    "ytick.minor.width": 0.6,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "xtick.minor.visible": True,
    "ytick.minor.visible": True,
    # --- Legend ---
    "legend.fontsize": 9,
    "legend.frameon": True,
    "legend.framealpha": 1.0,
    "legend.edgecolor": "0.5",
    "legend.fancybox": False,
    # --- Lines & markers ---
    "lines.linewidth": 1.5,
    "lines.markersize": 4,
    # --- Figure / savefig ---
    "figure.figsize": (4.5, 3.2),
    "figure.dpi": 120,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.05,
    # --- Layout ---
    "figure.autolayout": True,           # tight_layout by default
}


def set_academic_style(figsize=(4.5, 3.2), fontsize=11) -> None:
    """Apply the academic rcParams globally.

    Call once near the top of a script or notebook. Subsequent figures inherit
    the serif fonts, inward ticks, thin axes, and compact layout.

    Parameters
    ----------
    figsize : tuple
        Default figure size in inches (single-column width by default).
    fontsize : int
        Base font size.
    """
    import matplotlib as mpl
    rc = dict(_ACADEMIC_RCPARAMS)
    rc["font.size"] = fontsize
    rc["figure.figsize"] = figsize
    mpl.rcParams.update(rc)


@contextmanager
def science(figsize=(4.5, 3.2), fontsize=11, grid: bool = False) -> Iterator[None]:
    """Context manager that applies academic style, restoring rcParams on exit.

    Useful when only a subset of figures in a mixed script should be styled.

    Parameters
    ----------
    figsize : tuple
        Default figure size in inches.
    fontsize : int
        Base font size.
    grid : bool
        If True, draw a light major grid (some journals prefer this).

    Examples
    --------
    >>> with science(grid=True):
    ...     fig, ax = plt.subplots()
    ...     ax.plot(V, P)
    """
    import matplotlib as mpl
    saved = dict(mpl.rcParams)
    try:
        rc = dict(_ACADEMIC_RCPARAMS)
        rc["font.size"] = fontsize
        rc["figure.figsize"] = figsize
        if grid:
            rc["axes.grid"] = True
            rc["grid.alpha"] = 0.3
            rc["grid.linewidth"] = 0.5
        mpl.rcParams.update(rc)
        yield
    finally:
        mpl.rcParams.update(saved)
