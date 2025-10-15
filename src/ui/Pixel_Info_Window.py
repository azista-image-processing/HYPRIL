
# src/ui/Pixel_Info_Window.py

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# --- PySide6 Imports ---
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QFormLayout, 
                               QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
                               QWidget, QComboBox, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt

# --- Geospatial and Plotting Imports ---
from osgeo import gdal, osr
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

# --- Optional Import for Interactive Plot Cursors ---
try:
    import mplcursors
    MPLCURSORS_AVAILABLE = True
except ImportError:
    MPLCURSORS_AVAILABLE = False
    print("Warning: 'mplcursors' not found. Interactive plot annotations will be disabled.")


class PixelInfoWindow(QDialog):
    def __init__(self, file_name, image_data, band_names, metadata, geotransform, projection, x, y, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pixel Inspector")
        self.setMinimumSize(650, 800)

        # --- Validate and Store Data ---
        if not isinstance(image_data, np.ndarray) or image_data.ndim != 3:
            raise ValueError("image_data must be a 3D NumPy array")
        
        self.file_name = file_name
        self.image_data = image_data
        self.band_names = band_names if band_names else [f"Band {i+1}" for i in range(image_data.shape[2])]
        self.metadata = metadata or {}
        self.geotransform = geotransform
        self.projection = projection
        self.wavelengths = self._parse_wavelengths(self.metadata)
        self.wavelength_units = self.metadata.get("wavelength_units", "nm")
        self.x = x
        self.y = y
        self.cursor = None # For mplcursors
        print(f"Pixel Inspector initialized for {file_name} at ({x}, {y}) with projection {self.projection}")


        # --- Initialize UI Elements ---
        self._init_ui_elements()
        self._init_layout()
        
        # --- Final Setup ---
        self.update_pixel_info(x, y)
        self.update_view_mode() # Set initial view

    def _init_ui_elements(self):
        """Initializes all QWidget members."""
        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItems(["Spectral Plot", "Pixel Values"])
        self.view_mode_combo.currentIndexChanged.connect(self.update_view_mode)
        
        self.coords_edit = QLineEdit(readOnly=True)
        self.map_coords_edit = QLineEdit(readOnly=True)
        self.geo_coords_edit = QLineEdit(readOnly=True)
        
        self.value_table = QTableWidget()
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

    def _init_layout(self):
        """Builds the dialog's layout."""
        main_layout = QVBoxLayout(self)

        # --- Info Panel ---
        info_panel = QWidget()
        form_layout = QFormLayout(info_panel)
        form_layout.addRow("Pixel (X, Y):", self.coords_edit)
        # form_layout.addRow("Map Coords (Native):", self.map_coords_edit)
        form_layout.addRow("Geographic (Lon, Lat):", self.geo_coords_edit)

        # --- Table for Pixel Values ---
        self.value_table.setColumnCount(3)
        self.value_table.setHorizontalHeaderLabels(["Wavelength", "Band Name", "Value"])
        self.value_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.value_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # --- Buttons ---
        button_layout = QHBoxLayout()
        export_data_btn = QPushButton("Export Data (CSV)")
        export_plot_btn = QPushButton("Export Plot (PNG)")
        ok_btn = QPushButton("OK")
        
        export_data_btn.clicked.connect(self.export_data)
        export_plot_btn.clicked.connect(self.export_plot)
        ok_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(export_data_btn)
        button_layout.addWidget(export_plot_btn)
        button_layout.addStretch()
        button_layout.addWidget(ok_btn)

        # --- Assemble Layout ---
        main_layout.addWidget(self.view_mode_combo)
        main_layout.addWidget(info_panel)
        main_layout.addWidget(self.value_table)
        main_layout.addWidget(self.canvas)
        main_layout.addWidget(self.toolbar)
        main_layout.addLayout(button_layout)

    def _parse_wavelengths(self, metadata: dict) -> list[float]:
        """Safely parses wavelengths from metadata."""
        try:
            wavelength_str = metadata.get("wavelength")
            if wavelength_str:
                return [float(w) for w in str(wavelength_str).strip('{}').split(',')]
        except (ValueError, AttributeError):
            pass # Fails silently, returns empty list
        return []

    def _is_cursor_in_bounds(self) -> bool:
        """Helper to check if the current (x, y) is within the image dimensions."""
        return (0 <= self.y < self.image_data.shape[0] and 
                0 <= self.x < self.image_data.shape[1])

    def update_view_mode(self):
        """Toggles visibility between the plot and the table."""
        is_plot_mode = (self.view_mode_combo.currentText() == "Spectral Plot")
        self.canvas.setVisible(is_plot_mode)
        self.toolbar.setVisible(is_plot_mode)
        self.value_table.setVisible(not is_plot_mode)

        if is_plot_mode:
            self.plot_spectral_profile()
        else:
            self.populate_value_table()
    def update_pixel_info(self, x: int, y: int):
        """The main entry point to update all information in the window."""
        self.x = x
        self.y = y
        self.coords_edit.setText(f"({x}, {y})")

        if self.geotransform and self.projection:
            print(f" \n \n \n Updating pixel info for ({x}, {y}) with geotransform {self.geotransform} \n \n \n \n \n and projection {self.projection} \n\n\n\n\n")
            try:
                # 1. Get map coordinates (e.g., UTM easting, northing) from pixel coordinates
                # This returns (map_x, map_y)
                map_y, map_x = gdal.ApplyGeoTransform(self.geotransform, x + 0.5, y + 0.5)
                self.map_coords_edit.setText(f"{map_x:.3f}, {map_y:.3f}")

                # 2. Set up the spatial reference systems
                source_srs = osr.SpatialReference()
                source_srs.ImportFromWkt(self.projection)

                print(f"Source SRS: {source_srs} \n\n\n\n\n") 
                target_srs = osr.SpatialReference()
                target_srs.ImportFromEPSG(4326) # WGS84 (lat/lon)
                print(f"Target SRS: {target_srs} \n\n\n\n\n")

                # 3. Handle axis mapping for modern GDAL/PROJ versions
                # This ensures the transformation expects (easting, northing) or (lon, lat)
                source_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
                target_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

                # 4. Transform if the source is not already WGS84
                if not source_srs.IsSame(target_srs):
                    transform = osr.CoordinateTransformation(source_srs, target_srs)
                    # print(f"Transform: {transform} \n\n\n\n\n")

                    # CORRECT ORDER: Pass (map_x, map_y)
                    # The result is (longitude, latitude, altitude)
                    lat, lon, _ = transform.TransformPoint(map_y, map_x)
                    # print(f"Transformed map coords ({map_x}, {map_y}) to geographic coords ({lon}, {lat}) \n\n\n\n\n")
                    # Display in conventional Lon, Lat order
                    self.geo_coords_edit.setText(f"{lon:.6f}, {lat:.6f}")
                else: 
                    # The data is already in WGS84, so map coords are lon/lat
                    # Display in conventional Lon, Lat order
                    self.geo_coords_edit.setText(f"{map_x:.6f}, {map_y:.6f}")

            except Exception as e:
                # Better error handling: Log the error for debugging
                print(f"Coordinate transformation error: {e}")
                self.map_coords_edit.setText("Transform Error")
                self.geo_coords_edit.setText("Transform Error")
        else:
            # No georeferencing info available
            self.map_coords_edit.setText("N/A")
            self.geo_coords_edit.setText("N/A")
        
        # Refresh the active view (plot or table)
        self.update_view_mode()


    def populate_value_table(self):
        """Fills the QTableWidget with pixel values."""
        self.value_table.setRowCount(0)
        if not self._is_cursor_in_bounds():
            return

        pixel_values = self.image_data[self.y, self.x, :]
        self.value_table.setRowCount(len(pixel_values))

        for i, (value, band_name) in enumerate(zip(pixel_values, self.band_names)):
            wl_text = f"{self.wavelengths[i]:.2f}" if i < len(self.wavelengths) else "N/A"
            self.value_table.setItem(i, 0, QTableWidgetItem(wl_text))
            self.value_table.setItem(i, 1, QTableWidgetItem(band_name))
            self.value_table.setItem(i, 2, QTableWidgetItem(f"{value:.4f}"))
    # Add this new method to the PixelInfoWindow class
    def update_data(self, file_name, image_data, band_names, metadata, geotransform, projection, x, y):
        """
        Completely refreshes the window with data from a new source layer.
        """
        # Re-assign all of the window's internal data
        self.file_name = file_name
        self.image_data = image_data
        self.band_names = band_names
        self.metadata = metadata
        self.geotransform = geotransform
        self.projection = projection
        self.wavelengths = self._parse_wavelengths(metadata)
        self.wavelength_units = metadata.get("wavelength_units", "nm")
        
        # Now, call the existing update function to refresh the display
        self.update_pixel_info(x, y)
    def plot_spectral_profile(self):
        """Plots the spectral profile for the current pixel."""
        self.ax.clear()
        if not self._is_cursor_in_bounds():
            self.ax.set_title("Cursor is outside image bounds", color="red")
            self.canvas.draw()
            return

        pixel_values = self.image_data[self.y, self.x, :].astype(float)
        
        has_wavelengths = self.wavelengths and len(self.wavelengths) == len(pixel_values)
        x_data = self.wavelengths if has_wavelengths else range(1, len(pixel_values) + 1)
        xlabel = f"Wavelength ({self.wavelength_units})" if has_wavelengths else "Band Number"

        self.ax.plot(x_data, pixel_values, marker='.', linestyle='-', markersize=4)
        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel("Pixel Value")
        self.ax.set_title(f"{self.file_name}\nSpectral Profile at ({self.x}, {self.y})")
        self.ax.grid(True, linestyle="--", alpha=0.6)
        
        self.figure.tight_layout()
        self.canvas.draw()
        
        if MPLCURSORS_AVAILABLE:
            self._setup_plot_cursor()

    def _setup_plot_cursor(self):
        """Initializes mplcursors for interactive annotations on the plot."""
        # if hasattr(self, "cursor"): self.cursor.remove() # Remove old cursor
        if self.cursor is not None: # Instead of hasattr(self, "cursor")
            try:
                self.cursor.remove()
            except Exception:
                pass



        self.cursor = mplcursors.cursor(self.ax, hover=True)
        @self.cursor.connect("add")
        def _on_add(sel):
            x_val, y_val = sel.target
            x_str = f"{x_val:.2f}" if isinstance(x_val, float) else f"{int(x_val)}"
            sel.annotation.set_text(
                f"{self.ax.get_xlabel()}: {x_str}\n{self.ax.get_ylabel()}: {y_val:.4f}"
            )
            sel.annotation.get_bbox_patch().set(facecolor='white', alpha=0.8)

    def export_data(self):
        """Exports the current pixel's spectral data to a CSV file."""
        if not self._is_cursor_in_bounds():
            QMessageBox.warning(self, "Export Error", "Cannot export: Pixel is outside image bounds.")
            return

        default_name = f"{os.path.splitext(self.file_name)[0]}_pixel_{self.x}_{self.y}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Save Pixel Data", default_name, "CSV Files (*.csv)")
        
        if path:
            try:
                pixel_values = self.image_data[self.y, self.x, :]
                data = {
                    "Band_Name": self.band_names,
                    "Value": pixel_values,
                    "Wavelength": self.wavelengths if self.wavelengths else ["N/A"] * len(pixel_values)
                }
                pd.DataFrame(data).to_csv(path, index=False)
                QMessageBox.information(self, "Success", f"Data exported to {path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))

    def export_plot(self):
        """Exports the current spectral plot as a PNG image."""
        default_name = f"{os.path.splitext(self.file_name)[0]}_plot_{self.x}_{self.y}.png"
        path, _ = QFileDialog.getSaveFileName(self, "Save Plot", default_name, "PNG Files (*.png)")
        if path:
            try:
                self.figure.savefig(path, dpi=300, bbox_inches='tight')
                QMessageBox.information(self, "Success", f"Plot exported to {path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))
