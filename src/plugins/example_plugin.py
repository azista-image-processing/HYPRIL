"""
Example plugin for HYPRIL

Drop this file into `src/plugins/` (already created by this change).
The plugin API: implement `register(window)` where `window` is the
`ImageViewerWindow` instance. Use `window.menu_bar` to add items or
`window` public API to interact with the host application.

This example registers a simple action that shows a message box.
"""

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMessageBox

PLUGIN_NAME = "Example Plugin"
PLUGIN_DESCRIPTION = "Demo plugin that adds a simple action to the UI."


def register(window):
    """Register this plugin with the main window.

    The function will try to add the action under the 'Plugins' menu
    (if present). If not found, it appends the action to the main menu bar.
    """
    try:
        def on_triggered():
            QMessageBox.information(window, PLUGIN_NAME, "Example plugin executed successfully.")

        action = QAction(f"{PLUGIN_NAME} Action", window)
        action.triggered.connect(on_triggered)

        # Try to find an existing 'Plugins' QMenu and add the action there
        plugins_menu = None
        for act in window.menu_bar.actions():
            menu = act.menu()
            if menu and menu.title() == "Plugins":
                plugins_menu = menu
                break

        if plugins_menu is not None:
            plugins_menu.addAction(action)
        else:
            # Fallback: add directly to menu bar
            window.menu_bar.addAction(action)

    except Exception as e:
        import logging
        logging.error(f"Example plugin failed to register: {e}", exc_info=True)
