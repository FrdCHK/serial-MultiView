# Custom Plugin Development

## Where to put your plugin
- Create a module under `plugin/custom/<your_plugin>/`.
- Add an `__init__.py` file in the module directory.
- Register it in `plugin/custom/__init__.py`:
```
from . import your_plugin
```

## Minimal plugin skeleton
```
"""
Your plugin description.
@Author: Your Name
@DATE  : YYYY/MM/DD
"""
from core.Plugin import Plugin
from core.Context import Context

class YourPlugin(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Short description and required params."

    def run(self, context: Context) -> bool:
        context.logger.info("Start YourPlugin")
        # do work here
        context.logger.info("YourPlugin finished")
        return True
```

## Style conventions
- Use module docstrings with `@Author` and `@DATE`.
- Prefer `context.logger.info()` for high‑level progress.
- Use `context.logger.debug()` for detailed output.
- Validate required inputs early and return `False` on failure.

## Using the context
- Read common values from `context.get_context()`, for example:
  - `context.get_context()["config"]`
  - `context.get_context()["targets"]`
- Write results back with `context.edit_context({...})`.

## Adding parameters
- Parameters are passed from the control file:
```
plugins:
  - name: YourPlugin
    params:
      param1: value1
      param2: value2
```

## Debugging
- Enable debug logs in your logger configuration if needed.
- Keep log output deterministic and minimal for batch runs.
