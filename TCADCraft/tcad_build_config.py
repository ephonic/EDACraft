"""Build configuration that can be read without importing the native package."""
import os


CONSTANTS_PROFILES = ("si", "legacy-charge")


def constants_profile(environ=None):
    env = os.environ if environ is None else environ
    profile = env.get("TCAD_CONSTANTS_PROFILE", "si")
    if profile not in CONSTANTS_PROFILES:
        raise ValueError(
            "TCAD_CONSTANTS_PROFILE must be 'si' or 'legacy-charge'; "
            f"got {profile!r}"
        )
    return profile


def build_cache_tag(force_long_double, profile):
    constants_profile({"TCAD_CONSTANTS_PROFILE": profile})
    return ("long-double" if force_long_double else "quad") + "-" + profile
