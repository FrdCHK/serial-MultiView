"""Shared defaults for the AltAz Viterbi-Kalman MultiView solver."""

import copy


SOLVER_DEFAULTS = {
    "kalman_factor": 1.0e-14,
    "unit_weight_variance": 4.0e-22,
    "rts_smoothing": True,
    "viterbi_integer_states": 3,
    "viterbi_max_jump": 1,
    "viterbi_jump_penalty": 25.0,
    "viterbi_huber_c": 3.0,
    "viterbi_z_out": 4.0,
}

FIXED_SOLVER_DEFAULTS = {
    "viterbi_robust": True,
    "viterbi_max_outlier_iterations": 2,
    "viterbi_p0_gradient": None,
}

ADJUST_DEFAULTS = {
    "viterbi_fix_initial_enabled": False,
    "viterbi_fix_initial_values": {},
}

SOLVER_KEYS = list(SOLVER_DEFAULTS.keys())


def apply_solver_defaults(config):
    for key, value in SOLVER_DEFAULTS.items():
        config.setdefault(key, copy.deepcopy(value))
    for key, value in ADJUST_DEFAULTS.items():
        config.setdefault(key, copy.deepcopy(value))
    return config


def _initial_integer_setting(config):
    if not bool(config.get("viterbi_fix_initial_enabled", False)):
        return 0
    values = config.get("viterbi_fix_initial_values", {})
    if values is None:
        return {}
    return {int(key): int(value) for key, value in dict(values).items()}


def solver_kwargs(config):
    apply_solver_defaults(config)
    kwargs = {key: config[key] for key in SOLVER_KEYS}
    kwargs.update(copy.deepcopy(FIXED_SOLVER_DEFAULTS))
    kwargs["viterbi_fix_initial_integer"] = _initial_integer_setting(config)
    return kwargs
