import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "py"))
sys.path.insert(0, str(ROOT))

import mom._mom as M  # noqa: E402
from routed_case_solver import (  # noqa: E402
    _conductor_loss_geometry_scale,
    _default_full_route_retry_floor,
    _metal_thickness_by_ads_layer,
    _resolve_full_route_port_style,
    _should_try_high_mag_cluster_port,
    _should_try_terminal_extra_retry,
)


def test_finite_thickness_copper_surface_impedance_8ghz():
    zs = M.conductor_surface_impedance(2.0 * math.pi * 8.0e9, 58.0e6, 1.5e-6)

    assert zs.real > 0.0
    assert zs.imag > 0.0
    assert abs(zs.real - 0.0222170172) < 1e-8
    assert abs(zs.imag - 0.0234697232) < 1e-8


def test_full_route_retry_floor_is_length_aware():
    assert _default_full_route_retry_floor(780e-6) == 0.90
    assert _default_full_route_retry_floor(2100e-6) == 0.75

    mid = _default_full_route_retry_floor(1450e-6)
    assert 0.75 < mid < 0.90
    assert abs(mid - 0.825) < 1e-12


def test_terminal_extra_retry_only_for_clear_floor_miss():
    assert _should_try_terminal_extra_retry(0.78, 0.85)
    assert not _should_try_terminal_extra_retry(0.84, 0.85)
    assert not _should_try_terminal_extra_retry(0.40, 0.0)


def test_high_mag_cluster_retry_is_limited_to_long_cell_ports():
    assert _should_try_high_mag_cluster_port(0.90, 2.1e-3, "cell_unsigned_w135_030_135")
    assert not _should_try_high_mag_cluster_port(0.86, 2.1e-3, "cell_unsigned_w135_030_135")
    assert not _should_try_high_mag_cluster_port(0.90, 1.5e-3, "cell_unsigned_w135_030_135")
    assert not _should_try_high_mag_cluster_port(0.90, 2.1e-3, "local_unsigned_cluster2")


def test_auto_full_route_port_style_uses_cluster_only_for_long_launch_stub():
    assert (
        _resolve_full_route_port_style(
            "auto",
            total_length_m=2.1e-3,
            start_stub_um=150.0,
            end_stub_um=20.0,
        )
        == "cluster"
    )
    assert (
        _resolve_full_route_port_style(
            "auto",
            total_length_m=1.5e-3,
            start_stub_um=200.0,
            end_stub_um=20.0,
        )
        == "cell"
    )
    assert (
        _resolve_full_route_port_style(
            "auto",
            total_length_m=0.8e-3,
            start_stub_um=10.0,
            end_stub_um=8.0,
        )
        == "cell"
    )
    assert (
        _resolve_full_route_port_style(
            "auto",
            total_length_m=0.8e-3,
            start_stub_um=10.0,
            end_stub_um=8.0,
            auto_short_max_length_um=900.0,
            auto_short_max_stub_um=12.0,
        )
        == "cluster"
    )
    assert (
        _resolve_full_route_port_style(
            "auto",
            total_length_m=0.8e-3,
            start_stub_um=16.0,
            end_stub_um=8.0,
        )
        == "cell"
    )
    assert (
        _resolve_full_route_port_style(
            "cell",
            total_length_m=2.1e-3,
            start_stub_um=150.0,
            end_stub_um=20.0,
        )
        == "cell"
    )


def test_rectangular_perimeter_loss_scale_uses_width_and_thickness():
    scale = _conductor_loss_geometry_scale(2.0, 1.5)
    assert abs(scale - (2.0 / (2.0 * (2.0 + 1.5)))) < 1e-12


def test_substrate_copper_thickness_lookup(tmp_path):
    substrate = tmp_path / "substrate.subst"
    substrate.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<Substrate>
  <layer layer="41" materialname="copper" thick="1.5" thickunit="micron"/>
  <layer layer="43" materialname="copper" thick="1.5" thickunit="micron"/>
  <layer layer="45" materialname="copper" thick="1.5" thickunit="micron"/>
</Substrate>
""",
        encoding="utf-8",
    )
    thickness = _metal_thickness_by_ads_layer(str(substrate))
    assert thickness[41] == 1.5
    assert thickness[43] == 1.5
    assert thickness[45] == 1.5
