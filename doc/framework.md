# Pipeline Framework

## Concepts
- **Control file**: YAML that declares configuration and a list of plugins to run in order.
- **Context**: shared dictionary passed to every plugin. It stores config, catalog info, and intermediate results.
- **Plugin**: a Python class derived from `core.Plugin` with a `run(context)` method.

## Control file structure
```
config:
  # imported from config.yaml
  ...
plugins:
  - name: AipsCatalog
    params: {}
  - name: GetObsInfo
    params:
      inname: EXP1
      inclass: UVDATA
      indisk: 1
      in_cat_ident: ORIGIN
```

## Context lifecycle
1. `main.py` loads the control file and creates `Context`.
2. `Context` optionally loads `context.yaml` from `config.workspace` to resume prior state.
3. Plugins run sequentially and can read/write `context`.

Key fields often used:
- `config`: configuration dictionary from control file
- `targets`, `calibrators`, `antennas`: observation metadata
- `aips_catalog`: internal record of AIPS catalog and extensions
- `ref_ant`: selected reference antenna

## Plugin loading
All plugins under `plugin/` are loaded dynamically at startup. The `plugins` list in the control file controls execution order.

## Variable substitution
Parameters can reference values in context with `$a:b:c$` syntax. For example:
```
refant: $ref_ant:ID$
```
This is resolved by `util/parse_context_variable.py` during AIPS task execution.

## AIPS catalog tracking
`plugin/core/aips_catalog/AipsCatalog.py` keeps track of AIPS catalogs and extension tables (SN/CL). This allows later tasks to look up the correct versions by identifier.

## Logging
- Use `context.logger.info()` for user‑visible progress.
- Use `context.logger.debug()` for verbose or per‑row details.

