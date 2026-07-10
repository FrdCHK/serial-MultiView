"""Shared defaults and GUI-to-solver parameter translation.

The GUI and YAML files intentionally expose short parameter names such as
``integer_states`` and ``max_jump``.  The numerical solver keeps the longer
``viterbi_*`` argument names because those names describe the algorithmic
role at the call site in :mod:`plugin.core.mv.Antenna`.

Only relative covariance scaling matters for the current MV outputs, so a few
low-level controls stay fixed here instead of appearing in the config window.
"""

import copy


SOLVER_DEFAULTS = {
    "kalman_factor": 1.0e-14,
    "rts_smoothing": True,
    "integer_states": 3,
    "max_jump": 1,
    "jump_penalty": 25.0,
    "huber_c": 3.0,
    "z_out": 4.0,
}

FIXED_SOLVER_DEFAULTS = {
    "unit_weight_variance": 4.0e-22,
    "viterbi_robust": True,
    "viterbi_max_outlier_iterations": 2,
    "viterbi_p0_gradient": None,
}

ADJUST_DEFAULTS = {
    "fix_initial_enabled": False,
    "fix_initial_values": {},
}

SOLVER_KEYS = list(SOLVER_DEFAULTS.keys())

# Older saved configs used viterbi_* public names.  Keep loading them so users
# can reopen old SAVE directories without hand-editing YAML files.
LEGACY_CONFIG_KEYS = {
    "viterbi_integer_states": "integer_states",
    "viterbi_max_jump": "max_jump",
    "viterbi_jump_penalty": "jump_penalty",
    "viterbi_huber_c": "huber_c",
    "viterbi_z_out": "z_out",
    "viterbi_fix_initial_enabled": "fix_initial_enabled",
    "viterbi_fix_initial_values": "fix_initial_values",
}

SOLVER_ARG_NAMES = {
    "integer_states": "viterbi_integer_states",
    "max_jump": "viterbi_max_jump",
    "jump_penalty": "viterbi_jump_penalty",
    "huber_c": "viterbi_huber_c",
    "z_out": "viterbi_z_out",
}


def apply_solver_defaults(config):
    """Mutate ``config`` in place so it contains the current public keys.

    Returns the same dict for convenient call chaining.  Fixed solver controls
    are removed from user config because they are no longer meant to be edited
    through YAML or the config window.
    """
    for key in FIXED_SOLVER_DEFAULTS:
        config.pop(key, None)
    for legacy_key, new_key in LEGACY_CONFIG_KEYS.items():
        if legacy_key in config:
            config.setdefault(new_key, config.pop(legacy_key))
    for key, value in SOLVER_DEFAULTS.items():
        config.setdefault(key, copy.deepcopy(value))
    for key, value in ADJUST_DEFAULTS.items():
        config.setdefault(key, copy.deepcopy(value))
    return config


def _initial_integer_setting(config):
    """Return the initial ambiguity constraint expected by the solver.

    ``fix_initial_enabled=False`` means every secondary calibrator starts with
    ambiguity integer zero.  When enabled, ``fix_initial_values`` may contain a
    sparse per-calibrator map; missing calibrators also default to zero.
    """
    if not bool(config.get("fix_initial_enabled", False)):
        return 0
    values = config.get("fix_initial_values", {})
    if values is None:
        return {}
    return {int(key): int(value) for key, value in dict(values).items()}


def solver_kwargs(config):
    """Build keyword arguments for :meth:`Antenna.delay_multiview`.

    This is the single bridge from persisted/GUI config to the solver-facing
    API.  Keeping it centralized prevents stale names from spreading through
    GUI callbacks and template rendering.
    """
    apply_solver_defaults(config)
    kwargs = {SOLVER_ARG_NAMES.get(key, key): config[key] for key in SOLVER_KEYS}
    kwargs.update(copy.deepcopy(FIXED_SOLVER_DEFAULTS))
    kwargs["viterbi_fix_initial_integer"] = _initial_integer_setting(config)
    return kwargs
