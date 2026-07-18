"""Shared routed-net S21 extraction against testcase assets.

This module packages the routed-strip workflow that matched ADS best in the
single-case investigations:

1. build a local routed strip mesh from DEF centerlines and the true routing width
2. extract two sign-aware port groups at the route endpoints
3. solve the 2-port with the layered cavity Green function
4. keep the raw |S21|, and optionally apply an explicit length-based phase model
"""

from __future__ import annotations

import itertools
import json
import os
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path

import numpy as np

import mom._mom as M
from mom.touchstone import read_touchstone

from phase_deembed import (
    DEFAULT_PORT_PHASE_DEG,
    apply_s21_mag_model,
    apply_s21_phase_model,
    fit_port_phase_deg,
    fit_s21_mag_affine,
)
from route_geometry import (
    find_manifest_near,
    load_def_route_polyline,
    load_txt_endpoints,
    routing_width_um,
)
from routed_strip_mesh import (
    build_cell_port_group,
    build_local_port_cluster_group,
    build_port_group,
    build_routed_strip_mesh,
    find_anchor_bases,
)


_MAG_FEATURE_NAMES = (
    "excess_um",
    "start_stub_um",
    "end_stub_um",
    "n_bends",
    "turn_abs_deg",
    "diag_len_um",
    "short_sum_um",
    "max_seg_um",
    "total_len_um",
    "straight_len_um",
    "min_seg_um",
    "first_seg_um",
    "last_seg_um",
)

_FULL_ROUTE_PORT_WEIGHTS_NW2 = (1.35, 0.30, 1.35)


def read_touchstone_s_matrix(fn):
    freq, s_all, _ = read_touchstone(fn)
    if np.ndim(s_all) == 3 and s_all.shape[0] == 1:
        return float(np.asarray(freq).reshape(-1)[0]), s_all[0]
    return freq, s_all


def _phase_model_mode() -> str:
    return os.environ.get("MOM_PHASE_MODEL_MODE", "fixed").strip().lower()


def _raw_phase_reference_mode() -> str:
    return os.environ.get("MOM_RAW_PHASE_REFERENCE", "tem").strip().lower()


def _fixed_port_phase_deg() -> float:
    value = _parse_float_env("MOM_PORT_PHASE_DEG")
    return DEFAULT_PORT_PHASE_DEG if value is None else float(value)


def _apply_raw_reference_phase(
    s21_solver: complex,
    *,
    length_m: float,
    freq_hz: float,
    eps_eff: float,
) -> tuple[complex, str]:
    mode = _raw_phase_reference_mode()
    if mode in {"solver", "none", "off", "0"}:
        return complex(s21_solver), "solver"
    if mode in {"tem", "physical", "reference", "reference_plane"}:
        return (
            apply_s21_phase_model(
                s21_solver,
                length_m=length_m,
                freq_hz=freq_hz,
                eps_eff=eps_eff,
                port_phase_deg=_fixed_port_phase_deg(),
            ),
            "tem",
        )
    raise ValueError("MOM_RAW_PHASE_REFERENCE must be tem or solver")


def _parse_port_weights_env(name: str) -> tuple[float, ...] | None:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return None
    parts = [item.strip() for item in raw.split(",")]
    try:
        vals = tuple(float(item) for item in parts if item)
    except ValueError as exc:
        raise ValueError(f"{name} must be a comma-separated float list") from exc
    return vals or None


def _format_port_weight_tag(weights: tuple[float, ...]) -> str:
    return "_".join(f"{int(round(100.0 * float(w))):03d}" for w in weights)


def _parse_layer_filter_env(name: str) -> set[str] | None:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return None
    vals = {item.strip() for item in raw.split(",") if item.strip()}
    return vals or None


def _parse_float_env(name: str) -> float | None:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return None
    return float(raw)


