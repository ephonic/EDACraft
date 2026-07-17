from rtlgen.sim import RandomParityConfig, build_fuzz_templates, run_fuzz_suite


def test_fuzz_suite_runs_all_templates(tmp_path):
    report = run_fuzz_suite(
        config=RandomParityConfig(cycles=16, seed=2024),
        build_root=tmp_path / "fuzz_suite",
    )

    assert report.reports
    assert report.all_matched is True
    assert len(report.reports) == len(build_fuzz_templates())
    assert all(item.cycles == 16 for item in report.reports)
