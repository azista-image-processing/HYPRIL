"""
Safe plugin host API for HYPRIL

Plugins can import `HostAPI` from this module to access a limited set of
application functionality without touching the full `ImageViewerWindow` API.

Example:

    from plugin_api import HostAPI

    def register(window):
        host = HostAPI(window)
        host.add_action("Do Something", lambda: host.show_message("Hello"))

The HostAPI intentionally exposes only a small surface: listing layers,
adding simple in-memory layers, adding actions to the Plugins menu (or menu bar),
and showing a message.

Security: HostAPI does not sandbox plugin code — it only reduces the surface
area by convenience. Plugins still run in-process and must be trusted.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional, Callable
import logging
import numpy as np
import os
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMessageBox


class HostAPI:
    def __init__(self, window):
        # Keep a reference to the main window but avoid documenting internals here
        self._window = window

    # Read-only layer access
    def list_layers(self) -> List[Dict[str, Any]]:
        """Return the live list of layers (plugins should treat this as read-only)."""
        return self._window.layers

    def find_layer_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        for lyr in self._window.layers:
            if lyr.get("name") == name:
                return lyr
        return None

    # Add a simple in-memory layer (suitable for small test layers)
    def add_layer(self, data: np.ndarray, name: str = "Plugin Layer", band_names: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        if not isinstance(data, np.ndarray):
            raise ValueError("data must be a numpy.ndarray")
        if data.ndim == 2:
            data = data[:, :, None]
        band_names = band_names or [f"Band {i+1}" for i in range(data.shape[2])]
        meta = metadata.copy() if metadata else {}
        new_layer = {
            "name": name,
            "data": data,
            "band_names": band_names,
            "metadata": meta,
            "geotransform": None,
            "projection": None,
            "visible": True,
        }
        self._window.layers.insert(0, new_layer)
        # Refresh UI
        try:
            self._window._refresh_layer_list()
            self._window.layer_list.setCurrentRow(0)
            self._window._update_band_combos_for_active_layer()
            self._window._update_display()
        except Exception:
            logging.exception("HostAPI: failed to refresh UI after adding layer")

    # Convenience: add an action to the Plugins menu (or to the menu bar)
    def add_action(self, text: str, callback: Callable, tooltip: str = "", menu_title: str = "Plugins") -> QAction:
        action = QAction(text, self._window)
        if tooltip:
            action.setStatusTip(tooltip)
        action.triggered.connect(callback)

        # Find the menu with menu_title
        menu_found = None
        for act in self._window.menu_bar.actions():
            menu = act.menu()
            if menu and menu.title() == menu_title:
                menu_found = menu
                break
        if menu_found is not None:
            menu_found.addAction(action)
        else:
            # fallback: add to menubar
            self._window.menu_bar.addAction(action)
        return action

    def show_message(self, text: str, title: str = "HYPRIL") -> None:
        try:
            QMessageBox.information(self._window, title, text)
        except Exception:
            logging.exception("HostAPI: failed to show message")

    def refresh_ui(self) -> None:
        try:
            self._window._refresh_layer_list()
            self._window._update_band_combos_for_active_layer()
            self._window._update_display()
        except Exception:
            logging.exception("HostAPI: failed to refresh UI")


# Backwards compatibility: some plugins import plugin_api.HostAPI as HostAPI
__all__ = ["HostAPI"]
