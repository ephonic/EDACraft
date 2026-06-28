"""Tests for reusable tool utilities."""
from __future__ import annotations

from pathlib import Path

from src.tools.utils import gds, netlist, paths, port_labels


def test_resolve_routed_gds_prefers_artifact(tmp_path: Path) -> None:
    """resolve_routed_gds honors recorded artifacts."""
    gds_path = tmp_path / "finish" / "out" / "chip.gds"
    gds_path.parent.mkdir(parents=True)
    gds_path.write_text("gds")
    result = paths.resolve_routed_gds("chip", work_root=tmp_path, artifacts={"routed_gds": str(gds_path)})
    assert result == gds_path.resolve()


def test_resolve_routed_gds_falls_back_to_candidates(tmp_path: Path) -> None:
    """resolve_routed_gds searches conventional candidates."""
    gz = tmp_path / "finish" / "out" / "chip.gds.gz"
    gz.parent.mkdir(parents=True)
    gz.write_text("gz")
    result = paths.resolve_routed_gds("chip", work_root=tmp_path)
    assert result == gz.resolve()


def test_resolve_sdc_file_explicit(tmp_path: Path) -> None:
    """resolve_sdc_file returns the explicitly configured SDC if present."""
    sdc = tmp_path / "constraints.sdc"
    sdc.write_text("create_clock -period 2.0 clk")
    result = paths.resolve_sdc_file(str(sdc), "chip", work_root=tmp_path)
    assert result == sdc.resolve()


def test_generate_port_labels_from_def_with_route(tmp_path: Path) -> None:
    """DEF route segments are converted to text labels."""
    def_text = """VERSION 5.8 ;
UNITS DISTANCE MICRONS 1000 ;
NETS 1 ;
- in1
  ( PIN in1 )
  ( U1 A )
  + ROUTED M2 60 ( 10000 20000 30 ) ( * 25000 30 )
  + USE SIGNAL ;
END NETS
END DESIGN
"""
    def_file = tmp_path / "test.def"
    def_file.write_text(def_text)
    labels = port_labels.generate_port_labels_from_def(def_file, {"in1"})
    assert "in1" in labels
    layer, x, y = labels["in1"]
    assert layer == 132  # M2 text layer
    assert x == 10.0
    assert y == 20.0


def test_generate_port_labels_from_def_pin_offset(tmp_path: Path) -> None:
    """Unrouted pins use std-cell GDS pin offsets."""
    # Minimal GDS with one cell, pin A on layer 131 at (0.1, 0.2).
    import struct
    cell_name = b"INV\x00"
    text_str = b"A\x00"
    # GDS record: 2-byte length (incl. 4-byte header), 1-byte type,
    # 1-byte data type, payload.
    def rec(rtype, payload, dtype: int = 0):
        return struct.pack(">H", 4 + len(payload)) + bytes([rtype, dtype]) + payload

    data = rec(0x02, b"")  # HEADER (version)
    data += rec(0x05, b"")  # BGNSTR (no date fields for peek simplicity)
    data += rec(0x06, cell_name)  # STRNAME
    data += rec(0x0C, b"")       # TEXT
    data += rec(0x0D, struct.pack(">H", 131))  # LAYER
    data += rec(0x10, struct.pack(">ii", 100, 200))  # XY
    data += rec(0x19, text_str)  # STRING
    data += rec(0x11, b"")       # ENDEL
    gds_file = tmp_path / "lib.gds"
    gds_file.write_bytes(data)

    def_text = """VERSION 5.8 ;
UNITS DISTANCE MICRONS 1000 ;
COMPONENTS 1 ;
- U1 INV + PLACED ( 5000 6000 ) N ;
END COMPONENTS
NETS 1 ;
- in1
  ( PIN in1 )
  ( U1 A )
  + USE SIGNAL ;
END NETS
END DESIGN
"""
    def_file = tmp_path / "test.def"
    def_file.write_text(def_text)
    labels = port_labels.generate_port_labels_from_def(def_file, {"in1"}, std_gds=gds_file)
    assert "in1" in labels
    layer, x, y = labels["in1"]
    assert layer == 131
    assert x == 5.1
    assert y == 6.2


def test_strip_vt_suffix() -> None:
    """VT suffix stripping handles known suffixes."""
    assert netlist.strip_vt_suffix("AOI22D0BWP30P140UHVT") == ("AOI22D0BWP30P140", "UHVT")
    assert netlist.strip_vt_suffix("AOI22D0BWP30P140") == ("AOI22D0BWP30P140", None)


def test_filter_physical_only_cells(tmp_path: Path) -> None:
    """Physical-only cell instances are removed from SPICE."""
    spice = tmp_path / "net.sp"
    spice.write_text(
        "XU1 A Y VDD VSS INV\n"
        "XFILL1 VSS VSS FILL1BWP30P140\n"
        "XTAP1 VSS TAPCELLBWP30P140\n"
    )
    netlist.filter_physical_only_cells(spice)
    text = spice.read_text()
    assert "XU1" in text
    assert "XFILL1" not in text
    assert "XTAP1" not in text


def test_write_port_labels(tmp_path: Path) -> None:
    """write_port_labels produces sorted name-layer-x-y output."""
    out = tmp_path / "labels.txt"
    labels = {
        "B": (132, 2.0, 3.0),
        "A": (131, 1.0, 2.0),
    }
    port_labels.write_port_labels(labels, out)
    lines = out.read_text().splitlines()
    assert lines == ["A 131 1.000000 2.000000", "B 132 2.000000 3.000000"]


def test_parse_std_cell_pin_offsets_skips_metadata(tmp_path: Path) -> None:
    """Only pin-text layers are collected; metadata text is ignored."""
    import struct

    def rec(rtype, payload, dtype: int = 0):
        return struct.pack(">H", 4 + len(payload)) + bytes([rtype, dtype]) + payload

    data = rec(0x02, b"")  # HEADER
    data += rec(0x05, b"")  # BGNSTR
    data += rec(0x06, b"INV\x00")
    # Metadata text on layer 3 should be ignored
    data += rec(0x0C, b"")
    data += rec(0x0D, struct.pack(">H", 3))
    data += rec(0x10, struct.pack(">ii", 0, 0))
    data += rec(0x19, b"& Vendor\x00")
    data += rec(0x11, b"")
    # Pin label on layer 131
    data += rec(0x0C, b"")
    data += rec(0x0D, struct.pack(">H", 131))
    data += rec(0x10, struct.pack(">ii", 100, 200))
    data += rec(0x19, b"A\x00")
    data += rec(0x11, b"")
    gds_file = tmp_path / "lib.gds"
    gds_file.write_bytes(data)

    offsets, bboxes = gds.parse_std_cell_pin_offsets(gds_file)
    assert offsets == {"INV": {"A": (131, 0.1, 0.2)}}
    # No boundary/path shapes in this minimal file, so bboxes remain empty.