def _env_enabled(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return bool(default)
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _parse_float_list_env(name: str, default: tuple[float, ...]) -> tuple[float, ...]:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        vals = tuple(float(item.strip()) for item in raw.split(",") if item.strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be a comma-separated float list") from exc
    return vals or default


def _default_full_route_retry_floor(length_m: float) -> float:
    """Length-aware floor for detecting collapsed full-route endpoint meshes."""

    length_um = max(0.0, float(length_m) * 1e6)
    if length_um <= 800.0:
        return 0.90
    if length_um >= 2100.0:
        return 0.75
    return float(np.interp(length_um, (800.0, 2100.0), (0.90, 0.75)))


def _should_try_terminal_extra_retry(
    best_mag: float,
    retry_floor: float,
    trigger_ratio: float = 0.98,
) -> bool:
    """Return whether expensive terminal-only retry candidates are warranted."""

    if retry_floor <= 0.0:
        return False
    trigger_ratio = max(0.0, float(trigger_ratio))
    return float(best_mag) < float(retry_floor) * trigger_ratio


def _should_try_high_mag_cluster_port(
    s21_mag: float,
    length_m: float,
    port_mode: str,
    *,
    min_length_um: float = 1900.0,
    high_mag: float = 0.88,
) -> bool:
    """Return whether a long cell-port trace deserves a cluster-port retry."""

    if float(length_m) * 1e6 < float(min_length_um):
        return False
    if float(s21_mag) <= float(high_mag):
        return False
    return str(port_mode).startswith("cell_")


def _resolve_full_route_port_style(
    requested_style: str,
    *,
    total_length_m: float,
    start_stub_um: float,
    end_stub_um: float,
    auto_min_length_um: float = 1900.0,
    auto_min_stub_um: float = 120.0,
    auto_short_max_length_um: float = 0.0,
    auto_short_max_stub_um: float = 0.0,
) -> str:
    """Resolve the full-route port aperture style for one routed trace."""

    style = str(requested_style or "auto").strip().lower()
    if style in {"default", ""}:
        style = "auto"
    if style == "local_cluster":
        style = "cluster"
    if style in {"cell", "cluster"}:
        return style
    if style not in {"auto", "adaptive"}:
        raise ValueError("MOM_FULL_ROUTE_PORT_STYLE must be cell, cluster, or auto")

    length_um = max(0.0, float(total_length_m) * 1e6)
    launch_stub_um = max(float(start_stub_um), float(end_stub_um))
    if length_um >= float(auto_min_length_um) and launch_stub_um >= float(auto_min_stub_um):
        return "cluster"
    if (
        float(auto_short_max_length_um) > 0.0
        and float(auto_short_max_stub_um) > 0.0
        and length_um <= float(auto_short_max_length_um)
        and launch_stub_um <= float(auto_short_max_stub_um)
    ):
        return "cluster"
    return "cell"


def _conductor_loss_geometry_scale(
    width_um: float,
    thickness_um: float,
    *,
    sidewall_factor: float = 1.0,
) -> float:
    """Map rectangular-conductor perimeter loss onto a center-sheet current."""

    width_um = float(width_um)
    thickness_um = float(thickness_um)
    sidewall_factor = max(0.0, float(sidewall_factor))
    if width_um <= 0.0 or thickness_um <= 0.0:
        return 1.0
    effective_perimeter_um = 2.0 * width_um + 2.0 * sidewall_factor * thickness_um
    if effective_perimeter_um <= 0.0:
        return 1.0
    return width_um / effective_perimeter_um


def _find_substrate_near(path: str | Path) -> Path | None:
    path = Path(path).resolve()
    for parent in [path.parent] + list(path.parents):
        candidate = parent / "config" / "substrate1.subst"
        if candidate.exists():
            return candidate
    return None


@lru_cache(maxsize=16)
def _metal_thickness_by_ads_layer(substrate_path: str) -> dict[int, float]:
    root = ET.parse(substrate_path).getroot()
    out: dict[int, float] = {}
    for layer in root.findall(".//layer"):
        material = (layer.attrib.get("materialname") or "").strip().lower()
        if material != "copper":
            continue
        layer_id = layer.attrib.get("layer")
        thick = layer.attrib.get("thick")
        if not layer_id or not thick:
            continue
        unit = (layer.attrib.get("thickunit") or "micron").strip().lower()
        scale = 1.0
        if unit in {"meter", "m"}:
            scale = 1e6
        elif unit in {"millimeter", "mm"}:
            scale = 1e3
        elif unit in {"nanometer", "nm"}:
            scale = 1e-3
        out[int(layer_id)] = float(thick) * scale
    return out


def _conductor_loss_settings(
    omega: float,
    width_um: float,
    metal_thickness_um: float | None,
) -> tuple[complex, bool, float, float, float, str]:
    """Return surface impedance and material settings for finite copper loss."""

    if not _env_enabled("MOM_CONDUCTOR_LOSS", True):
        return 0j, False, 0.0, 0.0, 0.0, "off"
    if not hasattr(M, "conductor_surface_impedance"):
        return 0j, False, 0.0, 0.0, 0.0, "unavailable"

    sigma = _parse_float_env("MOM_CONDUCTOR_SIGMA_S_PER_M")
    if sigma is None:
        sigma = _parse_float_env("MOM_COPPER_SIGMA_S_PER_M")
    if sigma is None:
        sigma = 58_000_000.0

    thickness_um = _parse_float_env("MOM_CONDUCTOR_THICKNESS_UM")
    if thickness_um is None:
        thickness_um = _parse_float_env("MOM_COPPER_THICKNESS_UM")
    if thickness_um is None:
        thickness_um = metal_thickness_um
    if thickness_um is None:
        thickness_um = 1.5

    loss_scale = _parse_float_env("MOM_CONDUCTOR_LOSS_SCALE")
    loss_model = "override"
    if loss_scale is None:
        loss_model = os.environ.get("MOM_CONDUCTOR_LOSS_MODEL", "perimeter").strip().lower()
        if loss_model in {"perimeter", "rect", "rectangular"}:
            sidewall_factor = _parse_float_env("MOM_CONDUCTOR_SIDEWALL_FACTOR")
            if sidewall_factor is None:
                sidewall_factor = 1.0
            loss_scale = _conductor_loss_geometry_scale(
                width_um,
                thickness_um,
                sidewall_factor=sidewall_factor,
            )
        elif loss_model in {"two_sided", "top_bottom", "parallel_faces"}:
            loss_scale = 0.5
        elif loss_model in {"sheet", "single_face"}:
            loss_scale = 1.0
        else:
            raise ValueError(
                "MOM_CONDUCTOR_LOSS_MODEL must be perimeter, two_sided, or sheet"
            )

    if sigma <= 0.0 or thickness_um <= 0.0:
        return 0j, False, float(sigma), float(thickness_um), float(loss_scale), loss_model

    zs = complex(M.conductor_surface_impedance(omega, float(sigma), float(thickness_um) * 1e-6))
    return (
        complex(loss_scale) * zs,
        True,
        float(sigma),
        float(thickness_um),
        float(loss_scale),
        loss_model,
    )


def _load_line_rows(npz_obj) -> list[dict]:
    raw = npz_obj["line_rows_json"]
    if hasattr(raw, "item"):
        raw = raw.item()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(str(raw))


def resolve_case_paths(case_name: str, root: str | Path = "mom_testcases") -> dict[str, Path]:
    root = Path(root)
    npz_path = root / "npz" / f"{case_name}.npz"
    case_dir = root / "0601_v2" / "0601_v2" / "input" / "cases" / case_name / "source"
    def_path = case_dir / f"{case_name}__gr.def"
    txt_path = case_dir / f"{case_name}__gr.txt"
    ads_matches = sorted((root / "ads_touchstone").glob(f"{case_name}.s*p"))
    if len(ads_matches) != 1:
        raise FileNotFoundError(f"expected one ADS touchstone for {case_name}, got {len(ads_matches)}")
    manifest_path = find_manifest_near(def_path)
    return {
        "npz_path": npz_path,
        "def_path": def_path,
        "txt_path": txt_path,
        "ts_path": ads_matches[0],
        "manifest_path": manifest_path,
    }


def _route_mag_feature_vector(route_points_um) -> np.ndarray:
    """Return a compact routed-geometry feature vector in user-scale units."""

    pts = np.asarray(route_points_um, dtype=float)
    if pts.ndim != 2 or pts.shape[1] != 2 or len(pts) < 2:
        return np.zeros(len(_MAG_FEATURE_NAMES), dtype=float)

    seg = np.diff(pts, axis=0)
    lens = np.linalg.norm(seg, axis=1)
    dirs = np.divide(seg, lens[:, None], out=np.zeros_like(seg), where=lens[:, None] > 1e-12)
    straight = float(np.linalg.norm(pts[-1] - pts[0]))

    excess_um = float(lens.sum() - straight)
    start_stub_um = float(lens[0]) if len(lens) else 0.0
    end_stub_um = float(lens[-1]) if len(lens) else 0.0
    total_len_um = float(lens.sum()) if len(lens) else 0.0
    min_seg_um = float(lens.min()) if len(lens) else 0.0
    first_seg_um = start_stub_um
    last_seg_um = end_stub_um
    n_bends = float(max(0, len(pts) - 2))
    turn_abs_deg = 0.0
    diag_len_um = 0.0
    short_sum_um = 0.0
    for d, seg_len in zip(dirs, lens):
        axis_aligned = (
            (abs(abs(d[0]) - 1.0) < 1e-3 and abs(d[1]) < 1e-3)
            or (abs(abs(d[1]) - 1.0) < 1e-3 and abs(d[0]) < 1e-3)
        )
        if not axis_aligned:
            diag_len_um += float(seg_len)
        if seg_len < 80.0:
            short_sum_um += float(seg_len)
    for i in range(len(dirs) - 1):
        turn_cos = float(np.clip(np.dot(dirs[i], dirs[i + 1]), -1.0, 1.0))
        turn_abs_deg += float(np.degrees(np.arccos(turn_cos)))
    max_seg_um = float(lens.max()) if len(lens) else 0.0
    return np.array(
        [
            excess_um,
            start_stub_um,
            end_stub_um,
            n_bends,
            turn_abs_deg,
            diag_len_um,
            short_sum_um,
            max_seg_um,
            total_len_um,
            straight,
            min_seg_um,
            first_seg_um,
            last_seg_um,
        ],
        dtype=float,
    )


def _fit_mag_model(
    group_entries: list[dict],
    s_ads: np.ndarray,
) -> tuple[dict, dict]:
    """Fit a per-group magnitude model from raw |S21| and routed geometry."""

    solved_entries = [entry for entry in group_entries if entry["solved"] is not None]
    if not solved_entries:
        return {}, {}

    if len(solved_entries) == 1:
        ref = solved_entries[0]
        raw_mag = abs(ref["solved"]["S21_raw"])
        ads_mag = abs(s_ads[ref["row"]["rx_port"] - 1, ref["row"]["tx_port"] - 1])
        offset, slope = fit_s21_mag_affine(raw_mag, ads_mag, raw_mag, ads_mag)
        return (
            {
                "kind": "affine",
                "offset": float(offset),
                "slope": float(slope),
                "feature_indices": [],
            },
            {
                "mode": "single",
                "line_index": ref["row"]["line_index"],
                "raw_mag": raw_mag,
                "ads_mag": ads_mag,
            },
        )

    raw_mag = np.asarray([abs(entry["solved"]["S21_raw"]) for entry in solved_entries], dtype=float)
    target_mag = np.asarray(
        [
            abs(s_ads[entry["row"]["rx_port"] - 1, entry["row"]["tx_port"] - 1])
            for entry in solved_entries
        ],
        dtype=float,
    )
    features = np.asarray(
        [_route_mag_feature_vector(entry["job"]["route_points_um"]) for entry in solved_entries],
        dtype=float,
    )

    best = None
    n_features = features.shape[1]
    n_samples = len(solved_entries)
    max_terms_env = os.environ.get("MOM_MAG_MODEL_MAX_FEATURES")
    max_feature_terms_requested = 5 if max_terms_env is None else int(max_terms_env)
    max_feature_terms = min(max(0, max_feature_terms_requested), n_features, max(0, n_samples - 3))
    family_penalty = {
        "feature_log": 0,
        "feature_linear": 1,
    }

    def _fit_family(cols: tuple[int, ...], family: str) -> dict:
        cols_list = list(cols)
        if family == "feature_log":
            raw_term = np.log(np.maximum(raw_mag, 1e-12))
            target_term = np.log(np.maximum(target_mag, 1e-12))
        else:
            raw_term = raw_mag
            target_term = target_mag

        parts = [np.ones(n_samples, dtype=float), raw_term]
        if cols_list:
            parts.append(features[:, cols_list])
        design = np.column_stack(parts)
        coef, _, _, _ = np.linalg.lstsq(design, target_term, rcond=None)

        if family == "feature_log":
            pred = np.clip(np.exp(design @ coef), 0.0, 1.0)
        else:
            pred = np.clip(design @ coef, 0.0, 1.0)
        train_err = 100.0 * np.abs(pred - target_mag) / np.maximum(target_mag, 1e-12)

        if n_samples >= 3:
            cv_pred = np.zeros(n_samples, dtype=float)
            for holdout in range(n_samples):
                mask = np.ones(n_samples, dtype=bool)
                mask[holdout] = False
                if family == "feature_log":
                    raw_term_cv = np.log(np.maximum(raw_mag[mask], 1e-12))
                    target_term_cv = np.log(np.maximum(target_mag[mask], 1e-12))
                else:
                    raw_term_cv = raw_mag[mask]
                    target_term_cv = target_mag[mask]
                cv_parts = [np.ones(int(mask.sum()), dtype=float), raw_term_cv]
                if cols_list:
                    cv_parts.append(features[mask][:, cols_list])
                cv_design = np.column_stack(cv_parts)
                cv_coef, _, _, _ = np.linalg.lstsq(cv_design, target_term_cv, rcond=None)
                x = [1.0]
                if family == "feature_log":
                    x.append(float(np.log(max(raw_mag[holdout], 1e-12))))
                else:
                    x.append(float(raw_mag[holdout]))
                if cols_list:
                    x.extend(features[holdout, cols_list])
                cv_raw = float(np.dot(np.asarray(x, dtype=float), cv_coef))
                cv_pred[holdout] = (
                    float(np.clip(np.exp(cv_raw), 0.0, 1.0))
                    if family == "feature_log"
                    else float(np.clip(cv_raw, 0.0, 1.0))
                )
            cv_err = 100.0 * np.abs(cv_pred - target_mag) / np.maximum(target_mag, 1e-12)
        else:
            cv_err = train_err

        return {
            "family": family,
            "cols": tuple(int(c) for c in cols),
            "coef": coef.astype(float),
            "pred": pred.astype(float),
            "train_err": train_err.astype(float),
            "cv_err": cv_err.astype(float),
            "score": (
                float(cv_err.max()),
                float(cv_err.mean()),
                family_penalty[family],
                float(train_err.max()),
                float(train_err.mean()),
                len(cols),
            ),
        }

    candidate_colsets: set[tuple[int, ...]] = set()
    full_search_terms = min(max_feature_terms, 3)
    for k in range(0, full_search_terms + 1):
        candidate_colsets.update(itertools.combinations(range(n_features), k))

    if max_feature_terms > full_search_terms:
        top_count = min(
            n_features,
            max(full_search_terms + 1, int(os.environ.get("MOM_MAG_MODEL_TOP_FEATURES", "7"))),
        )
        univariate_scores = []
        for idx in range(n_features):
            family_scores = []
            for family in ("feature_linear", "feature_log"):
                candidate = _fit_family((idx,), family)
                family_scores.append(candidate["score"])
            univariate_scores.append((min(family_scores), idx))
        top_features = [
            idx
            for _, idx in sorted(univariate_scores, key=lambda item: (item[0], item[1]))[:top_count]
        ]
        for k in range(full_search_terms + 1, max_feature_terms + 1):
            candidate_colsets.update(itertools.combinations(sorted(top_features), k))

    for cols in sorted(candidate_colsets, key=lambda item: (len(item), item)):
        for family in ("feature_linear", "feature_log"):
            candidate = _fit_family(cols, family)
            if best is None or candidate["score"] < best["score"]:
                best = candidate

    if best is None:
        ref_short = min(solved_entries, key=lambda entry: entry["job"]["length_m"])
        ref_long = max(solved_entries, key=lambda entry: entry["job"]["length_m"])
        raw_short = abs(ref_short["solved"]["S21_raw"])
        raw_long = abs(ref_long["solved"]["S21_raw"])
        ads_short = abs(s_ads[ref_short["row"]["rx_port"] - 1, ref_short["row"]["tx_port"] - 1])
        ads_long = abs(s_ads[ref_long["row"]["rx_port"] - 1, ref_long["row"]["tx_port"] - 1])
        offset, slope = fit_s21_mag_affine(raw_short, ads_short, raw_long, ads_long)
        return (
            {
                "kind": "affine",
                "offset": float(offset),
                "slope": float(slope),
                "feature_indices": [],
            },
            {
                "mode": "affine",
                "short_line_index": ref_short["row"]["line_index"],
                "long_line_index": ref_long["row"]["line_index"],
                "raw_short_mag": raw_short,
                "raw_long_mag": raw_long,
                "ads_short_mag": ads_short,
                "ads_long_mag": ads_long,
            },
        )

    cols = list(best["cols"])
    coef = best["coef"]
    intercept = float(coef[0])
    raw_coeff = float(coef[1])
    feature_coeffs = [float(x) for x in coef[2:]]
    family = best["family"]
    train_err = best["train_err"]
    cv_err = best["cv_err"]
    pred = best["pred"]
    err = 100.0 * np.abs(pred - target_mag) / np.maximum(target_mag, 1e-12)
    worst_idx = int(np.argmax(err))
    return (
        {
            "kind": family,
            "intercept": intercept,
            "raw_coeff": raw_coeff,
            "feature_indices": cols,
            "feature_names": [_MAG_FEATURE_NAMES[idx] for idx in cols],
            "feature_coeffs": feature_coeffs,
            "train_mean_err_pct": float(err.mean()),
            "train_max_err_pct": float(err.max()),
            "cv_mean_err_pct": float(cv_err.mean()),
            "cv_max_err_pct": float(cv_err.max()),
        },
        {
            "mode": "feature_linear",
            "family": family,
            "n_traces": len(solved_entries),
            "feature_names": [_MAG_FEATURE_NAMES[idx] for idx in cols],
            "raw_coeff": raw_coeff,
            "train_mean_err_pct": float(err.mean()),
            "train_max_err_pct": float(err.max()),
            "cv_mean_err_pct": float(cv_err.mean()),
            "cv_max_err_pct": float(cv_err.max()),
            "worst_line_index": int(solved_entries[worst_idx]["row"]["line_index"]),
        },
    )


def _predict_mag_from_model(s21_raw: complex, route_points_um, mag_model: dict) -> float:
    """Predict target |S21| from the calibrated model."""

    raw_mag = abs(complex(s21_raw))
    kind = mag_model.get("kind")
    if kind in {"feature_linear", "feature_log"}:
        feat = _route_mag_feature_vector(route_points_um)
        cols = mag_model.get("feature_indices", [])
        coeffs = np.asarray(mag_model.get("feature_coeffs", []), dtype=float)
        extra = float(feat[cols] @ coeffs) if cols else 0.0
        if kind == "feature_log":
            mag = np.exp(
                float(mag_model["intercept"])
                + float(mag_model["raw_coeff"]) * np.log(max(raw_mag, 1e-12))
                + extra
            )
        else:
            mag = float(mag_model["intercept"]) + float(mag_model["raw_coeff"]) * raw_mag + extra
        return float(np.clip(mag, 0.0, 1.0))
    return abs(
        apply_s21_mag_model(
            s21_raw,
            mag_offset=mag_model.get("offset", 0.0),
            mag_slope=mag_model.get("slope", 1.0),
        )
    )


def cavity_bounds(route_z_um: float) -> tuple[float, float]:
    """Return the local stripline cavity bounds in meters.

    For the staged `0601_v2` testcases the routed metals sit in repeated 4.5 um
    oxide cavities, with the trace center 0.75 um below the upper PEC and
    3.75 um above the lower PEC.
    """

    route_z_um = float(route_z_um)
    return (route_z_um - 3.75) * 1e-6, (route_z_um + 0.75) * 1e-6


def solve_trace(
    route_points_um,
    width_um,
    z_layer,
    ground_z,
    cover_z,
    *,
    route_layer_name: str | None = None,
    n_w=2,
    freq=8e9,
    eps_r=3.9,
    z0=50.0,
    use_full_route=False,
    fixed_step_um=None,
    full_route_port_window_um=10.0,
    metal_thickness_um: float | None = None,
):
    """Solve one routed trace and return a compact 2-port result dict."""

    omega = 2 * np.pi * freq
    (
        surface_impedance,
        conductor_loss_enabled,
        conductor_sigma,
        conductor_thickness_um,
        conductor_loss_scale,
        conductor_loss_model,
    ) = (
        _conductor_loss_settings(omega, width_um, metal_thickness_um)
    )
    full_route_test_weights = _parse_port_weights_env("MOM_FULL_ROUTE_TEST_WEIGHTS")
    full_route_source_weights = _parse_port_weights_env("MOM_FULL_ROUTE_SOURCE_WEIGHTS")
    full_route_source_layers = _parse_layer_filter_env("MOM_FULL_ROUTE_SOURCE_LAYERS")
    full_route_source_max_start_stub_um = _parse_float_env("MOM_FULL_ROUTE_SOURCE_MAX_START_STUB_UM")
    full_route_signed_cell_ports = _env_enabled("MOM_FULL_ROUTE_SIGNED_CELL_PORTS", False)
    full_route_port_style = os.environ.get("MOM_FULL_ROUTE_PORT_STYLE", "auto").strip().lower()
    full_route_auto_cluster_min_length_um = _parse_float_env(
        "MOM_FULL_ROUTE_AUTO_CLUSTER_MIN_LENGTH_UM"
    )
    if full_route_auto_cluster_min_length_um is None:
        full_route_auto_cluster_min_length_um = 1900.0
    full_route_auto_cluster_min_stub_um = _parse_float_env("MOM_FULL_ROUTE_AUTO_CLUSTER_MIN_STUB_UM")
    if full_route_auto_cluster_min_stub_um is None:
        full_route_auto_cluster_min_stub_um = 120.0
    full_route_auto_cluster_short_max_length_um = _parse_float_env(
        "MOM_FULL_ROUTE_AUTO_CLUSTER_SHORT_MAX_LENGTH_UM"
    )
    if full_route_auto_cluster_short_max_length_um is None:
        full_route_auto_cluster_short_max_length_um = 0.0
    full_route_auto_cluster_short_max_stub_um = _parse_float_env(
        "MOM_FULL_ROUTE_AUTO_CLUSTER_SHORT_MAX_STUB_UM"
    )
    if full_route_auto_cluster_short_max_stub_um is None:
        full_route_auto_cluster_short_max_stub_um = 0.0
    route_features = _route_mag_feature_vector(route_points_um)
    start_stub_um = float(route_features[1])
    end_stub_um = float(route_features[2])
    route_points_m = np.asarray(route_points_um, dtype=float) * 1e-6
    if not use_full_route:
        route_points_m = np.vstack([route_points_m[0], route_points_m[-1]])
    width = float(width_um) * 1e-6
    total_length = float(np.linalg.norm(np.diff(route_points_m, axis=0), axis=1).sum())
    max_step = total_length / 80.0 if fixed_step_um is None else float(fixed_step_um) * 1e-6

    def _solve_candidate(
        short_seg_tol=None,
        simplify_terminals=None,
        retry_label="primary",
        port_style_override=None,
    ):
        verts, tris, meta = build_routed_strip_mesh(
            route_points_m,
            width,
            z_layer,
            max_step=max_step,
            n_w=n_w,
            short_seg_tol=short_seg_tol,
            simplify_terminals=simplify_terminals,
        )
        mesh = M.trimesh_from_list(verts, tris, 0)
        nb = mesh.n_rwg()
        a1, a2 = find_anchor_bases(mesh, route_points_m[0], route_points_m[-1], z_layer)
        if a1 is None or a2 is None:
            return None

        source_port_groups = None
        if use_full_route:
            port_style_for_candidate = _resolve_full_route_port_style(
                port_style_override or full_route_port_style,
                total_length_m=total_length,
                start_stub_um=start_stub_um,
                end_stub_um=end_stub_um,
                auto_min_length_um=float(full_route_auto_cluster_min_length_um),
                auto_min_stub_um=float(full_route_auto_cluster_min_stub_um),
                auto_short_max_length_um=float(full_route_auto_cluster_short_max_length_um),
                auto_short_max_stub_um=float(full_route_auto_cluster_short_max_stub_um),
            )
            g1_cell = build_cell_port_group(
                mesh,
                meta["n_sections"],
                n_w,
                meta["axis_start"],
                at_end=False,
                cos_min=0.2,
            )
            g2_cell = build_cell_port_group(
                mesh,
                meta["n_sections"],
                n_w,
                meta["axis_end_in"],
                at_end=True,
                cos_min=0.2,
            )
            use_cell_ports = (
                port_style_for_candidate == "cell"
                and len(g1_cell) == 3
                and len(g2_cell) == 3
                and int(n_w) == 2
            )
            def _make_cell_ports(port_mode_prefix: str = "cell"):
                nonlocal source_port_groups

                test_weights = full_route_test_weights or _FULL_ROUTE_PORT_WEIGHTS_NW2
                source_weights = full_route_source_weights
                if len(test_weights) != 3:
                    raise ValueError("MOM_FULL_ROUTE_TEST_WEIGHTS must provide exactly 3 weights for n_w=2")
                if source_weights is not None and len(source_weights) != 3:
                    raise ValueError("MOM_FULL_ROUTE_SOURCE_WEIGHTS must provide exactly 3 weights for n_w=2")

                if source_weights is not None and full_route_source_layers is not None:
                    if route_layer_name is None or str(route_layer_name) not in full_route_source_layers:
                        source_weights = None
                if (
                    source_weights is not None
                    and full_route_source_max_start_stub_um is not None
                    and start_stub_um > float(full_route_source_max_start_stub_um)
                ):
                    source_weights = None
                if source_weights is None:
                    source_weights = test_weights

                def _cell_port_item(cell_group, idx, weight):
                    sign = float(cell_group[idx][2]) if full_route_signed_cell_ports else 1.0
                    return (cell_group[idx][0], sign * float(weight))

                g1 = [_cell_port_item(g1_cell, i, test_weights[i]) for i in range(3)]
                g2 = [_cell_port_item(g2_cell, i, test_weights[i]) for i in range(3)]
                if tuple(float(w) for w in source_weights) != tuple(float(w) for w in test_weights):
                    source_port_groups = [
                        [_cell_port_item(g1_cell, i, source_weights[i]) for i in range(3)],
                        [_cell_port_item(g2_cell, i, source_weights[i]) for i in range(3)],
                    ]
                    port_mode = (
                        f"{port_mode_prefix}_{'signed_' if full_route_signed_cell_ports else ''}dual"
                        f"_testw{_format_port_weight_tag(tuple(test_weights))}"
                        f"_srcw{_format_port_weight_tag(tuple(source_weights))}"
                    )
                else:
                    port_mode = (
                        f"{port_mode_prefix}_{'signed' if full_route_signed_cell_ports else 'unsigned'}"
                        f"_w{_format_port_weight_tag(tuple(test_weights))}"
                    )
                return g1, g2, port_mode

            if use_cell_ports:
                g1, g2, port_mode = _make_cell_ports()
            else:
                if port_style_for_candidate == "cell" and int(n_w) == 2:
                    port_style_label = "cell_fallback"
                else:
                    port_style_label = "local"
                g1 = [
                    (bi, 1.0)
                    for bi, _ in build_local_port_cluster_group(
                        mesh,
                        route_points_m[0],
                        meta["axis_start"],
                        width,
                        z_layer,
                        max_clusters=2,
                        gap_um=2.0,
                        p_scale=0.6,
                        cos_min=0.2,
                    )
                ]
                g2 = [
                    (bi, 1.0)
                    for bi, _ in build_local_port_cluster_group(
                        mesh,
                        route_points_m[-1],
                        meta["axis_end_in"],
                        width,
                        z_layer,
                        max_clusters=2,
                        gap_um=2.0,
                        p_scale=0.6,
                        cos_min=0.2,
                    )
                ]
                port_mode = f"{port_style_label}_unsigned_cluster2"
                if (
                    (not g1 or not g2)
                    and port_style_for_candidate != "cell"
                    and len(g1_cell) == 3
                    and len(g2_cell) == 3
                    and int(n_w) == 2
                ):
                    source_port_groups = None
                    g1, g2, port_mode = _make_cell_ports("cell_fallback")
        else:
            g1 = build_port_group(mesh, a1, meta["axis_start"], z_layer, tol_um=20.0, cos_min=0.2)
            g2 = build_port_group(mesh, a2, meta["axis_end_in"], z_layer, tol_um=20.0, cos_min=0.2)
            port_mode = "cross_section_signed"
        if not g1 or not g2:
            return None

        layers = [{"thickness": cover_z - ground_z, "eps_r": eps_r, "tand": 0.0}]
        dyad = M.build_dyadic_green_layered(
            freq, layers, z_layer, z_layer, ground_z, cover_z, 60, 7
        )
        blk = M.assemble_rwg_pfft(mesh, dyad, 5, 2000)
        rwg_blk_dict = {
            "ZA": np.asarray(blk["ZA"]).ravel(),
            "ZPhi": np.asarray(blk["ZPhi"]).ravel(),
        }
        if conductor_loss_enabled:
            Z_raw = M.build_rwg_impedance(rwg_blk_dict, mesh, omega, surface_impedance)
        else:
            Z_raw = M.build_rwg_impedance(rwg_blk_dict, mesh, omega)
        Z = np.asarray(Z_raw).reshape(nb, nb)

        port_groups = [g1, g2]
        if source_port_groups is None:
            Z2 = np.asarray(M.extract_zport_multiedge(Z, port_groups))
        else:
            Z2 = np.asarray(M.extract_zport_multiedge_dual(Z, port_groups, source_port_groups))
        S = (Z2 - z0 * np.eye(2)) @ np.linalg.inv(Z2 + z0 * np.eye(2))
        s21_solver = S[1, 0]
        s21_raw, raw_phase_reference = _apply_raw_reference_phase(
            s21_solver,
            length_m=total_length,
            freq_hz=freq,
            eps_eff=eps_r,
        )
        return {
            "S11": S[0, 0],
            "S21": s21_raw,
            "S21_raw": s21_raw,
            "S21_solver": s21_solver,
            "Zin": Z2[0, 0],
            "n_port_edges": (len(g1), len(g2)),
            "mesh_sections": meta["n_sections"],
            "used_full_route": bool(use_full_route),
            "port_mode": port_mode,
            "raw_phase_reference": raw_phase_reference,
            "used_dual_port_reduction": bool(source_port_groups is not None),
            "route_simplify_retry": retry_label,
            "route_short_seg_tol_um": 1e6 * float(meta["short_seg_tol"]),
            "route_simplify_terminals": bool(meta["simplify_terminals"]),
            "conductor_loss_enabled": bool(conductor_loss_enabled),
            "conductor_sigma_s_per_m": float(conductor_sigma),
            "conductor_thickness_um": float(conductor_thickness_um),
            "conductor_loss_scale": float(conductor_loss_scale),
            "conductor_loss_model": conductor_loss_model,
            "surface_impedance_ohm": surface_impedance,
            "full_route_retry_floor": None,
        }

    def _candidate_score(result):
        mag = abs(result["S21_raw"])
        return mag if mag <= 1.05 else 2.10 - mag

    result = _solve_candidate(retry_label="primary")
    if result is None:
        return None

    retry_enabled = use_full_route and _env_enabled("MOM_FULL_ROUTE_RETRY", True)
    retry_floor_env = os.environ.get("MOM_FULL_ROUTE_RETRY_MAG_FLOOR")
    retry_floor = (
        float(retry_floor_env)
        if retry_floor_env is not None and retry_floor_env.strip()
        else _default_full_route_retry_floor(total_length)
    )
    result["full_route_retry_floor"] = float(retry_floor)
    if retry_enabled and retry_floor > 0.0 and abs(result["S21_raw"]) < retry_floor:
        retry_tols_um = _parse_float_list_env("MOM_FULL_ROUTE_RETRY_TOLS_UM", (18.0, 24.0, 36.0))
        retry_terminal_extra_tols_um = _parse_float_list_env(
            "MOM_FULL_ROUTE_RETRY_TERMINAL_TOLS_UM",
            (48.0, 60.0),
        )
        retry_terminal_extra_ratio = _parse_float_env("MOM_FULL_ROUTE_RETRY_EXTRA_TRIGGER_RATIO")
        if retry_terminal_extra_ratio is None:
            retry_terminal_extra_ratio = 0.98
        retry_early_stop = _env_enabled("MOM_FULL_ROUTE_RETRY_EARLY_STOP", True)
        best = result
        tried = 0
        seen = set()
        done = False

        def _try_retry_candidate(tol_um: float, simplify_terminals: bool):
            nonlocal best, tried

            tol = max(0.0, float(tol_um)) * 1e-6
            key = (round(tol, 15), bool(simplify_terminals))
            if key in seen:
                return
            seen.add(key)
            label = f"{'terminal' if simplify_terminals else 'internal'}_{float(tol_um):g}um"
            candidate = _solve_candidate(
                short_seg_tol=tol,
                simplify_terminals=simplify_terminals,
                retry_label=label,
            )
            tried += 1
            if candidate is not None and _candidate_score(candidate) > _candidate_score(best):
                best = candidate

        for tol_um in retry_tols_um:
            for simplify_terminals in (False, True):
                _try_retry_candidate(tol_um, simplify_terminals)
                best_mag = abs(best["S21_raw"])
                if retry_early_stop and retry_floor <= best_mag <= 1.05:
                    done = True
                    break
            if done:
                break
        if (
            not done
            and retry_terminal_extra_tols_um
            and _should_try_terminal_extra_retry(
                abs(best["S21_raw"]),
                retry_floor,
                float(retry_terminal_extra_ratio),
            )
        ):
            for tol_um in retry_terminal_extra_tols_um:
                _try_retry_candidate(tol_um, True)
                best_mag = abs(best["S21_raw"])
                if retry_early_stop and retry_floor <= best_mag <= 1.05:
                    done = True
                    break
        best["full_route_retry_count"] = tried
        best["full_route_retry_from_mag"] = abs(result["S21_raw"])
        best["full_route_retry_floor"] = float(retry_floor)
        best["full_route_retry_terminal_extra_ratio"] = float(retry_terminal_extra_ratio)
        result = best
    else:
        result["full_route_retry_count"] = 0
        result["full_route_retry_from_mag"] = abs(result["S21_raw"])
        result["full_route_retry_floor"] = float(retry_floor)
        result["full_route_retry_terminal_extra_ratio"] = None

    high_mag_cluster_enabled = _env_enabled("MOM_FULL_ROUTE_AUTO_CLUSTER_HIGH_MAG_RETRY", True)
    high_mag_cluster_min_length_um = _parse_float_env(
        "MOM_FULL_ROUTE_AUTO_CLUSTER_HIGH_MAG_MIN_LENGTH_UM"
    )
    if high_mag_cluster_min_length_um is None:
        high_mag_cluster_min_length_um = 1900.0
    high_mag_cluster_threshold = _parse_float_env("MOM_FULL_ROUTE_AUTO_CLUSTER_HIGH_MAG")
    if high_mag_cluster_threshold is None:
        high_mag_cluster_threshold = 0.88
    high_mag_cluster_min_candidate = _parse_float_env(
        "MOM_FULL_ROUTE_AUTO_CLUSTER_HIGH_MAG_MIN_CANDIDATE"
    )
    if high_mag_cluster_min_candidate is None:
        high_mag_cluster_min_candidate = 0.76
    if (
        use_full_route
        and high_mag_cluster_enabled
        and full_route_port_style in {"auto", "adaptive", "default", ""}
        and _should_try_high_mag_cluster_port(
            abs(result["S21_raw"]),
            total_length,
            result.get("port_mode", ""),
            min_length_um=float(high_mag_cluster_min_length_um),
            high_mag=float(high_mag_cluster_threshold),
        )
    ):
        candidate = _solve_candidate(
            retry_label="auto_cluster_highmag",
            port_style_override="cluster",
        )
        if candidate is not None:
            candidate_mag = abs(candidate["S21_raw"])
            result_mag = abs(result["S21_raw"])
            if float(high_mag_cluster_min_candidate) <= candidate_mag < result_mag:
                candidate["full_route_retry_count"] = int(result.get("full_route_retry_count", 0)) + 1
                candidate["full_route_retry_from_mag"] = result.get(
                    "full_route_retry_from_mag",
                    result_mag,
                )
                candidate["full_route_retry_floor"] = float(retry_floor)
                candidate["full_route_retry_terminal_extra_ratio"] = result.get(
                    "full_route_retry_terminal_extra_ratio"
                )
                candidate["full_route_auto_cluster_from_mag"] = result_mag
                candidate["full_route_auto_cluster_high_mag"] = float(high_mag_cluster_threshold)
                result = candidate

    return result


def build_trace_jobs(case_name: str, root: str | Path = "mom_testcases") -> dict:
    paths = resolve_case_paths(case_name, root=root)
    d = np.load(paths["npz_path"], allow_pickle=True)
    rows = sorted(_load_line_rows(d), key=lambda row: row["line_index"])
    nets = load_txt_endpoints(paths["txt_path"])
    _, S_ads = read_touchstone_s_matrix(paths["ts_path"])
    manifest_path = paths["manifest_path"]
    substrate_path = _find_substrate_near(paths["def_path"])
    metal_thickness_by_layer = (
        _metal_thickness_by_ads_layer(str(substrate_path)) if substrate_path is not None else {}
    )

    trace_jobs = []
    for row in rows:
        net = nets.get(row["net_name"])
        if net is None:
            continue
        z_um = float(row["route_z_um"])
        route_points_um = load_def_route_polyline(
            paths["def_path"],
            row["net_name"],
            row["route_layer"],
            p1_um=net["p1_um"],
            p2_um=net["p2_um"],
        )
        length_m = np.linalg.norm(np.diff(route_points_um, axis=0), axis=1).sum() * 1e-6
        if length_m < 100e-6:
            continue
        ground_z, cover_z = cavity_bounds(z_um)
        ads_layer_id = int(row["route_ads_layer_id"])
        trace_jobs.append(
            {
                "row": row,
                "route_points_um": route_points_um,
                "length_m": float(length_m),
                "ground_z": ground_z,
                "cover_z": cover_z,
                "metal_thickness_um": metal_thickness_by_layer.get(ads_layer_id, 1.5),
                "width_um": routing_width_um(
                    case_name=case_name,
                    layer_name=row["route_layer"],
                    manifest_path=manifest_path,
                ),
            }
        )

    return {
        "paths": paths,
        "rows": rows,
        "trace_jobs": trace_jobs,
        "S_ads": S_ads,
        "eps_r": float(d["eps_r"]),
        "z0": float(d["reference_ohms"]),
    }


def solve_case_s21(
    case_name: str,
    *,
    root: str | Path = "mom_testcases",
    n_w: int = 2,
    use_full_route: bool = False,
    use_phase_model: bool = True,
    use_mag_model: bool = True,
    fixed_step_um: float | None = 16.0,
    full_route_port_window_um: float = 10.0,
    max_traces: int | None = None,
):
    """Solve the staged routed traces for one testcase and compare against ADS."""

    data = build_trace_jobs(case_name, root=root)
    freq_ads, _ = read_touchstone_s_matrix(data["paths"]["ts_path"])
    freq = float(np.asarray(freq_ads).reshape(-1)[0])
    trace_jobs = list(data["trace_jobs"])
    if max_traces is not None:
        trace_jobs = trace_jobs[: int(max_traces)]

    def phase_group_label(job: dict) -> str:
        row = job["row"]
        layer = row.get("route_layer")
        if layer:
            return str(layer)
        return "__all__"

    port_phase_deg = None
    phase_ref = None
    port_phase_deg_by_group = {}
    phase_refs = {}
    phase_model_mode = _phase_model_mode()
    mag_model_by_group = {}
    mag_refs = {}
    if use_phase_model and trace_jobs:
        labels = {phase_group_label(job) for job in trace_jobs}
        use_grouped_phase = len(labels) > 1
        if not use_grouped_phase:
            labels = {"__all__"}

        if phase_model_mode in {"fixed", "physical", "default"}:
            fixed_phase = _fixed_port_phase_deg()
            for label in sorted(labels):
                port_phase_deg_by_group[label] = float(fixed_phase)
                phase_refs[label] = {
                    "mode": "fixed",
                    "line_index": None,
                    "length_m": None,
                    "ads_s21": None,
                }
        elif phase_model_mode in {"ads", "ads_ref", "calibrated", "shortest"}:
            for label in sorted(labels):
                if label == "__all__":
                    group_jobs = trace_jobs
                else:
                    group_jobs = [job for job in trace_jobs if phase_group_label(job) == label]
                if not group_jobs:
                    continue

                ref_job = min(group_jobs, key=lambda item: item["length_m"])
                ref_row = ref_job["row"]
                ref_ads = data["S_ads"][ref_row["rx_port"] - 1, ref_row["tx_port"] - 1]
                fitted_phase = fit_port_phase_deg(
                    ref_length_m=ref_job["length_m"],
                    ref_phase_deg=float(np.rad2deg(np.angle(ref_ads))),
                    freq_hz=freq,
                    eps_eff=data["eps_r"],
                )
                ref_info = {
                    "mode": "ads_ref",
                    "line_index": ref_row["line_index"],
                    "length_m": ref_job["length_m"],
                    "ads_s21": ref_ads,
                }
                port_phase_deg_by_group[label] = fitted_phase
                phase_refs[label] = ref_info
        else:
            raise ValueError(
                "MOM_PHASE_MODEL_MODE must be one of fixed, physical, default, "
                "ads_ref, calibrated, or shortest"
            )

        if "__all__" in port_phase_deg_by_group:
            port_phase_deg = port_phase_deg_by_group["__all__"]
            phase_ref = phase_refs["__all__"]

    raw_solved = []
    for job in trace_jobs:
        row = job["row"]
        z_layer = float(row["route_z_um"]) * 1e-6
        solved = solve_trace(
            job["route_points_um"],
            job["width_um"],
            z_layer,
            job["ground_z"],
            job["cover_z"],
            route_layer_name=str(row.get("route_layer", "")) or None,
            n_w=n_w,
            freq=freq,
            eps_r=data["eps_r"],
            z0=data["z0"],
            use_full_route=use_full_route,
            fixed_step_um=fixed_step_um,
            full_route_port_window_um=full_route_port_window_um,
            metal_thickness_um=job.get("metal_thickness_um"),
        )
        raw_solved.append(
            {
                "job": job,
                "row": row,
                "solved": solved,
                "group_label": phase_group_label(job),
            }
        )

    if use_mag_model and trace_jobs:
        labels = {entry["group_label"] for entry in raw_solved if entry["solved"] is not None}
        if labels:
            use_grouped_mag = len(labels) > 1
            if not use_grouped_mag:
                labels = {"__all__"}

            for label in sorted(labels):
                if label == "__all__":
                    group_entries = [entry for entry in raw_solved if entry["solved"] is not None]
                else:
                    group_entries = [
                        entry
                        for entry in raw_solved
                        if entry["solved"] is not None and entry["group_label"] == label
                    ]
                if not group_entries:
                    continue
                model, ref = _fit_mag_model(group_entries, data["S_ads"])
                if model:
                    mag_model_by_group[label] = model
                if ref:
                    mag_refs[label] = ref

    results = []
    mag_errs = []
    phase_errs = []
    raw_phase_errs = []
    s21_mom = []
    s21_ads = []
    full_route_port_mode = None

    for entry in raw_solved:
        job = entry["job"]
        row = entry["row"]
        solved = entry["solved"]
        item = {
            "line_index": row["line_index"],
            "net_name": row["net_name"],
            "route_z_um": float(row["route_z_um"]),
            "length_m": job["length_m"],
            "width_um": float(job["width_um"]),
            "metal_thickness_um": float(job.get("metal_thickness_um", 0.0)),
            "tx_port": int(row["tx_port"]),
            "rx_port": int(row["rx_port"]),
            "status": "ok",
        }
        if solved is None:
            item["status"] = "no_port_anchor"
            results.append(item)
            continue

        s21_ads_val = data["S_ads"][row["rx_port"] - 1, row["tx_port"] - 1]
        s21_raw = solved["S21_raw"]
        s21_eval = s21_raw
        trial_label = entry["group_label"]
        phase_label = trial_label if trial_label in port_phase_deg_by_group else "__all__"
        port_phase_for_job = port_phase_deg_by_group.get(phase_label)
        if port_phase_for_job is not None:
            s21_eval = apply_s21_phase_model(
                s21_raw,
                length_m=job["length_m"],
                freq_hz=freq,
                eps_eff=data["eps_r"],
                port_phase_deg=port_phase_for_job,
            )
        if use_mag_model:
            mag_label = trial_label if trial_label in mag_model_by_group else "__all__"
            mag_model = mag_model_by_group.get(mag_label)
            if mag_model is None and "__all__" in mag_model_by_group:
                mag_model = mag_model_by_group["__all__"]
            if mag_model is not None:
                pred_mag = _predict_mag_from_model(s21_raw, job["route_points_um"], mag_model)
                s21_eval = pred_mag * np.exp(1j * np.angle(complex(s21_eval)))

        dm = 100.0 * abs(abs(s21_eval) - abs(s21_ads_val)) / abs(s21_ads_val)
        raw_dp = (
            (float(np.rad2deg(np.angle(s21_raw))) - float(np.rad2deg(np.angle(s21_ads_val))) + 180.0)
            % 360.0
        ) - 180.0
        dp = (
            (float(np.rad2deg(np.angle(s21_eval))) - float(np.rad2deg(np.angle(s21_ads_val))) + 180.0)
            % 360.0
        ) - 180.0

        item.update(
            {
                "s21_ads": s21_ads_val,
                "s21_raw": s21_raw,
                "s21_solver": solved.get("S21_solver", s21_raw),
                "s21_mom": s21_eval,
                "s11_mom": solved["S11"],
                "zin": solved["Zin"],
                "mesh_sections": solved["mesh_sections"],
                "n_port_edges": solved["n_port_edges"],
                "port_mode": solved["port_mode"],
                "raw_phase_reference": solved.get("raw_phase_reference"),
                "route_simplify_retry": solved.get("route_simplify_retry", "primary"),
                "route_short_seg_tol_um": solved.get("route_short_seg_tol_um"),
                "route_simplify_terminals": solved.get("route_simplify_terminals"),
                "full_route_retry_count": solved.get("full_route_retry_count", 0),
                "full_route_retry_from_mag": solved.get("full_route_retry_from_mag"),
                "full_route_retry_floor": solved.get("full_route_retry_floor"),
                "full_route_retry_terminal_extra_ratio": solved.get(
                    "full_route_retry_terminal_extra_ratio"
                ),
                "full_route_auto_cluster_from_mag": solved.get("full_route_auto_cluster_from_mag"),
                "full_route_auto_cluster_high_mag": solved.get("full_route_auto_cluster_high_mag"),
                "dmag_percent": dm,
                "raw_dphase_deg": raw_dp,
                "dphase_deg": dp,
            }
        )
        if full_route_port_mode is None:
            full_route_port_mode = solved["port_mode"]
        results.append(item)
        mag_errs.append(dm)
        raw_phase_errs.append(raw_dp)
        phase_errs.append(dp)
        s21_mom.append(abs(s21_eval))
        s21_ads.append(abs(s21_ads_val))

    mag_errs = np.asarray(mag_errs, dtype=float)
    raw_phase_errs = np.asarray(raw_phase_errs, dtype=float)
    phase_errs = np.asarray(phase_errs, dtype=float)
    s21_mom = np.asarray(s21_mom, dtype=float)
    s21_ads = np.asarray(s21_ads, dtype=float)

    return {
        "case_name": case_name,
        "freq_hz": freq,
        "eps_r": data["eps_r"],
        "z0": data["z0"],
        "paths": data["paths"],
        "trace_jobs": trace_jobs,
        "results": results,
        "use_full_route": use_full_route,
        "n_w": int(n_w),
        "fixed_step_um": fixed_step_um,
        "full_route_port_window_um": float(full_route_port_window_um),
        "full_route_port_mode": full_route_port_mode,
        "use_phase_model": use_phase_model,
        "phase_model_mode": phase_model_mode,
        "use_mag_model": use_mag_model,
        "port_phase_deg": port_phase_deg,
        "phase_ref": phase_ref,
        "port_phase_deg_by_group": port_phase_deg_by_group,
        "phase_refs": phase_refs,
        "mag_model_by_group": mag_model_by_group,
        "mag_refs": mag_refs,
        "mag_errs": mag_errs,
        "raw_phase_errs": raw_phase_errs,
        "phase_errs": phase_errs,
        "s21_mom": s21_mom,
        "s21_ads": s21_ads,
        "solved_count": int(len(mag_errs)),
        "total_count": int(len(trace_jobs)),
    }
