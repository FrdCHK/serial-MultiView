Plugins should be in a form of modules, that is, a directory containing a __init__.py file.
It should contain at least one class that inherits from core.Plugin.
The class should have a run method, which takes a context object as argument.
The run method should return a boolean value, indicating whether the plugin succeeded (True) or failed (False), and the pipeline should continue (True) or stop (False).
It is recommended to mention which parameters (and/or other plugins) are required by the plugin in the docstring and/or the class description.
Put the plugin in the plugin/custom directory, and add it to plugin/custom/__init__.py:
```
from . import your_plugin_name
```
Then it will be loaded automatically.
To call it in your pipeline, add it to the configuration file. Extra parameters are optional:
```
plugins:
  - name: Class1
    params: {}
  - name: Class2
    params:
      param1: value1
      param2: value2
```
The plugin will be called in the order they are listed in the configuration file.

A shared context is available to all plugins.
It is initialized with the configuration file and passed to all plugins.
It can be readed and modified by all plugins.

You should use logger to log messages, for example:
```
context.logger.info("This is an info message")
```
Debug level messages are only outputed to the log file, while other messages are outputed to both the log file and the console.
