"""
Layer Stacking plugin for HYPRIL

Provides a dialog to select multiple existing layers and stack them
into a single multi-band layer. The plugin registers a "Stack Layers..."
action under the Plugins menu.

Plugin API: implement `register(window)` which receives the main
`ImageViewerWindow` instance.
"""
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QMessageBox, QInputDialog
)
import numpy as np
import logging

PLUGIN_NAME = "Layer Stacker"
PLUGIN_DESCRIPTION = "Stack selected layers into a single multi-band layer."


class LayerStackDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setWindowTitle("Stack Layers")
        self.setMinimumSize(400, 400)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Select layers to include in the stack (top -> bottom order):"))

        self.list_widget = QListWidget()
        # populate with current layers (top-first)
        for lyr in self.window.layers:
            item = QListWidgetItem(lyr.get("name", "Layer"))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
            item.setCheckState(Qt.Unchecked)
            self.list_widget.addItem(item)
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        self.btn_move_up = QPushButton("Move Up")
        self.btn_move_up.clicked.connect(self.move_up)
        btn_row.addWidget(self.btn_move_up)

        self.btn_move_down = QPushButton("Move Down")
        self.btn_move_down.clicked.connect(self.move_down)
        btn_row.addWidget(self.btn_move_down)

        btn_row.addStretch()

        self.btn_stack = QPushButton("Stack Selected")
        self.btn_stack.clicked.connect(self.stack_selected)
        btn_row.addWidget(self.btn_stack)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)

        layout.addLayout(btn_row)

    def move_up(self):
        row = self.list_widget.currentRow()
        if row <= 0:
            return
        item = self.list_widget.takeItem(row)
        self.list_widget.insertItem(row - 1, item)
        self.list_widget.setCurrentRow(row - 1)

    def move_down(self):
        row = self.list_widget.currentRow()
        if row < 0 or row >= self.list_widget.count() - 1:
            return
        item = self.list_widget.takeItem(row)
        self.list_widget.insertItem(row + 1, item)
        self.list_widget.setCurrentRow(row + 1)

    def stack_selected(self):
        # Gather indices in the order of items (top-first)
        selected_indices = []
        for i in range(self.list_widget.count()):
            it = self.list_widget.item(i)
            if it.checkState() == Qt.Checked:
                selected_indices.append(i)

        if len(selected_indices) < 1:
            QMessageBox.information(self, "No layers selected", "Please select at least one layer to stack.")
            return

        try:
            arrays = []
            band_names = []
            shapes = None
            dtypes = []

            for idx in selected_indices:
                layer = self.window.layers[idx]
                data = layer.get("data")
                if data is None:
                    raise ValueError(f"Layer '{layer.get('name')}' has no data")

                arr = np.asarray(data)
                # Ensure HxWxB
                if arr.ndim == 2:
                    arr = arr[:, :, None]
                elif arr.ndim == 3:
                    pass
                else:
                    raise ValueError(f"Unsupported layer shape: {arr.shape}")

                if shapes is None:
                    shapes = arr.shape[:2]
                else:
                    if arr.shape[:2] != shapes:
                        raise ValueError(f"Layer '{layer.get('name')}' has incompatible shape {arr.shape[:2]}, expected {shapes}")

                arrays.append(arr)
                dtypes.append(arr.dtype)

                # collect band names (prefix with layer name for clarity)
                ln = layer.get('name', 'Layer')
                bn = layer.get('band_names', [])
                if bn and len(bn) == arr.shape[2]:
                    prefixed = [f"{ln}:{b}" for b in bn]
                else:
                    prefixed = [f"{ln}:Band {i+1}" for i in range(arr.shape[2])]
                band_names.extend(prefixed)

            # Use a common dtype (promote if necessary)
            # common_dtype = np.find_common_type(dtypes, [])
            common_dtype = np.result_type(*dtypes)
            arrays = [a.astype(common_dtype, copy=False) for a in arrays]

            # Concatenate along band axis
            stacked = np.concatenate(arrays, axis=2)

            # Ask for output layer name
            name, ok = QInputDialog.getText(self, "Stack Name", "Name for stacked layer:", text="Stacked Layer")
            if not ok or not name:
                return

            # Build metadata: copy from first selected layer
            first_layer = self.window.layers[selected_indices[0]]
            meta = first_layer.get('metadata', {}).copy() if first_layer.get('metadata') else {}
            meta['band_count'] = stacked.shape[2]

            new_layer = {
                'name': name,
                'data': stacked,
                'band_names': band_names,
                'metadata': meta,
                'geotransform': first_layer.get('geotransform'),
                'projection': first_layer.get('projection'),
                'visible': True
            }

            # Insert to top and refresh UI
            self.window.layers.insert(0, new_layer)
            self.window._refresh_layer_list()
            self.window.layer_list.setCurrentRow(0)
            self.window._update_band_combos_for_active_layer()
            self.window._update_display()

            QMessageBox.information(self, "Stack Complete", f"Created stacked layer '{name}' with {stacked.shape[2]} bands.")
            self.accept()

        except Exception as e:
            logging.exception("Error stacking layers: %s", e)
            QMessageBox.critical(self, "Stack Failed", f"Could not stack layers: {e}")


def register(window):
    """Register the plugin with the main window: add action under Plugins menu."""
    try:
        # action = QAction("Stack Layers...", window)
        
        action = QAction(PLUGIN_NAME, window)
        action.setStatusTip(PLUGIN_DESCRIPTION)

        def on_triggered():
            dlg = LayerStackDialog(window)
            dlg.exec()

        action.triggered.connect(on_triggered)

        # Try to find 'Plugins' menu; if found add the action there, else add to menu bar
        plugins_menu = None
        for act in window.menu_bar.actions():
            menu = act.menu()
            if menu and menu.title() == 'Plugins':
                plugins_menu = menu
                break

        if plugins_menu is not None:
            plugins_menu.addAction(action)
        else:
            window.menu_bar.addAction(action)

    except Exception as e:
        logging.exception("Failed to register Layer Stacker plugin: %s", e)
