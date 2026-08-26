"""Lightweight compatibility helpers for public MultiView solver settings."""


LEGACY_CONFIG_KEYS = {
    "viterbi_integer_states": "integer_states",
    "viterbi_max_jump": "max_jump",
    "viterbi_jump_penalty": "jump_penalty",
    "viterbi_huber_c": "huber_c",
    "viterbi_z_out": "z_out",
    "viterbi_fix_initial_enabled": "fix_initial_enabled",
    "viterbi_fix_initial_values": "fix_initial_values",
}


def solver_value_missing(value):
    """Return whether a public solver value should fall back to a default."""

    return value is None or (
        isinstance(value, str)
        and value.strip().lower() in ("", "none", "null")
    )


def migrate_legacy_solver_config(config):
    """Replace legacy ``viterbi_*`` public keys with their current names.

    A valid current key wins when both spellings are present.  A legacy value
    fills a missing or blank current key, and blank legacy values are left for
    the normal defaulting pass instead of being rendered as YAML nulls.
    """

    for legacy_key, new_key in LEGACY_CONFIG_KEYS.items():
        if legacy_key not in config:
            continue
        legacy_value = config.pop(legacy_key)
        if new_key not in config or solver_value_missing(config[new_key]):
            if solver_value_missing(legacy_value):
                config.pop(new_key, None)
            else:
                config[new_key] = legacy_value
    return config
