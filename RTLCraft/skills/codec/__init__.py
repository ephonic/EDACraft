"""
skills.codec — Codec Skills (backward-compat shim)

Re-exports from skills.codec.video for backward compatibility.
"""
from skills.codec.video import (
    H265EncoderModel,
    CTUState,
    Xk265SuiteModel,
    Codec_Model,
    CodecArchParams,
    CodecArchTemplate,
    BaselineCodecTemplate,
    HighPerfCodecTemplate,
    LowPowerCodecTemplate,
    get_template,
    list_templates,
    register_template,
    register_codec_skeleton_steps,
    register_xk265_skeleton_steps,
    build_xk265_arch,
)

__all__ = [
    "H265EncoderModel", "CTUState", "Xk265SuiteModel",
    "Codec_Model", "CodecArchParams", "CodecArchTemplate",
    "BaselineCodecTemplate", "HighPerfCodecTemplate", "LowPowerCodecTemplate",
    "get_template", "list_templates", "register_template",
    "register_codec_skeleton_steps", "register_xk265_skeleton_steps",
    "build_xk265_arch",
]
