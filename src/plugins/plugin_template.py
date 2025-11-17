"""
Plugin template for HYPRIL

Copy this file to `src/plugins/` and change the file name to your plugin's name.
Edit only the `your_function(window, *args, **kwargs)` body — leave the rest intact.

Expected plugin API:
- Expose a callable `register(window)` which the application will call with
  the `ImageViewerWindow` instance. `register` should wire your function
  into the UI (for example by adding an action to the Plugins menu).

Notes:
- `QAction` lives in `PySide6.QtGui`; `QMessageBox` is in `PySide6.QtWidgets`.
- Keep plugin code trusted — these run in-process and can execute arbitrary Python.
"""

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMessageBox
import logging

# Optional metadata
PLUGIN_NAME = "My Plugin"
PLUGIN_DESCRIPTION = "Describe what your plugin does here."
PLUGIN_VERSION = "0.1"


def your_function(window, *args, **kwargs):
    """Implement your plugin logic here.

    The `window` parameter is the `ImageViewerWindow` instance. Use only public
    APIs (e.g. `window.layers`, `window._refresh_layer_list()`,
    `window._update_display()`) unless you intentionally need private internals.

    Keep this function focused: do not block the UI for long-running work — if
    you need to run heavy tasks, start a background thread/process and update
    the UI when done.

    Example minimal implementation (commented):

        # show a message box
        QMessageBox.information(window, PLUGIN_NAME, "Hello from plugin")

    Replace the body below with your code.
    """
    # ---- START: developer edits go here ----
    # Example default behavior — simply notify user. Replace this with your logic.
    QMessageBox.information(window, PLUGIN_NAME, f"{PLUGIN_NAME} v{PLUGIN_VERSION} executed.")
    # ----  END: developer edits go here  ----


def register(window):
    """Called by HYPRIL to register the plugin with the main window.

    This function wires the `your_function` into the UI by adding an action
    under the existing `Plugins` menu if present, otherwise the main menu bar.
    You do not need to edit this function in most cases.
    """
    try:
        action = QAction(PLUGIN_NAME, window)
        action.setStatusTip(PLUGIN_DESCRIPTION)
        action.triggered.connect(lambda: your_function(window))

        # Try to find an existing 'Plugins' menu
        plugins_menu = None
        for act in window.menu_bar.actions():
            menu = act.menu()
            if menu and menu.title() == 'Plugins':
                plugins_menu = menu
                break

        if plugins_menu is not None:
            plugins_menu.addAction(action)
        else:
            # fallback: add to main menu bar
            window.menu_bar.addAction(action)

        logging.info(f"Plugin registered: {PLUGIN_NAME}")

    except Exception as e:
        logging.exception("Failed to register plugin: %s", e)
        # Avoid raising — registration failures are handled by the host
