"""Tests for configuration loader."""
import json
import tempfile
from pathlib import Path

import yaml

from src.config.loader import load_config, save_config
from src.db.design_state import DesignConfig


def test_load_config_basic():
    """Test loading a basic YAML config."""
    config_data = {
        "design": {
            "name": "test_design",
            "top_module": "top",
            "clock_period_ns": 5.0,
            "clock_name": "sys_clk",
            "die_width_um": 1000.0,
            "die_height_um": 1000.0,
        },
        "pdk": {
            "name": "tsmc28hpcp",
            "tech_file": "/path/to/tech.tf",
        },
        "libraries": {
            "std_cell_libs": ["/path/to/lib1.db"],
            "ndm_libs": ["/path/to/lib1.ndm"],
        },
        "rtl": {
            "files": ["/path/to/rtl/top.v"],
        },
        "flow": {
            "work_root": "./test_work",
            "dry_run": True,
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        config_path = f.name

    config, flow_opts = load_config(config_path)

    assert config.design_name == "test_design"
    assert config.top_module == "top"
    assert config.clock_period_ns == 5.0
    assert config.clock_name == "sys_clk"
    assert config.die_width_um == 1000.0
    assert config.pdk.name == "tsmc28hpcp"
    assert config.pdk.tech_file == "/path/to/tech.tf"
    assert len(config.libraries.std_cell_libs) == 1
    assert flow_opts["work_root"] == "./test_work"
    assert flow_opts["dry_run"] is True

    Path(config_path).unlink()


def test_save_and_reload_config():
    """Test round-trip save and load."""
    config = DesignConfig(
        design_name="roundtrip_test",
        clock_period_ns=3.33,
        die_width_um=500.0,
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        config_path = f.name

    save_config(config, config_path, {"work_root": "./rt_work"})
    loaded_config, flow_opts = load_config(config_path)

    assert loaded_config.design_name == "roundtrip_test"
    assert loaded_config.clock_period_ns == 3.33
    assert loaded_config.die_width_um == 500.0
    assert flow_opts["work_root"] == "./rt_work"

    Path(config_path).unlink()


def test_load_config_defaults():
    """Test that missing fields get sensible defaults."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"design": {"name": "minimal"}}, f)
        config_path = f.name

    config, flow_opts = load_config(config_path)

    assert config.design_name == "minimal"
    assert config.clock_period_ns == 10.0  # default
    assert config.pdk.name == "tsmc28hpcp"  # default
    assert flow_opts["dry_run"] is False

    Path(config_path).unlink()
