"""
Test harness plugin demonstrating common plugin tasks using HostAPI.
- Adds two actions under Plugins:
  * "Test: Add Sample Layer" — creates a small random layer and inserts it
  * "Test: Print Layer Names" — prints current layer names to the log
"""
from PySide6.QtGui import QAction
import numpy as np
import logging

try:
    from plugin_api import HostAPI
except Exception:
    HostAPI = None

PLUGIN_NAME = "Test Harness Plugin"


def _add_sample_layer(host_or_window):
    # Accept either HostAPI or raw window for compatibility
    if HostAPI is not None and isinstance(host_or_window, HostAPI):
        host = host_or_window
    else:
        # assume window
        host = HostAPI(host_or_window) if HostAPI else None

    if host is None:
        logging.warning("No HostAPI available; cannot add sample layer")
        return

    h, w = 64, 64
    band_count = 3
    data = np.random.rand(h, w, band_count).astype(np.float32)
    host.add_layer(data, name="Plugin Sample Layer", band_names=["R", "G", "B"]) 
    host.show_message("Sample layer added by plugin", "Test Harness")


def _print_layer_names(host_or_window):
    if HostAPI is not None and isinstance(host_or_window, HostAPI):
        host = host_or_window
    else:
        host = HostAPI(host_or_window) if HostAPI else None
    if host is None:
        logging.warning("No HostAPI available; cannot list layers")
        return
    names = [lyr.get('name') for lyr in host.list_layers()]
    logging.info("Current layers (from plugin): %s", names)
    host.show_message("Layers: " + ", ".join(names), "Test Harness")


def register(window):
    # Prefer HostAPI if available
    host = HostAPI(window) if HostAPI else None

    def add_action(text, func):
        if host:
            host.add_action(text, lambda: func(host), tooltip=text)
        else:
            # fallback: add raw action bound to window
            act = QAction(text, window)
            act.triggered.connect(lambda: func(window))
            window.menu_bar.addAction(act)

    add_action("Test: Add Sample Layer", _add_sample_layer)
    add_action("Test: Print Layer Names", _print_layer_names)

    logging.info("Test harness plugin registered")
