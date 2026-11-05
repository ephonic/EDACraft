"""Volume quadrature of nodal FE polarization; not terminal charge extraction."""

from __future__ import annotations

import math

import numpy as np


def _real_array(value, name, *, allow_bool=False):
    array = np.asarray(value)
    if array.dtype.kind not in ("biuf" if allow_bool else "iuf"):
        raise ValueError(f"{name} must contain real numeric values")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain finite values")
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        converted = array.astype(float, copy=False)
    if not np.all(np.isfinite(converted)):
        raise ValueError(f"{name} overflowed float64 conversion")
    if np.any((array != 0) & (converted == 0)):
        raise ValueError(f"{name} underflowed float64 conversion")
    return converted


def _weighted_polarization(values, weights, total):
    # Combine exponents before rounding a cell's contribution. Computing
    # weight/total first can underflow even when weight*P/total is measurable.
    weight_mantissa, weight_exponent = np.frexp(weights)
    value_mantissa, value_exponent = np.frexp(values)
    total_mantissa, total_exponent = math.frexp(total)
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        terms = np.ldexp(weight_mantissa * value_mantissa / total_mantissa,
                         weight_exponent + value_exponent - total_exponent)
    exact_required = (not np.all(np.isfinite(terms))
                      or np.any((values != 0) & (np.abs(terms) < np.finfo(float).tiny)))
    if not exact_required:
        try:
            mean = math.fsum(terms)
            mean_abs = math.fsum(np.abs(terms))
        except OverflowError:
            exact_required = True
        else:
            # Rounded per-cell products cannot establish a tiny residual of
            # large opposite domains. Resolve that case from exact inputs.
            exact_required = (mean_abs > 0 and
                              abs(mean) <= 16*np.finfo(float).eps*mean_abs)
    if exact_required:
        # Portable fallback for subnormal contributions and cancellation;
        # it does not depend on extended precision being available.
        # Every finite binary64 value is an integer multiple of 2**-1074.
        # Accumulate products in units of 2**-2148 without repeatedly
        # reducing rational denominators for a large domain population.
        denominator = numerator = absolute_numerator = 0
        for weight, value in zip(weights, values):
            weight_numerator, weight_denominator = float(weight).as_integer_ratio()
            value_numerator, value_denominator = float(value).as_integer_ratio()
            weight_power = weight_denominator.bit_length() - 1
            value_power = value_denominator.bit_length() - 1
            product = ((weight_numerator * value_numerator)
                       << (2148 - weight_power - value_power))
            denominator += weight_numerator << (1074 - weight_power)
            numerator += product
            absolute_numerator += abs(product)
        mean = numerator / (denominator << 1074)
        mean_abs = absolute_numerator / (denominator << 1074)
    return mean, mean_abs


def polarization_readout(polarization, mesh, *, polar_axis=0, fe_mask=None):
    """Return FE-volume-weighted axial polarization and spatial diagnostics.

    ``mesh.fields['control_volume']`` supplies explicit positive nodal volumes
    in m^3 (also usable for nonuniform meshes). Otherwise ``control_volumes()``
    must supply geometry-derived volumes. No equal-node fallback is allowed.
    Optional ``fe_volume_fraction`` in [0, 1] describes the FE portion of each
    dual cell; without it the FE-node mask selects whole dual cells. This does
    not infer cut-cell geometry or establish physical/material validity.
    """
    if (isinstance(polar_axis, (bool, np.bool_))
            or not isinstance(polar_axis, (int, np.integer)) or polar_axis not in (0, 1, 2)):
        raise ValueError("polar axis must be an integer 0, 1 or 2")
    count = mesh.npts() if hasattr(mesh, "npts") else mesh.num_nodes
    if (isinstance(count, (bool, np.bool_))
            or not isinstance(count, (int, np.integer)) or count < 1):
        raise ValueError("mesh node count must be a positive integer")
    count = int(count)
    P = _real_array(polarization, "polarization")
    if P.shape not in ((count, 3), (3 * count,)) or not np.all(np.isfinite(P)):
        raise ValueError("polarization must contain one finite 3-vector per mesh node")
    P = P.reshape(count, 3)
    fields = mesh.fields
    if fe_mask is None:
        alpha = fields.get("fe_alpha")
        if alpha is None:
            fe_mask = np.ones(count, dtype=bool)
        else:
            alpha = _real_array(alpha, "fe_alpha").ravel()
            if alpha.size != count or not np.all(np.isfinite(alpha)):
                raise ValueError("fe_alpha must contain one finite value per node")
            fe_mask = alpha != 0
    mask = _real_array(fe_mask, "FE mask", allow_bool=True).ravel()
    if (mask.size != count or not np.all(np.isfinite(mask))
            or not np.all((mask == 0) | (mask == 1))):
        raise ValueError("FE mask must contain one boolean or binary value per node")
    mask = mask.astype(bool)
    if "control_volume" in fields:
        volumes = fields["control_volume"]
        volume_source = "explicit_control_volume"
    elif callable(getattr(mesh, "control_volumes", None)):
        volumes = mesh.control_volumes()
        volume_source = "mesh_control_volumes"
    else:
        raise ValueError("polarization readout requires nodal control volumes")
    volumes = _real_array(volumes, "control_volume").ravel()
    if (volumes.size != count or not np.all(np.isfinite(volumes))
            or np.any(volumes <= 0)):
        raise ValueError("control_volume must contain one finite positive m^3 value per node")
    fraction = _real_array(fields.get("fe_volume_fraction", np.ones(count)),
                           "fe_volume_fraction").ravel()
    if (fraction.size != count or not np.all(np.isfinite(fraction))
            or np.any(fraction < 0) or np.any(fraction > 1)):
        raise ValueError("fe_volume_fraction must contain one finite value in [0, 1] per node")
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        weights = volumes * fraction * mask
    try:
        total = math.fsum(weights)
    except OverflowError as exc:
        raise ValueError("polarization readout requires a finite positive FE volume") from exc
    # A positive cell portion that rounded to zero must not silently disappear.
    if np.any(mask & (fraction > 0) & (weights == 0)):
        raise ValueError("FE cell volume underflowed")
    if not np.isfinite(total) or total <= 0:
        raise ValueError("polarization readout requires a finite positive FE volume")
    selected = weights > 0
    values = P[selected, polar_axis]
    mean, mean_abs = _weighted_polarization(values, weights[selected], total)
    if not np.isfinite(mean) or not np.isfinite(mean_abs):
        raise ValueError("polarization quadrature overflowed")
    return {
        "mean_polarization": mean,
        "mean_absolute_polarization": mean_abs,
        "min_polarization": float(np.min(values)),
        "max_polarization": float(np.max(values)),
        "fe_volume_m3": total,
        "contributing_nodes": int(np.count_nonzero(selected)),
        "polar_axis": int(polar_axis),
        "polarization_units": "C/m^2",
        "weighting": "FE_control_volume",
        "volume_source": volume_source,
        "interface_geometry": ("explicit_FE_volume_fraction"
                               if "fe_volume_fraction" in fields
                               else "whole_masked_dual_cells"),
        "terminal_charge_validated": False,
        "physical_validated": False,
    }
