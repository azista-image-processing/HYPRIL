# src/ui/main_window.py
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QPushButton, QToolButton, QMenu,
                               QFileDialog, QDialog, QVBoxLayout, QLabel, QToolBar,
                               QComboBox, QListWidget, QRadioButton)
#importing QAction 
# from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt, QSize
# from netCDF4 import Dataset
from osgeo import gdal
import numpy as np
import os
import logging

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
# from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar


from src.core.Image_loader import HyperspectralImageLoader  
from src.ui.Image_Viewer_Window import ImageViewerWindow
from src.core.Spectral_Library_Plotter import SpectralLibraryPlotter

class HyperspectralViewer(QMainWindow):
    """
    The main window of the application.
    It handles loading the hyperspectral image and opening the viewer window.
    """
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setWindowTitle("HYPRIL(Hyperspectral Processing and Interpretation Lab)")
        # self.setGeometry(600, 600, 800, 600)
        #Setting Fix width
        self.setFixedWidth(400)
        self.setFixedHeight(25)
        self.image_data = None
        self.band_names = []
        self.metadata = {}
        self.geotransform = None
        self.projection = None
        self.init_ui()
        self.adjustSize()

    def init_ui(self):
        # Create a toolbar
        toolbar = QToolBar("Main Toolbar", self)
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(32, 32))
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        # ---- File Menu ----
        file_menu = QMenu("File", self)
        file_menu.addAction("Open Image", self.load_image)
        file_menu.addAction("Open Spectral Library", self.open_spectral_library)
        file_menu.addAction("Save", self.save_file)
        file_menu.addAction("Exit", self.close)

        file_btn = QToolButton()
        file_btn.setText("File")
        file_btn.setPopupMode(QToolButton.InstantPopup)  # Dropdown on click
        file_btn.setMenu(file_menu)
        toolbar.addWidget(file_btn)

        # ---- Display Menu ----
        display_menu = QMenu("Display", self)
        display_menu.addAction("RGB Composite", self.show_rgb)
        display_menu.addAction("Histogram", self.show_histogram)

        display_btn = QToolButton()
        display_btn.setText("Display")
        display_btn.setPopupMode(QToolButton.InstantPopup)
        display_btn.setMenu(display_menu)
        toolbar.addWidget(display_btn)


        # ---- Analysis Menu ----
        analysis_menu = QMenu("Analysis", self)
        analysis_menu.addAction("Spectral Profile", self.spectral_profile)
        analysis_menu.addAction("Classification", self.classification)

        analysis_btn = QToolButton()
        analysis_btn.setText("Analysis")
        analysis_btn.setPopupMode(QToolButton.InstantPopup)
        analysis_btn.setMenu(analysis_menu)
        toolbar.addWidget(analysis_btn)

        # ---- Analysis Menu ----
        option_1 = QMenu("Option 1", self)
        option_1.addAction("Spectral Profile", self.spectral_profile)
        option_1.addAction("Classification", self.classification)

        option_1_button = QToolButton()
        option_1_button.setText("Option 1")
        option_1_button.setPopupMode(QToolButton.InstantPopup)
        option_1_button.setMenu(option_1)
        toolbar.addWidget(option_1_button)

        file_btn.setStyleSheet("QToolButton::menu-indicator { image: none; }")
        display_btn.setStyleSheet("QToolButton::menu-indicator { image: none; }")
        analysis_btn.setStyleSheet("QToolButton::menu-indicator { image: none; }")
        option_1_button.setStyleSheet("QToolButton::menu-indicator { image: none; }")

        self.adjustSize()


    def save_file(self):
        print("Save clicked")

    def show_rgb(self):
        print("Show RGB Composite")

    def show_histogram(self):
        print("Show Histogram")

    def spectral_profile(self):
        print("Spectral Profile Analysis")

    def classification(self):
        print("Classification Analysis")
    

    def open_spectral_library(self):
        """Open a spectral library using the SpectralLibraryPlotter."""
        plotter = SpectralLibraryPlotter()
        plotter.plot_spectral_library(parent=self)



    def load_image(self):
        """Load a hyperspectral image using the new loader."""
        
        # This one line handles the file dialog and the entire loading process
        loaders = HyperspectralImageLoader.open_file_dialog(parent=self)
        if loaders is None:
            self.statusBar().showMessage("Image loading cancelled.", 5000)
            return

        if len(loaders) > 1:
            for loader in loaders:
                if loader and loader.is_loaded:
                    # Assign the loaded data from the loader object's attributes
                    self.image_data = loader.image_data
                    self.band_names = loader.band_names
                    self.metadata = loader.metadata # You can still access the raw dict
                    self.geotransform = loader.geotransform
                    self.projection = loader.projection
                    self.wavelengths = loader.wavelengths # Now directly available!
                    self.wavelength_units = loader.wavelength_units
                    self.file_name = os.path.splitext(os.path.basename(loader.file_path))[0]
                    
                    # Now proceed with your application logic
                    self.show_image_viewer_window()
                    self.statusBar().showMessage(f"Loaded image successfully from {loader.file_path}", 5000)
            else:
                self.statusBar().showMessage("Image loading cancelled or failed.", 5000)




    def show_image_viewer_window(self):
        if self.image_data is None:
            self.show_error("No image loaded!")
            return
        # self.show_image_viewer_window()
        self.image_viewer_window = ImageViewerWindow(
            self.image_data, self.band_names, self.metadata,
            self.geotransform, self.projection, self.file_name, self)
        self.image_viewer_window.show()



    def show_error(self, message):
        error_dialog = QDialog(self)
        error_dialog.setWindowTitle("Error")
        layout = QVBoxLayout()
        layout.addWidget(QLabel(message))
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(error_dialog.accept)
        layout.addWidget(ok_button)
        error_dialog.setLayout(layout)
        error_dialog.exec()

