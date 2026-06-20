from rtlgen_x.ppa import (
    load_implementation_report_bundle,
    parse_area_report,
    parse_power_report,
    parse_timing_report,
)


def test_parse_timing_area_and_power_reports(tmp_path):
    timing_text = "Clock period = 2.00\nWNS = -0.25\nTNS = -1.50\n"
    area_text = "Total area = 12345.0\nCombinational area = 4567.0\nSequential area = 3210.0\n"
    power_text = "Dynamic Power = 0.72\nLeakage Power = 0.08\n"

    timing = parse_timing_report(timing_text)
    area = parse_area_report(area_text)
    power = parse_power_report(power_text)

    assert timing.wns_ns == -0.25
    assert timing.tns_ns == -1.5
    assert timing.clock_period_ns == 2.0
    assert timing.fmax_mhz == 500.0
    assert timing.critical_path_ns == 2.25
    assert area.total_area == 12345.0
    assert area.combinational_area == 4567.0
    assert power.dynamic_mw == 0.72
    assert power.total_mw == 0.8

    timing_path = tmp_path / "timing.rpt"
    area_path = tmp_path / "area.rpt"
    power_path = tmp_path / "power.rpt"
    timing_path.write_text(timing_text, encoding="utf-8")
    area_path.write_text(area_text, encoding="utf-8")
    power_path.write_text(power_text, encoding="utf-8")

    bundle = load_implementation_report_bundle((timing_path, area_path, power_path))
    assert bundle.timing.wns_ns == -0.25
    assert bundle.timing.clock_period_ns == 2.0
    assert bundle.area.total_area == 12345.0
    assert bundle.power.total_mw == 0.8
    assert len(bundle.sources) == 3
