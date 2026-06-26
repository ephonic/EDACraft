"""Tests for report parsers."""
import tempfile
from pathlib import Path

from src.parsers.dc_parser import DCReportParser, DCQoRResult
from src.parsers.icc2_parser import ICC2ReportParser, ICC2StageResult
from src.parsers.calibre_parser import CalibreReportParser, DRCResult, LVSResult


# ---- DC Parser Tests ----

SAMPLE_QOR = """
  Timing Path Group 'clk'
  -----------------------------------
  Levels of Logic:             24
  Critical Path Slack:         -0.123
  Critical Path Clk Period:    2.000
  Total Negative Slack:        -1.456

  timing    -0.123    -1.456
  area       12345.678

  Number of cells:     5432
  Number of nets:      6789
"""

SAMPLE_TIMING = """
Startpoint: reg_a (rising edge-triggered flip-flop)
Endpoint: reg_b (rising edge-triggered flip-flop)
Path Group: clk

  data arrival time                       2.156
  data required time                      2.000
  -----------------------------------
  slack (VIOLATED)                       -0.156

Startpoint: reg_c (rising edge-triggered flip-flop)
Endpoint: reg_d (rising edge-triggered flip-flop)
Path Group: clk

  data arrival time                       1.900
  data required time                      2.000
  -----------------------------------
  slack (MET)                             0.100
"""

SAMPLE_AREA = """
Total cell area:   12345.678
Total area:        25000.000
Combinational cell count:     3000
Sequential cell count:        1200
"""

SAMPLE_POWER = """
                          Leakage    Dynamic    Short     Total
                          Power      Power      Circuit   Power
  Total                   0.500      2.300      0.100     2.900
"""


def test_dc_qor_parser():
    result = DCQoRResult()
    parser = DCReportParser("/tmp")
    parser.parse_qor(SAMPLE_QOR, result)
    assert result.wns_setup == -0.123
    assert result.tns_setup == -1.456
    assert result.cell_area == 12345.678
    assert result.num_endpoints == 0  # not in sample


def test_dc_timing_parser():
    result = DCQoRResult()
    parser = DCReportParser("/tmp")
    parser.parse_timing(SAMPLE_TIMING, result, is_setup=True)
    assert result.wns_setup is not None
    assert result.wns_setup < 0
    assert result.num_setup_violations == 1


def test_dc_area_parser():
    result = DCQoRResult()
    parser = DCReportParser("/tmp")
    parser.parse_area(SAMPLE_AREA, result)
    assert result.cell_area == 12345.678
    assert result.num_comb_cells == 3000
    assert result.num_seq_cells == 1200


def test_dc_power_parser():
    result = DCQoRResult()
    parser = DCReportParser("/tmp")
    parser.parse_power(SAMPLE_POWER, result)
    assert result.leakage_power is not None
    assert result.dynamic_power is not None
    assert result.total_power is not None


# ---- ICC2 Parser Tests ----

SAMPLE_ICC2_TIMING = """
Path Group: reg2reg
  slack (VIOLATED)                       -0.234

Path Group: input
  slack (MET)                             0.567
"""


def test_icc2_timing_parser():
    result = ICC2StageResult()
    parser = ICC2ReportParser("/tmp", stage_name="test")
    parser.parse_timing(SAMPLE_ICC2_TIMING, result)
    assert result.wns == -0.234
    assert result.num_violating_paths == 1


# ---- Calibre Parser Tests ----

SAMPLE_DRC_SUMMARY = """
DRC Summary Report
==================
Total DRC Errors: 42

M1.1 : 10
M2.3 : 15
M3.2 : 7
VIA1.1 : 10
"""

SAMPLE_LVS_REPORT = """
LVS Comparison Report
=====================
Layout device count: 12345
Source device count: 12345
Layout net count: 10000
Source net count: 10000

CORRECT

Total ERC Errors: 0
"""


def test_calibre_drc_parser():
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "drc_summary.rpt").write_text(SAMPLE_DRC_SUMMARY)
        parser = CalibreReportParser(tmpdir)
        result = parser.parse_drc()
        assert result.total_errors == 42
        assert result.is_clean is False
        assert len(result.errors_by_rule) > 0


def test_calibre_drc_clean():
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "drc_summary.rpt").write_text(
            "Total DRC Errors: 0\n"
        )
        parser = CalibreReportParser(tmpdir)
        result = parser.parse_drc()
        assert result.is_clean is True
        assert result.total_errors == 0


def test_calibre_lvs_parser():
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "lvs_report.rpt").write_text(SAMPLE_LVS_REPORT)
        parser = CalibreReportParser(tmpdir)
        result = parser.parse_lvs()
        assert result.is_clean is True
        assert result.layout_device_count == 12345
        assert result.source_device_count == 12345
