"""Elevation-coordinate mappings for primary-relative delay MultiView.

The solver always fits an intercept-free plane through the primary calibrator.
These helpers only choose the first design-matrix coordinate; the azimuth
coordinate remains a wrapped degree difference.  Linear elevation offsets are
also used separately to compute true angular separation for optional
separation-dependent weighting.
"""

import numpy as np


LINEAR_ELEVATION_MAPPING = "linear"
COSECANT_ELEVATION_MAPPING = "cosecant"
ELEVATION_MAPPING_CHOICES = (LINEAR_ELEVATION_MAPPING, COSECANT_ELEVATION_MAPPING)


def normalize_elevation_mapping(value):
    """Return a supported elevation mapping name, falling back to ``linear``.

    Config files and saved GUI state are user-editable, so invalid strings must
    not stop a solve.  The public rule is deliberately forgiving: only the two
    supported names are accepted, and everything else becomes ``linear``.
    """
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ELEVATION_MAPPING_CHOICES:
            return normalized
    return LINEAR_ELEVATION_MAPPING


def mapped_elevation_offset(source_alt_deg, primary_alt_deg, mapping=LINEAR_ELEVATION_MAPPING):
    """Compute the primary-relative elevation coordinate used by the solver.

    ``linear`` returns the ordinary elevation difference in degrees.  ``cosecant``
    returns the raw slant-path mapping difference, ``csc(el_source) -
    csc(el_primary)``.  Any invalid mapping name is treated as ``linear``.  The
    raw cosecant form intentionally changes the gradient unit from seconds per
    degree to seconds per cosecant-unit.
    """
    source_alt = np.asarray(source_alt_deg, dtype=float)
    primary_alt = np.asarray(primary_alt_deg, dtype=float)
    if normalize_elevation_mapping(mapping) == COSECANT_ELEVATION_MAPPING:
        with np.errstate(divide="ignore", invalid="ignore"):
            return 1.0 / np.sin(np.deg2rad(source_alt)) - 1.0 / np.sin(np.deg2rad(primary_alt))
    return source_alt - primary_alt


def elevation_coordinate_label(mapping=LINEAR_ELEVATION_MAPPING):
    """Return a human-readable label for the first solver coordinate."""
    if normalize_elevation_mapping(mapping) == COSECANT_ELEVATION_MAPPING:
        return "cosecant elevation"
    return "elevation"


def elevation_axis_label(mapping=LINEAR_ELEVATION_MAPPING):
    """Return the x-axis label for 3D slice plots."""
    if normalize_elevation_mapping(mapping) == COSECANT_ELEVATION_MAPPING:
        return "Delta cosecant elevation"
    return "Delta elevation (deg)"


def gradient_axis_label(mapping=LINEAR_ELEVATION_MAPPING):
    """Return the gradient y-axis label for root-window plots."""
    if normalize_elevation_mapping(mapping) == COSECANT_ELEVATION_MAPPING:
        return "delay gradient (el: ps/csc-unit, az: ps/deg)"
    return "delay gradient (ps/deg)"
