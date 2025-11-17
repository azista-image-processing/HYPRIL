HYPRIL Plugins — README
========================

Overview
--------
This folder contains plugins for HYPRIL. Plugins are discovered automatically
from this `src/plugins/` folder at application startup and are loaded into the
main window.

Plugin API
----------
- Plugin entrypoint: implement a `register(window)` function in your plugin.
- Recommended: use the `HostAPI` helper to interact with the application safely:

    from plugin_api import HostAPI

    def register(window):
        host = HostAPI(window)
        host.add_action('Do Something', lambda: host.show_message('Hello'))

HostAPI features
----------------
- `list_layers()` — get the current layers list (read-only unless you modify it)
- `find_layer_by_name(name)` — find a layer dict
- `add_layer(data, name, band_names, metadata)` — insert a new in-memory layer (small arrays only)
- `add_action(text, callback, tooltip='', menu_title='Plugins')` — add an action to the Plugins menu
- `show_message(text, title='HYPRIL')` — display a message box
- `refresh_ui()` — request the viewer to refresh its layer list and display

Security
--------
Plugins run in-process and can execute arbitrary code. Only install plugins you
trust. `HostAPI` reduces the number of steps needed to interact with the UI but
is not a sandbox.

Creating plugins
----------------
1. Copy `plugin_template.py` to `src/plugins/your_plugin.py`.
2. Edit `your_function(window, *args, **kwargs)` with your logic.
3. Add any UI wiring in `register(window)` if needed (the template already
   wires an action to the Plugins menu).

Testing
-------
- `test_harness_plugin.py` demonstrates adding an in-memory sample layer and
  listing layers. It is auto-loaded at startup.

Support
-------
If you want a plugin manager (enable/disable/uninstall) or a remote plugin
sandbox, open an issue and we can extend the API.
