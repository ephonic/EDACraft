"""The loaded binary owns its charge identity, even after build-env changes."""
from decimal import Decimal, localcontext
import os
import pytest
from tcad.core import native_constants, native_precision, require_constants_profile
from tcad_build_config import constants_profile, build_cache_tag


def test_binary_constants_are_not_runtime_environment_settings(monkeypatch):
    info = native_constants()
    expected = os.environ.get("TCAD_EXPECT_CONSTANTS_PROFILE")
    if expected:
        assert info["profile"] == expected
    assert info["profile"] in ("si", "legacy-charge")
    monkeypatch.setenv("TCAD_CONSTANTS_PROFILE", "legacy-charge" if info["profile"] == "si" else "si")
    assert native_constants() == info
    info["profile"] = "corrupted"
    assert native_constants()["profile"] != "corrupted"


def test_compiled_charge_matches_its_definition_at_native_precision():
    info = native_constants()
    with localcontext() as ctx:
        ctx.prec = 80
        expected = Decimal("1.602192e-19" if info["profile"] == "legacy-charge" else "1.602176634e-19")
        assert Decimal(info["elementary_charge_definition_C"]) == expected
        assert abs(Decimal(info["elementary_charge_C"]) / expected - 1) < Decimal(2) ** (1-native_precision()["mantissa_bits"])
    assert info["scope"] == "shared_QE_only"
    assert info["all_model_constants_profiled"] is False
    assert info["boltzmann_definition_J_K"] == "1.380649e-23"
    assert info["vacuum_permittivity_definition_F_m"] == "8.854187817e-12"


def test_wrong_binary_profile_is_rejected():
    profile = native_constants()["profile"]
    assert require_constants_profile(profile) == native_constants()
    with pytest.raises(RuntimeError, match="constants profile mismatch"):
        require_constants_profile("legacy-charge" if profile == "si" else "si")
    with pytest.raises(ValueError):
        require_constants_profile("sentaurus")


def test_defaults_and_all_cache_dimensions_are_distinct():
    assert constants_profile({}) == "si"
    assert len({build_cache_tag(p, c) for p in (False, True) for c in ("si", "legacy-charge")}) == 4


@pytest.mark.parametrize("invalid", ["", "SI", "sentaurus", "../si", "legacy", " si"])
def test_unknown_build_profiles_fail_closed(invalid):
    with pytest.raises(ValueError, match="TCAD_CONSTANTS_PROFILE"):
        constants_profile({"TCAD_CONSTANTS_PROFILE": invalid})
