#src/ui/Image_Viewer_Window.py
import os
import numpy as np
import matplotlib.pyplot as plt

from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import QAction, QKeySequence, QIcon, QPixmap
from PySide6.QtWidgets import (QTableWidgetItem,QHeaderView, QLineEdit, QTabWidget, QDialog, QVBoxLayout, QHBoxLayout, QWidget, QToolButton, QMenuBar, QMenu,  QSlider, QSpinBox,
    QListWidget, QListWidgetItem, QTableWidget, QRadioButton, QComboBox, QLabel, QGroupBox, QStatusBar,
    QErrorMessage, QFileDialog, QPushButton, QAbstractItemView, QMainWindow , QFrame, QMessageBox,QSizePolicy
)

from datetime import datetime
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar


from src.core.Spectral_Library_Plotter import SpectralLibraryPlotter
from src.ui.Pixel_Info_Window import PixelInfoWindow
from src.core.MNFProcessor import MNFProcessor
from src.core.Image_loader import HyperspectralImageLoader
from src.ui.ppi_workflow_window import PPI_Workflow_Window
from src.core.Export_Selected import TiffExportDialog
from src.ui.raster_calculator import RasterCalculatorWindow
from src.core.aoi_selector import AOISelector

# --- Constants ---
MODE_SINGLE = "Single Band"
MODE_RGB = "RGB Composite"
ZOOM_FACTOR = 1.2

import logging

logging.basicConfig(level=logging.INFO)
import importlib.util
import sys
import pathlib
import glob


class LayerListWidget(QListWidget):
    """QListWidget with InternalMove enabled and a signal when the order changes."""
    orderChanged = Signal()
    layerrightclicked = Signal(int)


    def __init__(self, parent=None):
        super().__init__(parent)
        logging.info("Initialized LayerListWidget with drag-and-drop support.")
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setDropIndicatorShown(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)  # <-- Enable custom menu
        self.customContextMenuRequested.connect(self._on_context_menu)

    def dropEvent(self, event):
        super().dropEvent(event)
        # Emit when rows have been moved via DnD
        #Printing log message for debugging WITH FILENAME AND LINE NUMBER
        logging.info("Layer order changed via drag-and-drop. dropevent triggered.")
        logging.info("Layer item changed signal received.")
        self.orderChanged.emit()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            # Let parent window handle removal to keep lists in sync
            self.parent().remove_selected_layer()
        else:
            super().keyPressEvent(event)
        logging.info("Key press event in LayerListWidget: %s", event.text())

    def _on_context_menu(self, pos):
        row = self.indexAt(pos).row()
        if row < 0:
            return
        self.layerrightclicked.emit(row)  # notify parent which layer was clicked


class AnimationViewerWindow(QMainWindow):
    """
    A reusable window for animating through the bands of any data cube.
    """
    def __init__(self, image_data, band_names, title="Band Animation", parent=None):
        super().__init__(parent)
        self.image_data = image_data
        self.band_names = band_names
        self.num_bands = image_data.shape[2]
        self.current_band = 0
        self.setWindowTitle(title)
        self.setGeometry(200, 200, 800, 700)

        # Main Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Matplotlib Canvas
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.addToolBar(self.toolbar)

        # Controls Layout
        controls_layout = QHBoxLayout()
        self.prev_button = QPushButton("<< Previous")
        self.prev_button.clicked.connect(self.show_previous)
        controls_layout.addWidget(self.prev_button)

        self.next_button = QPushButton("Next >>")
        self.next_button.clicked.connect(self.show_next)
        controls_layout.addWidget(self.next_button)

        controls_layout.addStretch()
        controls_layout.addWidget(QLabel("Jump to:"))
        self.jump_spinbox = QSpinBox()
        self.jump_spinbox.setRange(1, self.num_bands)
        self.jump_spinbox.valueChanged.connect(self.jump_to_band)
        controls_layout.addWidget(self.jump_spinbox)
        self.layout.addLayout(controls_layout)
        
        # Animation Controls
        animation_layout = QHBoxLayout()
        animation_layout.addStretch()
        self.animate_button = QPushButton("Animate")
        self.animate_button.setCheckable(True)
        self.animate_button.clicked.connect(self.toggle_animation)
        animation_layout.addWidget(self.animate_button)

        animation_layout.addWidget(QLabel("Speed (ms):"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(10, 2000)
        self.speed_slider.setValue(100)
        self.speed_slider.valueChanged.connect(self.set_animation_speed)
        animation_layout.addWidget(self.speed_slider)
        
        self.speed_value_label = QLabel(f"{self.speed_slider.value()} ms")
        animation_layout.addWidget(self.speed_value_label)
        animation_layout.addStretch()
        self.layout.addLayout(animation_layout)
        
        # Timer
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.animate_frame)
        
        self.show_band()
    def show_band(self):
        # Save current zoom/pan limits (only if something is already plotted)
        xlim, ylim = None, None
        if self.ax.images:  
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()

        self.ax.clear()

        # Normalize the band for better viewing
        band_data = self.image_data[:, :, self.current_band]
        p2, p98 = np.percentile(band_data, (2, 98))
        norm_data = np.clip((band_data - p2) / (p98 - p2), 0, 1)

        # Show band
        self.ax.imshow(norm_data, cmap='gray')

        # Title
        band_label = self.band_names[self.current_band] if self.band_names else f"Band {self.current_band+1}"
        self.ax.set_title(band_label)
        self.ax.axis('off')

        # Restore zoom/pan if available
        if xlim and ylim:
            self.ax.set_xlim(xlim)
            self.ax.set_ylim(ylim)

        self.figure.tight_layout()
        self.canvas.draw()

        # Update spinbox
        self.jump_spinbox.blockSignals(True)
        self.jump_spinbox.setValue(self.current_band + 1)
        self.jump_spinbox.blockSignals(False)

    def show_previous(self):
        if self.current_band > 0:
            self.current_band -= 1
            self.show_band()

    def show_next(self):
        if self.current_band < self.num_bands - 1:
            self.current_band += 1
            self.show_band()

    def jump_to_band(self, value):
        self.current_band = value - 1
        self.show_band()

    def toggle_animation(self, checked):
        if checked:
            self.animation_timer.start(self.speed_slider.value())
            self.animate_button.setText("Stop Animation")
        else:
            self.animation_timer.stop()
            self.animate_button.setText("Animate")

    def animate_frame(self):
        self.current_band = (self.current_band + 1) % self.num_bands
        self.show_band()

    def set_animation_speed(self, speed):
        self.speed_value_label.setText(f"{speed} ms")
        if self.animation_timer.isActive():
            self.animation_timer.setInterval(speed)

    def closeEvent(self, event):
        self.animation_timer.stop()
        plt.close(self.figure)
        super().closeEvent(event)



from PySide6.QtGui import QIcon


class ImageViewerWindow(QMainWindow):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        # Set window icon (company logo) before the window title so it appears in the titlebar/taskbar
        self.setWindowTitle("HYPRIL - Hyperspectral Processing, Research and Innovation Lab") # Changed title slightly
        try:
            icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "icons", "April _ Azista - Copy.png"))
            icon = QIcon(icon_path)
            if not icon.isNull():
                self.setWindowIcon(icon)
                logging.info(f"Window icon set from: {icon_path}")
            else:
                logging.warning(f"Window icon not found at: {icon_path}")
        except Exception as e:
            logging.warning(f"Failed to set window icon: {e}")

        

        # --- Initialize with an empty state ---
        self.layers = []  # Start with an empty list of layers
        self.active_layer_index = -1 
        # Plugin infrastructure
        self.loaded_plugins = {}  # name -> module
        self.plugin_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "plugins"))

        # --- Keep track of the last opened file's path for convenience ---
        self.last_dir = os.path.expanduser("~") 

        # --- Interaction State ---
        self._aoi_active = False
        self._is_panning = False
        self._pan_start = (0, 0)
        self._cur_xlim = None
        self._cur_ylim = None
        self.current_mode = MODE_SINGLE
        self.pixel_info_window = None
        self.animation_window = None
        self.raster_analysis_window = None
        self.child_viewer_windows = []
        self.active_processor = None

        # Add these new attributes for viewport management
        self.viewport_cache = {}  # Cache rendered tiles
        self.current_viewport = None
        self.zoom_level = 0
        self.base_resolution = 2048  # Base resolution for initial display
        

        # --- UI ---
        # We need a central widget for a QMainWindow
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self._init_ui() # This will now build the UI on the central_widget
        self._connect_signals()
        self._center_window()
        self._auto_load_plugins()  # Load all discovered plugins at startup

        # --- Initial display ---
        self._update_controls_for_mode()
        self._update_display() # This will initially show an empty canvas
    # ---------------- UI SETUP ----------------
    def _init_ui(self) -> None:
        try:
            logging.basicConfig(level=logging.INFO)
            logger = logging.getLogger(__name__)
            logger.info("Initializing UI components...")

            self.open_metadata_windows = {}

            # main_layout = QVBoxLayout(self)
            main_layout = QVBoxLayout(self.central_widget)
            main_layout.setContentsMargins(5, 5, 5, 5)
            main_layout.setSpacing(5)

            # --- Create header with logo ---
            header_layout = QHBoxLayout()
            
            # Add title label on the left
            # title_label = QLabel("HYPRIL - Hyperspectral Processing, Research and Innovation Lab")
            # title_font = title_label.font()
            # title_font.setPointSize(8)
            # title_font.setBold(True)
            # title_label.setFont(title_font)
            # header_layout.addWidget(title_label)
            
            # Add stretch to push logo to the right
            header_layout.addStretch()
            
            # Add logo on the right
            logo_path = "src/assets/icons/April _ Azista.png"
            logo_label = QLabel()
            try:
                pixmap = QPixmap(logo_path)
                if not pixmap.isNull():
                    # Scale the logo to a reasonable size (height: 15px)
                    scaled_pixmap = pixmap.scaledToHeight(18, Qt.SmoothTransformation)
                    logo_label.setPixmap(scaled_pixmap)
                    logo_label.setContentsMargins(0,0,20,0) # left, top, right, bottom
                    logging.info(f"Logo loaded successfully from: {logo_path}")
                else:
                    logging.warning(f"Logo image not found or invalid at: {logo_path}")
                    logo_label.setText("Logo")
            except Exception as e:
                logging.warning(f"Could not load logo: {str(e)}")
                logo_label.setText("Logo")
            
            header_layout.addWidget(logo_label)
            
            # Add header to main layout
            header_widget = QWidget()
            header_widget.setLayout(header_layout)
            main_layout.addWidget(header_widget)

            self.status_bar = QStatusBar(self)
            self.status_bar.showMessage("Ready" , 5000)
            main_layout.addWidget(self.status_bar)
            
            self._create_menu_bar(main_layout)

            # Content layout (Left controls + Right canvas)
            content_layout = QHBoxLayout()
            content_layout.addWidget(self._create_control_panel(), 1)
            content_layout.addWidget(self._create_image_panel(), 4)
            main_layout.addLayout(content_layout)

        except Exception as e:
            logging.error(f"UI initialization error: {str(e)}")
            QErrorMessage(self).showMessage(f"UI initialization error: {str(e)}")

    def _center_window(self) -> None:
        # Get available screen geometry (excluding taskbar/dock)
        screen_geom = self.screen().availableGeometry()
        
        # Resize window to fill available screen area
        self.setGeometry(screen_geom)
        
        # Log action
        logging.info("Window resized to cover full available screen.")

    def _create_menu_bar(self, main_layout: QVBoxLayout) -> None:
        """Create and configure the menu bar."""
        try:
            self.menu_bar = QMenuBar(self)
            self.menu_bar.setAccessibleName("Main Menu Bar")

            #adding refresh option to menu bar
            refresh_action = QAction(QIcon("src/assests/icons/open.png"), "Refresh Display", self)
            refresh_action.setStatusTip("Refresh the image display")
            refresh_action.triggered.connect(self.refresh_display)
            self.menu_bar.addAction(refresh_action)

            # File menu
            file_menu = QMenu("File", self.menu_bar)
            file_menu.setAccessibleName("File Menu")

            act_load = QAction(QIcon("icons/open.png"), "Load Image…", self)
            act_load.setShortcut(QKeySequence("Ctrl+O"))
            act_load.setStatusTip("Load an image file for processing")
            act_load.setToolTip("Open an image file (Ctrl+O)")
            act_load.triggered.connect(self.load_image)
            file_menu.addAction(act_load)


            # NEW: Open selected layer in a new window
            act_open_new_win = QAction(QIcon("icons/new_window.png"), "Open Image in New Window", self)
            act_open_new_win.setStatusTip("Open the selected layer in a separate viewer window")
            act_open_new_win.triggered.connect(self.open_image_in_new_window)
            file_menu.addAction(act_open_new_win)


            act_remove = QAction(QIcon("icons/remove.png"), "Remove Selected Layer", self)
            act_remove.setShortcut(QKeySequence.Delete)
            act_remove.setStatusTip("Remove the currently selected layer")
            act_remove.setToolTip("Remove selected layer (Delete)")
            act_remove.triggered.connect(self.remove_selected_layer)
            file_menu.addAction(act_remove)

            # file_menu.addSeparator()

            act_exit = QAction(QIcon("icons/exit.png"), "Exit", self)
            act_exit.setShortcut(QKeySequence("Ctrl+Q"))
            act_exit.setStatusTip("Exit the application")
            act_exit.setToolTip("Exit application (Ctrl+Q)")
            act_exit.triggered.connect(self.close)
            file_menu.addAction(act_exit)

        

            # Tool menu
            tools_menu = QMenu("Tools", self.menu_bar)
            tools_menu.setAccessibleName("Tools Menu")

            act_draw_aoi = QAction(QIcon("icons/select_rect.png"), "Draw AOI (Clip)...", self)
            act_draw_aoi.setStatusTip("Draw an AOI on the active layer and clip to it")
            act_draw_aoi.triggered.connect(self._start_aoi_selection)
            file_menu.addAction(act_draw_aoi)




            #Raster Analysis submenu
            raster_analysis_menu = QMenu("Raster Analysis", self)
            raster_analysis_menu.setAccessibleName("Raster Analysis Menu")

            #add actions for raster Calculator
            act_raster_analysis = QAction("Raster Calculator", self)
            act_raster_analysis.setStatusTip("Perform raster analysis on the loaded image")
            act_raster_analysis.triggered.connect(self._raster_analysis)
            raster_analysis_menu.addAction(act_raster_analysis)


            #Raster Analysis submenu
            End_Member_Menu = QMenu("End Member Extractor", self)
            End_Member_Menu.setAccessibleName("End Member Extractor")

            #add actions for raster Calculator
            act_PPI = QAction("Pure Pixel Index", self)
            act_PPI.setStatusTip("Calculate PPI on the loaded image")
            act_PPI.triggered.connect(self._PPI_Calculator)
            End_Member_Menu.addAction(act_PPI)


            #Spectral plotting
            spectral_plotting_menu = QMenu("Spectral Plotting", self)
            spectral_plotting_menu.setAccessibleName("Spectral Plotting Menu")

            # Add actions for spectral plotting
            act_plot_spectral_profile = QAction("Plot Spectral Profile", self)
            act_plot_spectral_profile.setStatusTip("Plot the spectral profile of the selected pixel")
            act_plot_spectral_profile.triggered.connect(self.plot_spectral_profile)
            spectral_plotting_menu.addAction(act_plot_spectral_profile)

             # Pre-Processing submenu
            pre_processing_menu = QMenu("Pre-Processing", self)
            pre_processing_menu.setAccessibleName("Pre-Processing Menu")

            act_Bad_band_removal = QAction(QIcon("icons/blur.png"), "Bad Band Removal", self)
            act_Bad_band_removal.setStatusTip("Removing Bands Based on the Pixel Values")
            act_Bad_band_removal.triggered.connect(self.Bad_Band_Removal)
            pre_processing_menu.addAction(act_Bad_band_removal)

            act_PCA = QAction(QIcon("icons/blur.png"), "PCA", self)
            act_PCA.setStatusTip("Apply PCA")
            act_PCA.triggered.connect(self.PCA)
            pre_processing_menu.addAction(act_PCA)


            act_MNF = QAction(QIcon("icons/blur.png"), "MNF", self)
            act_MNF.setStatusTip("Apply MNF")
            act_MNF.triggered.connect(self.MNF)
            pre_processing_menu.addAction(act_MNF)


            act_ICA = QAction(QIcon("icons/blur.png"), "ICA", self)
            act_ICA.setStatusTip("Apply ICA")
            act_ICA.triggered.connect(self.ICA)
            pre_processing_menu.addAction(act_ICA)


            tools_menu.addMenu(pre_processing_menu) 
            tools_menu.addMenu(spectral_plotting_menu)
            tools_menu.addMenu(raster_analysis_menu)
            tools_menu.addMenu(End_Member_Menu)
            # tools_menu.addMenu()

            main_layout.addWidget(self.menu_bar)
            self.menu_bar.addMenu(file_menu)
            self.menu_bar.addMenu(tools_menu)


            # --- Plugins menu (discover & load external plugins) ---
            try:
                plugins_menu = QMenu("Plugins", self.menu_bar)
                plugins_menu.setAccessibleName("Plugins Menu")

                install_action = QAction("Install Plugin from File...", self)
                install_action.setStatusTip("Install a plugin from a Python file")
                install_action.triggered.connect(lambda: self._install_plugin_dialog())
                plugins_menu.addAction(install_action)
                plugins_menu.addSeparator()

                # Discover local plugins folder and add entries
                discovered = self._discover_plugins()
                for p in discovered:
                    name = os.path.splitext(os.path.basename(p))[0]
                    act = QAction(name, self)
                    act.setStatusTip(f"Load plugin: {name}")
                    act.triggered.connect(lambda checked=False, path=p: self._load_plugin_from_path(path))
                    plugins_menu.addAction(act)
                self.menu_bar.addMenu(plugins_menu)

                
                logging.info(f"Plugins menu created. Found {len(discovered)} plugin(s).")
            except Exception as e:
                logging.warning(f"Failed to create Plugins menu: {e}")
            logging.info("Menu bar created successfully.")


        except Exception as e:
            logging.error(f"Error creating menu bar: {str(e)}")
            self.status_bar.showMessage(f"Menu bar creation error: {str(e)}")
            raise

    def refresh_display(self):
        """
        Removes all loaded layers, clears the display, and resets UI controls.
        """
        if not self.layers:
            self.status_bar.showMessage("No layers to clear.", 2000)
            return

        # 1. Clear the main data list that holds all layer information
        self.layers.clear()
        self.active_layer_index = -1

        # 2. Update the visual list widget in the UI
        self._refresh_layer_list() 
        # This will remove all items from the list widget
        self.layer_list.clear()

        # self.layer_list.setCurrentRow(-1)  # No selection
        # 3. Clear the band selection dropdowns
        self.single_band_combo.clear()
        self.r_combo.clear()
        self.g_combo.clear()
        self.b_combo.clear()
        self.ax.clear()
        # 4. Redraw the canvas, which will now be empty
        self._update_display() 

        self.status_bar.showMessage("Workspace Cleared. Ready to load new image.", 3000)

    # ---------------- PLUGIN INFRASTRUCTURE ----------------
    def _discover_plugins(self) -> list:
        """Return list of .py plugin file paths in the configured plugins folder."""
        try:
            if not os.path.isdir(self.plugin_dir):
                logging.info(f"Plugin directory does not exist: {self.plugin_dir}")
                return []
            pattern = os.path.join(self.plugin_dir, "*.py")
            files = sorted(glob.glob(pattern))
            logging.info(f"Discovered plugin files: {files}")
            return files
        except Exception as e:
            logging.error(f"Error discovering plugins: {e}")
            return []

    def _install_plugin_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select plugin file", "", "Python Files (*.py)")
        if not path:
            return
        try:
            self._load_plugin_from_path(path)
        except Exception as e:
            logging.error(f"Failed to install plugin from {path}: {e}")
            QErrorMessage(self).showMessage(f"Failed to install plugin: {e}")

    def _load_plugin_from_path(self, path: str):
        """Dynamically load a plugin module from a filesystem path.

        Expected plugin entry point: a callable `register(window)` function which
        receives the `ImageViewerWindow` instance and can add actions/widgets.
        """
        try:
            name = os.path.splitext(os.path.basename(path))[0]
            unique_name = f"hypril_plugin_{name}_{abs(hash(path))}"
            if unique_name in sys.modules:
                module = sys.modules[unique_name]
                logging.info(f"Plugin module already loaded: {unique_name}")
            else:
                spec = importlib.util.spec_from_file_location(unique_name, path)
                if spec is None or spec.loader is None:
                    raise ImportError(f"Cannot load plugin spec for {path}")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                sys.modules[unique_name] = module
                logging.info(f"Plugin module loaded: {unique_name}")

            # Call register if present
            if hasattr(module, 'register') and callable(module.register):
                try:
                    module.register(self)
                    self.loaded_plugins[name] = module
                    logging.info(f"Plugin '{name}' registered successfully.")
                    QMessageBox.information(self, "Plugin Installed", f"Plugin '{name}' installed and registered.")
                except Exception as e:
                    logging.error(f"Error while registering plugin '{name}': {e}", exc_info=True)
                    QErrorMessage(self).showMessage(f"Plugin '{name}' failed during register(): {e}")
            else:
                logging.warning(f"Plugin '{name}' does not expose a register(window) function.")
                QMessageBox.information(self, "Plugin Loaded", f"Plugin '{name}' loaded but no register(window) found.")
        except Exception as e:
            logging.error(f"Failed to load plugin from {path}: {e}", exc_info=True)
            QErrorMessage(self).showMessage(f"Failed to load plugin: {e}")

    def _auto_load_plugins(self):
        """Automatically discover and load all plugins from the plugins folder at startup.
        
        Unlike _load_plugin_from_path, this does NOT show message boxes; it just logs results.
        """
        discovered = self._discover_plugins()
        if not discovered:
            logging.info("No plugins to auto-load.")
            return

        logging.info(f"Auto-loading {len(discovered)} plugin(s)...")
        for path in discovered:
            try:
                name = os.path.splitext(os.path.basename(path))[0]
                unique_name = f"hypril_plugin_{name}_{abs(hash(path))}"
                
                if unique_name in sys.modules:
                    module = sys.modules[unique_name]
                    logging.info(f"Plugin '{name}' already loaded.")
                else:
                    spec = importlib.util.spec_from_file_location(unique_name, path)
                    if spec is None or spec.loader is None:
                        logging.warning(f"Cannot load plugin spec for {path}")
                        continue
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    sys.modules[unique_name] = module
                    logging.info(f"Plugin module loaded: {unique_name}")

                # Call register if present
                if hasattr(module, 'register') and callable(module.register):
                    try:
                        module.register(self)
                        self.loaded_plugins[name] = module
                        logging.info(f"✓ Plugin '{name}' auto-loaded and registered.")
                    except Exception as e:
                        logging.error(f"Error registering plugin '{name}': {e}", exc_info=True)
                else:
                    logging.warning(f"Plugin '{name}' has no register(window) function; skipping.")

            except Exception as e:
                logging.error(f"Failed to auto-load plugin from {path}: {e}", exc_info=True)

        logging.info(f"Auto-load complete. Loaded {len(self.loaded_plugins)} plugin(s).")

    def plot_spectral_profile(self):
        # Plot spectral library
        plotter = SpectralLibraryPlotter()
        plotter.plot_spectral_library(parent=self)
        logging.info("Spectral profile plotter launched.")

    def _create_control_panel(self) -> QWidget:
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        control_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- Display Mode ---
        mode_group = QGroupBox("Display Mode")
        mode_layout = QVBoxLayout()
        self.single_band_radio = QRadioButton(MODE_SINGLE)
        self.single_band_radio.setChecked(True)
        self.rgb_radio = QRadioButton(MODE_RGB)
        mode_layout.addWidget(self.single_band_radio)
        mode_layout.addWidget(self.rgb_radio)
        mode_group.setLayout(mode_layout)
        control_layout.addWidget(mode_group)

        # --- Single Band Controls ---
        self.single_band_group = QGroupBox("Single Band Selection")
        single_band_layout = QVBoxLayout()
        self.single_band_combo = QComboBox()
        single_band_layout.addWidget(self.single_band_combo)
        self.single_band_group.setLayout(single_band_layout)
        control_layout.addWidget(self.single_band_group)

        # --- RGB Controls ---
        self.rgb_group = QGroupBox("RGB Composite Selection")
        rgb_layout = QVBoxLayout()
        self.r_combo = QComboBox()
        self.g_combo = QComboBox()
        self.b_combo = QComboBox()
        rgb_layout.addWidget(QLabel("Red Band:"))
        rgb_layout.addWidget(self.r_combo)
        rgb_layout.addWidget(QLabel("Green Band:"))
        rgb_layout.addWidget(self.g_combo)
        rgb_layout.addWidget(QLabel("Blue Band:"))
        rgb_layout.addWidget(self.b_combo)
        self.rgb_group.setLayout(rgb_layout)
        control_layout.addWidget(self.rgb_group)

        # --- Layer Management ---
        self.layer_group = QGroupBox("Layer Management")
        layer_layout = QVBoxLayout()

        # List with checkboxes + DnD
        self.layer_list = LayerListWidget(control_widget)
        layer_layout.addWidget(self.layer_list)

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_load = QPushButton("Load Image…")
        self.btn_load.clicked.connect(self.load_image)
        self.btn_remove = QPushButton("Remove Selected")
        self.btn_remove.clicked.connect(self.remove_selected_layer)
        btn_row.addWidget(self.btn_load)
        btn_row.addWidget(self.btn_remove)
        layer_layout.addLayout(btn_row)

        self.btn_animate = QPushButton("Animate Bands of Selected Layer")
        self.btn_animate.clicked.connect(self.animate_bands)
        control_layout.addWidget(self.btn_animate)

        control_layout.addStretch()

        self.layer_group.setLayout(layer_layout)
        control_layout.addWidget(self.layer_group)

        # Populate initial controls
        self._refresh_layer_list()
        logging.info("Control panel created successfully.")

        return control_widget

    def _create_image_panel(self) -> QWidget:
        """Creates a robust PySide6 panel for displaying hyperspectral images."""

        # 1. Frame setup with styling
        image_frame = QFrame()
        image_frame.setObjectName("HyperspectralImagePanel")
        image_frame.setStyleSheet("""
            QFrame#HyperspectralImagePanel {
                border: 2px solid #555;
                border-radius: 8px;
                background-color: #f0f0f0;
            }
        """)
        frame_layout = QVBoxLayout(image_frame)
        frame_layout.setContentsMargins(5, 5, 5, 5)

        # 2. Matplotlib figure and canvas
        self.figure, self.ax = plt.subplots()
        self.figure.subplots_adjust(left=0, right=1, top=1, bottom=0)
        self.ax.axis('off')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas.setStyleSheet("border: 3px solid #444; border-radius: 5px;")

        # 3. Toolbar
        self.toolbar = NavigationToolbar(self.canvas, image_frame)

        # 4. Status bar for feedback/user hints
        self.statusbar = QStatusBar(image_frame)
        self.statusbar.setSizeGripEnabled(False)
        self.statusbar.showMessage("Ready")

        # 5. Layout widgets
        frame_layout.addWidget(self.toolbar)
        frame_layout.addWidget(self.canvas)
        frame_layout.addWidget(self.statusbar)

        self.canvas.mpl_connect("button_press_event", self._on_mouse_press)
        self.canvas.mpl_connect("button_release_event", self._on_mouse_release)
        self.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)

        # 7. Optional: expose figure/canvas/ax/statusbar for outside use
        image_frame.figure = self.figure
        image_frame.ax = self.ax
        image_frame.canvas = self.canvas
        image_frame.statusbar = self.statusbar

        # 8. Logging and return
        logging.info("Image panel created successfully.")
        return image_frame

    def _start_aoi_selection(self):
        if not (0 <= self.active_layer_index < len(self.layers)):
            QErrorMessage(self).showMessage("No layer selected.")
            return

        # Disable existing pan/zoom while AOI is active
        self._aoi_active = True
        self.status_bar.showMessage("AOI mode: drag a rectangle on the image to clip; release to finish.", 0)

        # Create and start selector
        self._aoi_selector = AOISelector(self.ax, self.canvas, parent=self)
        self._aoi_selector.finished.connect(self._on_aoi_finished)
        self._aoi_selector.start()


    def _on_aoi_finished(self, bounds):
        # Re-enable pan/zoom
        self._aoi_active = False
        self.status_bar.showMessage("AOI selection complete.", 3000)

        try:
            x1, y1, x2, y2 = bounds
            if x2 <= x1 or y2 <= y1:
                QErrorMessage(self).showMessage("Invalid AOI: zero or negative area.")
                return

            # Clamp to image bounds
            active = self.layers[self.active_layer_index]
            data = active["data"]
            h, w = data.shape[:2]
            xi1 = max(0, min(w - 1, x1))
            xi2 = max(0, min(w - 1, x2))
            yi1 = max(0, min(h - 1, y1))
            yi2 = max(0, min(h - 1, y2))

            # Inclusive → exclusive slice
            xs, xe = xi1, xi2 + 1
            ys, ye = yi1, yi2 + 1

            clipped = data[ys:ye, xs:xe, :] if data.ndim == 3 else data[ys:ye, xs:xe]

            # Compute new geotransform from parent if present
            gt = active.get("geotransform")
            proj = active.get("projection")
            new_gt = None
            if gt:
                # General affine adjustment for offset by (xs, ys)
                gt0, gt1, gt2, gt3, gt4, gt5 = gt
                new_gt0 = gt0 + xs * gt1 + ys * gt2
                new_gt3 = gt3 + xs * gt4 + ys * gt5
                new_gt = (new_gt0, gt1, gt2, new_gt3, gt4, gt5)

            # Build new layer with propagated metadata
            layer_name = active.get("name", "Layer")
            band_names = active.get("band_names", [])
            new_band_names = band_names if (clipped.ndim == 3 and clipped.shape[2] == len(band_names)) else \
                            ([band_names[0]] if (clipped.ndim == 2 and band_names) else
                            [f"Band {i+1}" for i in range(clipped.shape[2])] if clipped.ndim == 3 else ["Band 1"])




            new_layer = {
                "name": f"AOI Clip - {layer_name}",
                "data": clipped.astype(data.dtype, copy=False),
                "band_names": new_band_names,
                "metadata": active.get("metadata", {}).copy(),
                "geotransform": new_gt,
                "projection": proj,
                "visible": True
            }
            new_width, new_height = clipped.shape[1], clipped.shape[0]
            new_layer["metadata"]["RasterXSize"] = new_width
            new_layer["metadata"]["RasterYSize"] = new_height

            # Also carry wavelengths if present on layer or on viewer
            wl = active.get("wavelengths", getattr(self, "wavelengths", []))
            wl_units = active.get("wavelength_units", getattr(self, "wavelength_units", "nm"))
            if wl:
                new_layer["wavelengths"] = wl
                new_layer["wavelength_units"] = wl_units

            self.layers.insert(0, new_layer)
            self._refresh_layer_list()
            self.layer_list.setCurrentRow(0)
            self._update_band_combos_for_active_layer()
            self._update_display()
            self.fit_image_to_display()
            QMessageBox.information(self, "AOI Clip", f"Created layer '{new_layer['name']}'")

        except Exception as e:
            QErrorMessage(self).showMessage(f"AOI clip failed: {e}")







    def fit_image_to_display(self):
        """Automatically fit the image to fill the display area"""
        if not self.layers or self.active_layer_index < 0:
            return
        
        active_layer = self.layers[self.active_layer_index]
        data = active_layer['data']
        rows, cols = data.shape[:2]
        
        self.ax.set_xlim(0, cols)
        self.ax.set_ylim(rows, 0)
        self.ax.autoscale(enable=True, axis='both', tight=True)
        self.canvas.draw_idle()

    # ---------------- SIGNALS ----------------

    def _connect_signals(self) -> None:
        # Mode change
        self.single_band_radio.toggled.connect(self._on_mode_change)

        # Band selection
        self.single_band_combo.currentIndexChanged.connect(self._update_display)
        self.r_combo.currentIndexChanged.connect(self._update_display)
        self.g_combo.currentIndexChanged.connect(self._update_display)
        self.b_combo.currentIndexChanged.connect(self._update_display)

        # Canvas interactions
        self.canvas.mpl_connect('button_press_event', self._on_mouse_press_For_plot)
        self.canvas.mpl_connect('button_release_event', self._on_mouse_release_For_plot)
        self.canvas.mpl_connect('scroll_event', self._on_scroll_zoom)

        # Layer list interactions
        self.layer_list.itemChanged.connect(self._on_layer_item_changed)
        self.layer_list.orderChanged.connect(self._sync_layers_from_list)
        self.layer_list.itemSelectionChanged.connect(self._on_active_layer_changed)
        self.layer_list.layerrightclicked.connect(self._show_layer_context_menu)

        logging.info("Signals connected successfully.")

    def _show_layer_context_menu(self, row: int):
        layer = self.layers[row]
        
        menu = QMenu(self)

        # Example actions
        view_metadata_action = QAction("View Metadata", self)
        view_metadata_action.triggered.connect(lambda: self._view_layer_metadata(layer))
        menu.addAction(view_metadata_action)

        export_layer_action = QAction("Export Layer", self)
        export_layer_action.triggered.connect(lambda: self._export_layer(layer))
        menu.addAction(export_layer_action)

        remove_layer_action = QAction("Remove Layer", self)
        remove_layer_action.triggered.connect(lambda: self._remove_layer_by_index(row))
        menu.addAction(remove_layer_action)

        properties_action = QAction("Properties", self)
        properties_action.triggered.connect(lambda: self._show_layer_properties(layer))
        menu.addAction(properties_action)

        menu.exec(self.layer_list.mapToGlobal(self.layer_list.visualItemRect(self.layer_list.item(row)).bottomLeft()))

    def _show_layer_properties(self, layer: dict):
        """
        Displays a properties dialog for a layer, similar to QGIS.
        Includes:
        - General tab: metadata table
        - NoData tab: set image no-data value
        """
        from PySide6.QtWidgets import (
            QDialog, QVBoxLayout, QTabWidget, QWidget, QTableWidget, QTableWidgetItem,
            QAbstractItemView, QHeaderView, QHBoxLayout, QLabel, QDoubleSpinBox, QPushButton, QMessageBox
        )

        layer_name = layer.get("name", "Unknown Layer")
        metadata = layer.get("metadata", {})

        # Create main dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Properties - {layer_name}")
        dialog.setMinimumSize(500, 400)

        main_layout = QVBoxLayout(dialog)
        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        # -------------------------------
        # TAB 1: GENERAL (metadata table)
        # -------------------------------
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)

        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Property", "Value"])
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)

        if metadata:
            table.setRowCount(len(metadata))
            for row, (key, value) in enumerate(metadata.items()):
                table.setItem(row, 0, QTableWidgetItem(str(key)))
                table.setItem(row, 1, QTableWidgetItem(str(value)))
        else:
            table.setRowCount(1)
            table.setItem(0, 0, QTableWidgetItem("No metadata"))
            table.setItem(0, 1, QTableWidgetItem(""))

        general_layout.addWidget(table)
        tabs.addTab(general_tab, "General")

        # -------------------------------
        # TAB 2: NODATA SETTINGS
        # -------------------------------
        nodata_tab = QWidget()
        nodata_layout = QVBoxLayout(nodata_tab)

        nodata_label = QLabel("Set NoData value (pixels with this value will be treated as empty):")
        nodata_spin = QDoubleSpinBox()
        nodata_spin.setRange(-1e9, 1e9)
        nodata_spin.setDecimals(4)
        nodata_spin.setValue(float(metadata.get("NoData", 0)))  # Default 0 if not present

        apply_btn = QPushButton("Apply NoData Value")

        # Function to apply no-data change
        def apply_nodata_value():
            nodata_value = nodata_spin.value()
            metadata["NoData"] = nodata_value
            layer["metadata"] = metadata  # update layer dict

            # Optional: if layer has actual numpy data, replace NaN with 0 or similar
            if "data" in layer:
                import numpy as np
                data = layer["data"]
                if isinstance(data, np.ndarray):
                    data[np.isnan(data)] = nodata_value
                    layer["data"] = data

            QMessageBox.information(dialog, "NoData Updated", f"NoData value set to {nodata_value}")
            self._update_display()  # Refresh display to reflect changes

        apply_btn.clicked.connect(apply_nodata_value)

        nodata_layout.addWidget(nodata_label)
        nodata_layout.addWidget(nodata_spin)
        nodata_layout.addWidget(apply_btn)
        nodata_layout.addStretch()

        tabs.addTab(nodata_tab, "NoData")


        dialog.exec()


    def _view_layer_metadata(self, layer: dict):
        """
        Displays a detailed, QGIS-style properties dialog for a layer, 
        including per-band min/max statistics.
        """
        layer_name = layer.get("name", "Unknown Layer")
        metadata = layer.get("metadata", {}).copy() # Use a copy to avoid modifying original

        # --- If a window for this layer is already open, just bring it to the front ---
        if layer_name in self.open_metadata_windows:
            window = self.open_metadata_windows.get(layer_name)
            if window:
                window.activateWindow()
                return

        if not metadata:
            QMessageBox.information(
                self, f"Metadata - {layer_name}", "No metadata available for this layer."
            )
            return

        # --- Create the Dialog Window ---
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Properties - {layer_name}")
        dialog.setGeometry(300, 300, 800, 600) # Increased default width

        # Store a reference and remove it when closed
        self.open_metadata_windows[layer_name] = dialog
        dialog.finished.connect(lambda: self.open_metadata_windows.pop(layer_name, None))

        # --- Main Widgets ---
        main_layout = QVBoxLayout(dialog)
        search_input = QLineEdit(placeholderText="Filter properties in current tab...")
        tab_widget = QTabWidget()
        
        # --- Helper function to create a standard key-value table ---
        def create_kv_table(data: dict) -> QTableWidget:
            table = QTableWidget()
            table.setColumnCount(2)
            table.setHorizontalHeaderLabels(["Property", "Value"])
            table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            table.verticalHeader().setVisible(False)
            header = table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            table.setRowCount(len(data))
            for row, (key, value) in enumerate(data.items()):
                table.setItem(row, 0, QTableWidgetItem(str(key)))
                table.setItem(row, 1, QTableWidgetItem(str(value)))
            return table

        # --- ✨ MODIFIED: Helper to create the detailed band information tab ---
        def create_band_info_tab(layer_data: dict) -> QWidget:
            tab_content_widget = QWidget()
            layout = QVBoxLayout(tab_content_widget)
            layout.setContentsMargins(5, 5, 5, 5)

            # 2. Extract band-specific lists and calculate stats
            image_data = layer_data["data"]
            num_bands = image_data.shape[2]
            band_names = layer_data.get("band_names", [])
            print("layer_data name:", layer_data.get("name", "Unknown"))
            md = layer_data.get("metadata", {})
            # wavelengths = self._parse_wavelengths(md)
            wavelengths = md.get('Wavelengths', [])
            # print("Wavelengths:", wavelengths)
            if isinstance(wavelengths, str):
                wavelengths = wavelengths.strip("{} \n")
                if wavelengths:
                    wavelengths = [float(w) for w in wavelengths.replace(",", " ").split()]
                else:
                    wavelengths = []
            elif isinstance(wavelengths, set):
                wavelengths = list(wavelengths)   # convert set → list
            units = md.get("wavelength_units", "nm")
            
            # --- NEW: Efficiently calculate min/max for all bands at once ---
            min_values = np.min(image_data, axis=(0, 1))
            max_values = np.max(image_data, axis=(0, 1))
            
            # 3. Create the detailed per-band table
            table = QTableWidget()
            # --- NEW: Added Min/Max columns ---
            table.setColumnCount(5)
            table.setHorizontalHeaderLabels([
                "Band #", "Name", f"Wavelength ({units})", "Min Value", "Max Value"
            ])
            table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            table.verticalHeader().setVisible(False)
            table.setRowCount(num_bands)

            for i in range(num_bands):
                # Band Number
                table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
                # Band Name
                name = band_names[i] if i < len(band_names) else "N/A"
                table.setItem(i, 1, QTableWidgetItem(name))
                # Wavelength
                wl = f"{wavelengths[i]}" if i < len(wavelengths) else "N/A"
                table.setItem(i, 2, QTableWidgetItem(wl))
                # --- NEW: Populate Min/Max Value columns ---
                min_val_str = f"{min_values[i]:.2f}"
                table.setItem(i, 3, QTableWidgetItem(min_val_str))
                max_val_str = f"{max_values[i]:.2f}"
                table.setItem(i, 4, QTableWidgetItem(max_val_str))
            
            table.resizeColumnsToContents()
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            layout.addWidget(table)
            return tab_content_widget

        # --- Categorize Metadata and Create Tabs ---
        general_info, spatial_info = {}, {}
        spatial_keys = ['projection', 'geotransform', 'coordinate', 'crs', 'extent', 'map info']
        
        for key, value in metadata.items():
            if any(s_key in key.lower() for s_key in spatial_keys):
                spatial_info[key] = value
            else:
                general_info[key] = value

        tab_widget.addTab(create_kv_table(metadata), "All Properties")
        tab_widget.addTab(create_band_info_tab(layer), "Band Information")
        if spatial_info:
            tab_widget.addTab(create_kv_table(spatial_info), "Spatial Reference")
        if general_info:
            tab_widget.addTab(create_kv_table(general_info), "General")

        # --- Define Slot Functions ---
        def filter_properties():
            search_text = search_input.text().lower()
            current_tab = tab_widget.currentWidget()
            
            tables_to_filter = current_tab.findChildren(QTableWidget)
            if isinstance(current_tab, QTableWidget):
                tables_to_filter.append(current_tab)

            for table in tables_to_filter:
                for row in range(table.rowCount()):
                    is_match = False
                    for col in range(table.columnCount()):
                        item = table.item(row, col)
                        if item and search_text in item.text().lower():
                            is_match = True
                            break
                    table.setRowHidden(row, not is_match)
                    
        def export_metadata():
            path, _ = QFileDialog.getSaveFileName(dialog, "Export Metadata", f"{layer_name}_metadata.txt", "Text Files (*.txt)")
            if not path:
                return
            try:
                with open(path, 'w') as f:
                    f.write(f"Metadata for layer: {layer_name}\n{'='*40}\n")
                    for key, value in metadata.items():
                        f.write(f"{key}: {value}\n")
                QMessageBox.information(dialog, "Success", f"Metadata exported to {path}")
            except Exception as e:
                QMessageBox.critical(dialog, "Error", f"Could not export file: {e}")

        # --- Assemble and Connect ---
        search_input.textChanged.connect(filter_properties)
        tab_widget.currentChanged.connect(filter_properties)

        button_layout = QHBoxLayout()
        export_button = QPushButton("Export to TXT...")
        export_button.clicked.connect(export_metadata)
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        button_layout.addStretch()
        button_layout.addWidget(export_button)
        button_layout.addWidget(close_button)

        main_layout.addWidget(search_input)
        main_layout.addWidget(tab_widget)
        main_layout.addLayout(button_layout)
        
        dialog.show()
   
    def _export_layer(self, layer):
        """Export layer to GeoTIFF format with professional options"""
        export_dialog = TiffExportDialog(layer, parent=self)
        if export_dialog.exec():
            try:
                export_options = export_dialog.get_export_options()
                self._export_to_geotiff(layer, export_options)
                
                file_path = export_options['file_path']
                self.status_bar.showMessage(f"Layer '{layer['name']}' exported to {file_path}", 5000)
                
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export layer: {str(e)}")

    def _export_to_geotiff(self, layer, options):
        """Export hyperspectral layer to GeoTIFF with full metadata"""
        from osgeo import gdal, osr
        
        # Get export parameters
        file_path = options['file_path']
        compression = options['compression']
        extent = options['extent']
        bands = options['selected_bands']
        data_type = options['data_type']
        
        # Prepare data
        data = layer['data']
        
        # Handle extent selection
        if extent == 'current_view' and hasattr(self, 'ax'):
            data = self._crop_to_current_view(data)
        
        # Handle band selection
        if bands != 'all':
            data = data[:, :, bands]
        
        rows, cols, num_bands = data.shape
        
        # Set up GDAL driver and creation options
        driver = gdal.GetDriverByName('GTiff')
        creation_options = ['TILED=YES', 'BIGTIFF=IF_SAFER']
        
        # Add compression
        if compression == 'LZW':
            creation_options.append('COMPRESS=LZW')
            creation_options.append('PREDICTOR=2')  # Better compression for continuous data
        elif compression == 'DEFLATE':
            creation_options.append('COMPRESS=DEFLATE')
            creation_options.append('PREDICTOR=2')
        elif compression == 'JPEG':
            creation_options.append('COMPRESS=JPEG')
            creation_options.append('JPEG_QUALITY=95')
        
        # Determine GDAL data type
        gdal_dtype_map = {
            'Float32': gdal.GDT_Float32,
            'Float64': gdal.GDT_Float64,
            'UInt16': gdal.GDT_UInt16,
            'Int16': gdal.GDT_Int16,
            'UInt32': gdal.GDT_UInt32,
            'Int32': gdal.GDT_Int32
        }
        gdal_dtype = gdal_dtype_map.get(data_type, gdal.GDT_Float32)
        
        # Create the dataset
        dataset = driver.Create(file_path, cols, rows, num_bands, gdal_dtype, creation_options)
        
        if dataset is None:
            raise Exception("Could not create output file")
        
        # Set geospatial information
        geotransform = layer.get('geotransform')
        projection = layer.get('projection')
        
        if geotransform:
            dataset.SetGeoTransform(geotransform)
            
        if projection:
            dataset.SetProjection(projection)
        
        # Write bands with metadata
        wavelengths = layer.get('wavelengths', [])
        band_names = layer.get('band_names', [])
        
        for i in range(num_bands):
            band = dataset.GetRasterBand(i + 1)
            
            # Convert and write data
            band_data = data[:, :, i].astype(self._get_numpy_dtype(data_type))
            band.WriteArray(band_data)
            
            # Set band description
            if i < len(band_names):
                band.SetDescription(band_names[i])
            
            # Set wavelength metadata
            if i < len(wavelengths):
                band.SetMetadataItem('wavelength', str(wavelengths[i]))
                band.SetMetadataItem('wavelength_units', layer.get('wavelength_units', 'nm'))
            
            # Calculate and set statistics
            band.ComputeStatistics(False)
        
        # Set dataset-level metadata
        metadata = layer.get('metadata', {})
        dataset.SetMetadataItem('HYPERSPECTRAL_BANDS', str(num_bands))
        dataset.SetMetadataItem('SOURCE_FILE', layer.get('name', 'Unknown'))
        dataset.SetMetadataItem('EXPORT_TOOL', 'HYPRIL')
        dataset.SetMetadataItem('EXPORT_DATE', str(datetime.now()))
        
        # Add original metadata
        for key, value in metadata.items():
            if isinstance(value, (str, int, float)):
                dataset.SetMetadataItem(str(key), str(value))
        
        # Flush and close
        dataset.FlushCache()
        dataset = None
        
    def _crop_to_current_view(self, data):
        """Crop data to current viewport"""
        if not hasattr(self, 'ax'):
            return data
            
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        
        x1 = max(0, int(xlim[0]))
        x2 = min(data.shape[1], int(xlim[1]) + 1)
        y1 = max(0, int(ylim[1]))  # Y axis is inverted
        y2 = min(data.shape[0], int(ylim[0]) + 1)
        
        return data[y1:y2, x1:x2, :]

    def _get_numpy_dtype(self, data_type_str):
        """Convert data type string to numpy dtype"""
        dtype_map = {
            'Float32': np.float32,
            'Float64': np.float64,
            'UInt16': np.uint16,
            'Int16': np.int16,
            'UInt32': np.uint32,
            'Int32': np.int32
        }
        return dtype_map.get(data_type_str, np.float32)

    def _remove_layer_by_index(self, row):
        self.layer_list.setCurrentRow(row)
        self.remove_selected_layer()

    def _on_mouse_press_For_plot(self, event):
        if event.inaxes == self.ax and event.button == 1:  # Left click
            self._press_pos = (event.x, event.y)

    def _on_mouse_release_For_plot(self, event):
        if event.inaxes == self.ax and event.button == 1:
            if hasattr(self, "_press_pos"):
                dx = abs(event.x - self._press_pos[0])
                dy = abs(event.y - self._press_pos[1])
                if dx < 5 and dy < 5:  # Threshold to detect click
                    self._on_image_click(event)  # Actual click
            self._press_pos = None


    # ---------------- MENU ACTIONS ----------------


    def load_image(self):
        """Load a hyperspectral image using the HyperspectralImageLoader."""
        logging.info("="*80)
        logging.info("START: User initiated Load Image operation")
        logging.info("="*80)

        # loaders = HyperspectralImageLoader.open_file_dialog(parent=self)
        self.statusBar().showMessage("Opening file dialog...", 2000)
        logging.info("Opening file dialog for user to select image file(s)...")
        loaders = HyperspectralImageLoader.open_file_dialog(parent=self)
        self.statusBar().showMessage("Loading hyperspectral data... Please wait for large files.", 0)

        if loaders is None:
            logging.warning("Image loading cancelled by user.")
            self.statusBar().showMessage("Image loading cancelled.", 5000)
            return
        try:
            for i, loader in enumerate(loaders):
                if loader and loader.is_loaded:
                    # self.statusBar().showMessage(f"Processing dataset {i+1}/{len(loaders)}...", 0)
                    logging.info(f"---\nProcessing file {i+1}/{len(loaders)}")
                    logging.info(f"File path: {loader.file_path}")
                    
                    # Assign the loaded data from the loader object's attributes
                    self.image_data = loader.image_data
                    self.band_names = loader.band_names
                    self.metadata = loader.metadata # You can still access the raw dict
                    self.geotransform = loader.geotransform
                    self.projection = loader.projection
                    self.wavelengths = loader.wavelengths # Now directly available!
                    self.wavelength_units = loader.wavelength_units
                    self.file_name = os.path.splitext(os.path.basename(loader.file_path))[0]

                    print(f"Zero {np.sum(self.image_data ==0)}")
                    print(f"Nan {np.sum(np.isnan(self.image_data))}")
                    print(f"Negative {np.sum(self.image_data < 0)}")

                    new_layer = {
                        "name": self.file_name,
                        "data": self.image_data,
                        "band_names": self.band_names,
                        "metadata": self.metadata,
                        "geotransform": self.geotransform,
                        "projection": self.projection,
                        "visible": True
                    }
                    # Add the complete dictionary to the layers list
                    self.layers.insert(0, new_layer)
                    logging.info(f"Layer added to layer list: '{self.file_name}'")

                    self._refresh_layer_list()
                    logging.info(f"Layer list refreshed. Total layers: {len(self.layers)}")
                    
                    # Make the new layer active
                    # self.layer_list.setCurrentRow(0)
                    self._update_band_combos_for_active_layer()
                    logging.info(f"Band combos updated for active layer")
                    
                    self._update_display()
                    logging.info(f"Display updated")
                    
            if loaders:
                QTimer.singleShot(100, self.fit_image_to_display)
                logging.info(f"Image fit to display scheduled")
            
            logging.info("="*80)
            logging.info(f"COMPLETED: Successfully loaded {len([l for l in loaders if l and l.is_loaded])} image(s)")
            logging.info("="*80)

        except Exception as e:
            logging.error(f"ERROR during image loading: {str(e)}", exc_info=True)
            logging.error("="*80)
            QErrorMessage(self).showMessage(f"Error loading image: {e}")

    def animate_bands(self):
        """Launches the animation viewer for the currently selected layer."""
        if not (0 <= self.active_layer_index < len(self.layers)):
            QErrorMessage(self).showMessage("No layer selected.")
            return

        if self.animation_window and self.animation_window.isVisible():
            self.animation_window.activateWindow()
            return
            
        active_layer = self.layers[self.active_layer_index]
        layer_data = active_layer["data"]
        band_names = active_layer["band_names"]
        layer_name = active_layer["name"]
        
        self.animation_window = AnimationViewerWindow(
            image_data=layer_data,
            band_names=band_names,
            title=f"Band Animation: {layer_name}",
            parent=self
        )
        self.animation_window.show()

    def open_image_in_new_window(self):
            """Open the currently selected layer in a separate ImageViewerWindow instance."""
            idx = self.layer_list.currentRow()
            if idx < 0 or idx >= len(self.layers):
                QErrorMessage(self).showMessage("No layer selected.")
                return

            layer = self.layers[idx]
            try:
                # Create a new top-level viewer window
                new_win = ImageViewerWindow(parent=None)

                # Create a shallow copy of data to avoid accidental shared-state modifications.
                data_copy = layer["data"].copy()

                # Add as a new layer in the new window and copy metadata/geo
                new_win.add_layer(data_copy, name=f"{layer.get('name','Layer')}")
                # carry over metadata and spatial info if present
                new_win.layers[0].update({
                    "metadata": layer.get("metadata", {}).copy(),
                    "geotransform": layer.get("geotransform"),
                    "projection": layer.get("projection"),
                    "band_names": layer.get("band_names", new_win.layers[0].get("band_names", []))
                })
                new_win._refresh_layer_list()
                new_win.layer_list.setCurrentRow(0)
                new_win._update_band_combos_for_active_layer()
                new_win._update_display()

                # new_win.show()

                self.child_viewer_windows.append(new_win)  # Keep a reference to prevent garbage collection
                new_win.destroyed.connect(lambda _, w=new_win: self.child_viewer_windows.remove(w) if w in self.child_viewer_windows else None)
                new_win.show()


            except Exception as e:
                QErrorMessage(self).showMessage(f"Could not open image in new window: {e}")

    def remove_selected_layer(self):
        """Removes the selected layer from the list."""
        # 1. Get the currently selected row
        selected_row = self.layer_list.currentRow()
        if selected_row < 0:
            # Nothing is selected, so do nothing.
            logging.warning("Remove layer requested but no layer is selected")
            return

        logging.info("="*80)
        logging.info(f"START: Removing layer at index {selected_row}")
        removed_layer_name = self.layers[selected_row]["name"] if selected_row < len(self.layers) else "Unknown"
        logging.info(f"Layer name: '{removed_layer_name}'")

        # 2. Remove the layer from the data model first
        del self.layers[selected_row]
        logging.info(f"Layer removed from data model. Remaining layers: {len(self.layers)}")
        
        # 3. Refresh the UI list widget
        self._refresh_layer_list() # This will remove the item from the visual list
        logging.info(f"Layer list UI refreshed")

        # 4. Handle the new application state (either items remain or it's empty)
        if self.layers:
            # --- Layers still exist, so select the next logical item ---
            # If we deleted the last item, select the new last item.
            # Otherwise, select the item that took the deleted one's place.
            new_index = min(selected_row, len(self.layers) - 1)
            self.active_layer_index = new_index
            self.layer_list.setCurrentRow(new_index)
            logging.info(f"New active layer set to index {new_index}: '{self.layers[new_index]['name']}'")
            
            # Update UI components for the newly selected layer
            self._update_band_combos_for_active_layer()
            self._update_display()
            logging.info(f"Display and controls updated for new active layer")
        else:
            # --- No layers are left, so clear everything ---
            self.active_layer_index = -1
            logging.info(f"No layers remaining. Display cleared")
            
            # Clear any UI components that depend on a layer
            # For example, clear the band dropdowns and the main image view
            self.single_band_combo.clear()
            self.r_combo.clear()
            self.g_combo.clear()
            self.b_combo.clear()
            self.ax.clear()
            self._update_display()

    # ---------------- LAYER PANEL HELPERS ----------------
    def _refresh_layer_list(self):
        """Rebuild the list widget from self.layers. Top list item is top-most layer."""
        self.layer_list.blockSignals(True)
        self.layer_list.clear()
        for layer in self.layers:
            item = QListWidgetItem(layer["name"])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)
            item.setCheckState(Qt.Checked if layer["visible"] else Qt.Unchecked)
            self.layer_list.addItem(item)
        self.layer_list.blockSignals(False)

    def _on_layer_item_changed(self, item: QListWidgetItem):
        logging.info("Layer item changed signal received.")
        """Checkbox toggled → update visibility and redraw."""
        row = self.layer_list.row(item)
        if 0 <= row < len(self.layers):
            self.layers[row]["visible"] = (item.checkState() == Qt.Checked)
            self._update_display()

    def _sync_layers_from_list(self):
        """After drag/drop, sync the order of self.layers with the list widget."""
        new_order = []
        for i in range(self.layer_list.count()):
            name = self.layer_list.item(i).text()
            # find corresponding layer by name (names are unique per load)
            for lyr in self.layers:
                if lyr["name"] == name:
                    new_order.append(lyr)
                    break
        if len(new_order) == len(self.layers):
            self.layers = new_order
            # keep active index consistent with selection
            self.active_layer_index = self.layer_list.currentRow()
            self._update_display()

    def _on_active_layer_changed(self):
        """When selection changes, update band combos to reflect selected layer."""
        idx = self.layer_list.currentRow()
        if idx < 0:
            return
        self.active_layer_index = idx
        self._update_band_combos_for_active_layer()
        self._update_display()

    def _update_band_combos_for_active_layer(self):
        """Populate Single/RGB combos with the active layer's band names."""
        if not (0 <= self.active_layer_index < len(self.layers)):
            return
        active_layer = self.layers[self.active_layer_index]
        names = active_layer["band_names"]
        bands = active_layer["data"].shape[2]

        # Enable/disable RGB by band count
        self.rgb_radio.setEnabled(bands >= 3)

        # Rebuild combos
        def refill(combo: QComboBox, count: int, default_idx: int):
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(names[:count] if len(names) >= count else names)
            combo.setCurrentIndex(min(default_idx, combo.count() - 1) if combo.count() else -1)
            combo.blockSignals(False)

        refill(self.single_band_combo, bands, 0)
        refill(self.r_combo, bands, 0)
        refill(self.g_combo, bands, 1 if bands >= 2 else 0)
        refill(self.b_combo, bands, 2 if bands >= 3 else 0)

    # ---------------- DISPLAY PIPELINE ----------------
    def _on_mode_change(self) -> None:
        logging.info("Display mode changed to %s.", "Single" if self.single_band_radio.isChecked() else "RGB")
        self.current_mode = MODE_SINGLE if self.single_band_radio.isChecked() else MODE_RGB
        self._update_controls_for_mode()
        self._update_display()

    def _update_controls_for_mode(self) -> None:
        logging.info("Updating controls for mode: %s", self.current_mode)
        is_single = self.current_mode == MODE_SINGLE
        self.single_band_group.setVisible(is_single)
        self.rgb_group.setVisible(not is_single)

    def _normalize_for_display(self, band_data: np.ndarray) -> np.ndarray:
        logging.info(f"Normalizing {band_data.shape} and {band_data.dtype} band data for display.")
        band_float = band_data.astype(np.float32)
        p_low, p_high = np.percentile(band_float, (2, 98))
        if p_high == p_low:
            return np.zeros_like(band_float)
        clipped = np.clip(band_float, p_low, p_high)
        return (clipped - p_low) / (p_high - p_low)

    def _render_layer_image(self, layer) -> np.ndarray:
        """Return an HxWx3 (RGB) or HxW array normalized for display based on current mode & active layer combos."""
        data = layer["data"]

        h, w, b = data.shape

        if self.current_mode == MODE_RGB and b >= 3:
            # Use the active layer's index choices only if this layer has enough bands
            r_idx = min(self.r_combo.currentIndex(), b - 1) if self.r_combo.count() else 0
            g_idx = min(self.g_combo.currentIndex(), b - 1) if self.g_combo.count() else min(1, b - 1)
            b_idx = min(self.b_combo.currentIndex(), b - 1) if self.b_combo.count() else min(2, b - 1)

            r = self._normalize_for_display(data[:, :, r_idx])
            g = self._normalize_for_display(data[:, :, g_idx])
            b = self._normalize_for_display(data[:, :, b_idx])
            logging.info(f"Rendering RGB with bands R:{r_idx}, G:{g_idx}, B:{b_idx}")

            return np.stack([r, g, b], axis=-1)

        # Single-band (or fallback if fewer than 3 bands)
        sb_idx = min(self.single_band_combo.currentIndex(), b - 1) if self.single_band_combo.count() else 0
        return self._normalize_for_display(data[:, :, sb_idx])

    def _subsample_for_display(self, image_data: np.ndarray, max_display_size: int = 2048) -> np.ndarray:
        """Subsample large images for faster display"""
        rows, cols = image_data.shape[:2]
        
        if rows <= max_display_size and cols <= max_display_size:
            return image_data
        
        # Calculate subsampling factor
        factor = max(rows // max_display_size, cols // max_display_size) + 1
        
        # Subsample spatially but keep all bands
        return image_data[::factor, ::factor, :]



    def _update_display(self) -> None:
        try:
            # Preserve any existing viewport extent (limits) so we don't reset them
            try:
                prev_xlim = self.ax.get_xlim()
                prev_ylim = self.ax.get_ylim()
            except Exception:
                prev_xlim, prev_ylim = None, None

            # Consider prev limits meaningful if they are not matplotlib's default (0.0, 1.0)
            use_prev_extent = False
            if prev_xlim is not None and prev_ylim is not None:
                try:
                    if not (np.allclose(prev_xlim, (0.0, 1.0)) and np.allclose(prev_ylim, (0.0, 1.0))):
                        use_prev_extent = True
                except Exception:
                    use_prev_extent = True

            # Now clear the axes to redraw, but we will restore limits below when appropriate
            self.ax.clear()
            #debug
            print("Updating display with layers:", [lyr["name"] for lyr in self.layers])

            if not self.layers:
                self.ax.axis('off')
                self.canvas.draw_idle()
                # self.canvas.draw()
                self.status_bar.showMessage("No layers to display", 3000)
                return

            # Draw layers from bottom to top
            for i in range(len(self.layers) - 1, -1, -1):
                layer = self.layers[i]
                if not layer.get("visible", True):
                    continue

                img = self._render_layer_image(layer)

                if img is None:
                    logging.warning(f"Layer '{layer.get('name', 'Unknown')}' returned no image")
                    continue
                img_h, img_w = img.shape[:2]
                

                if img.ndim == 2:
                    logging.info(f"Displaying grayscale image of shape {img.shape}")
                    self.ax.imshow(img, cmap='gray', alpha=1.0, interpolation='nearest')#, aspect='auto')
                elif img.ndim == 3 and img.shape[2] in (3, 4):
                    logging.info(f"Displaying RGB image of shape {img.shape}")
                    self.ax.imshow(img, alpha=1.0, interpolation='nearest')#, aspect='auto')

                # Defer setting extent until after all layers are drawn. We don't
                # want to override user panning/zooming if an extent already exists.
                self.ax.axis('off')
                self.ax.autoscale(False)

            # Restore previous extent (if it was meaningful) instead of forcing
            # the axes to canvas-size on every update. This preserves panning/zoom
            # performed by the user or programmatically set limits.
            try:
                if use_prev_extent and prev_xlim is not None and prev_ylim is not None:
                    self.ax.set_xlim(prev_xlim)
                    self.ax.set_ylim(prev_ylim)
                else:
                    canva_x_lmit, canva_y_lmit = self.canvas.get_width_height()
                    self.ax.set_xlim(0, canva_x_lmit)
                    self.ax.set_ylim(canva_y_lmit, 0)
            except Exception:
                # If restoring limits fails for any reason, ignore and continue
                pass

            self.canvas.draw_idle()
            self.status_bar.showMessage("Display updated", 2000)

        except Exception as e:
            logging.error(f"Error updating display: {str(e)}", exc_info=True)
            self.status_bar.showMessage(f"Display update error: {str(e)}", 5000)

    # ---------------- INTERACTIONS ----------------


    # This new version finds the topmost visible layer before getting pixel data.
    def _on_image_click(self, event) -> None:
        if not event.inaxes == self.ax or event.xdata is None or event.ydata is None:
            return

        # 1. Find the topmost visible layer in the layer list
        top_layer = None

        for layer in self.layers:
            if layer.get("visible", True):
                top_layer = layer
                break # Stop after finding the first one

        if top_layer is None:
            self.status_bar.showMessage("No visible layers to inspect.", 3000)
            return

        try:
            x, y = int(event.xdata), int(event.ydata)

            # Bounds check using the found layer's data
            h, w = top_layer["data"].shape[:2]
            if not (0 <= x < w and 0 <= y < h):
                return

            # 2. Use the data from that specific 'top_layer'
            if self.pixel_info_window is None or not self.pixel_info_window.isVisible():
                self.pixel_info_window = PixelInfoWindow(
                    file_name=top_layer["name"],
                    image_data=top_layer["data"],
                    band_names=top_layer["band_names"],
                    metadata=top_layer.get("metadata", {}),
                    geotransform=top_layer.get("geotransform"),
                    projection=top_layer.get("projection"),
                    x=x, y=y, parent=self
                )
                self.pixel_info_window.show()
            else:
                # 3. If window is already open, call a new update method
                self.pixel_info_window.update_data(
                    file_name=top_layer["name"],
                    image_data=top_layer["data"],
                    band_names=top_layer["band_names"],
                    metadata=top_layer.get("metadata", {}),
                    geotransform=top_layer.get("geotransform"),
                    projection=top_layer.get("projection"),
                    x=x, y=y
                )
                self.pixel_info_window.activateWindow()

        except Exception as e:
            QErrorMessage(self).showMessage(f"Error retrieving pixel info: {e}")


    def _on_scroll_zoom(self, event) -> None:
        if self._aoi_active or event.xdata is None or event.ydata is None:
            return
        scale_factor = 1 / ZOOM_FACTOR if event.button == 'up' else ZOOM_FACTOR
        cur_xlim = self.ax.get_xlim()
        cur_ylim = self.ax.get_ylim()
        xdata, ydata = event.xdata, event.ydata
        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
        relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])
        self.ax.set_xlim([xdata - new_width * (1 - relx), xdata + new_width * relx])
        self.ax.set_ylim([ydata - new_height * (1 - rely), ydata + new_height * rely])
        self.canvas.draw_idle()

    def _on_mouse_press(self, event):
        

        if self._aoi_active or event.inaxes != self.ax:
            return
        if event.button in [1, 2, 3]:
            self._is_panning = True
            self._pan_start = (event.xdata, event.ydata)
            self._cur_xlim = self.ax.get_xlim()
            self._cur_ylim = self.ax.get_ylim()

    def _on_mouse_release(self, event):
        self._is_panning = False

    def _on_mouse_move(self, event):
        if not self._is_panning or event.xdata is None or event.ydata is None:
            return
        dx = event.xdata - self._pan_start[0]
        dy = event.ydata - self._pan_start[1]
        self.ax.set_xlim(self._cur_xlim[0] - dx, self._cur_xlim[1] - dx)
        self.ax.set_ylim(self._cur_ylim[0] - dy, self._cur_ylim[1] - dy)
        self.canvas.draw_idle()

    # ---------------- PRE/POST ----------------


    def closeEvent(self, event):
        """Ensure child windows are closed when this window is closed."""
        if self.pixel_info_window:
            self.pixel_info_window.close()
        if self.animation_window: 
            self.animation_window.close()
        if self.active_processor and self.active_processor.mnf_viewer_window:
            self.active_processor.mnf_viewer_window.close()
        # Close any externally opened image viewer windows kept to prevent GC
        for w in list(getattr(self, "child_viewer_windows", [])):
            try:
                w.close()
            except Exception:
                pass

        # Safely close MNF viewer if present
        if getattr(self, "active_processor", None) and getattr(self.active_processor, "mnf_viewer_window", None):
            try:
                self.active_processor.mnf_viewer_window.close()
            except Exception:
                pass

        super().closeEvent(event)


    def add_layer(self, image_data, name="New Layer"):
        """A helper method to add a new layer programmatically."""
        logging.info("="*80)
        logging.info(f"START: Adding new layer - '{name}'")
        logging.info(f"Image shape: {image_data.shape}")
        
        band_names = [f"Band {i+1}" for i in range(image_data.shape[2])]
        new_layer = {
            "name": name,
            "data": image_data.astype(np.float32),
            "visible": True,
            "band_names": band_names
        }
        self.layers.insert(0, new_layer) # Add to the top
        logging.info(f"Layer '{name}' inserted at position 0 (top)")
        logging.info(f"Total layers now: {len(self.layers)}")
        
        self._refresh_layer_list()
        logging.info(f"Layer list refreshed")
        
        self.layer_list.setCurrentRow(0) # Make it the active layer
        logging.info(f"Layer '{name}' set as active layer")
        logging.info(f"COMPLETED: New layer '{name}' added successfully")
        logging.info("="*80)


    def Bad_Band_Removal(self):
        print("Bad Band Removal clicked")

    def PCA(self):
        print("PCA clicked")

    def ICA(self):
        print("ICA clicked")

    def MNF(self):
        logging.info("="*80)
        logging.info("START: MNF (Minimum Noise Fraction) processing initiated")
        
        try:
            if not (0 <= self.active_layer_index < len(self.layers)):
                logging.warning("MNF requested but no layer is active")
                QErrorMessage(self).showMessage("No layer selected. Please select a layer first.")
                return
            
            active_layer_data = self.layers[self.active_layer_index]["data"]
            active_layer_name = self.layers[self.active_layer_index]["name"]
            logging.info(f"Active layer: '{active_layer_name}'")
            logging.info(f"Layer shape: {active_layer_data.shape}")
            
            # Pass the data and a reference to the viewer window itself
            processor = MNFProcessor(active_layer_data, active_layer_name)
            logging.info("MNFProcessor created successfully")
            
            processor.display_interactive_mnf(parent_viewer=self)
            logging.info("Interactive MNF window displayed")

            # Note: We keep the processor in memory to keep the window alive
            # A more advanced solution might store it in a list of active processors
            self.active_processor = processor
            logging.info("COMPLETED: MNF processing window opened")
            logging.info("="*80)

        except Exception as e:
            logging.error(f"ERROR in MNF processing: {str(e)}", exc_info=True)
            logging.error("="*80)
            QErrorMessage(self).showMessage(f"MNF error: {e}")

    def _raster_analysis(self):
        logging.info("="*80)
        logging.info("START: Raster Analysis (Calculator) initiated")
        
        try:
            if not self.layers: # Check if any layers are loaded at all
                logging.warning("Raster Analysis requested but no layers are loaded")
                QErrorMessage(self).showMessage("No layers loaded. Please load an image first.")
                return
            
            logging.info(f"Total layers available: {len(self.layers)}")
            for idx, layer in enumerate(self.layers):
                logging.info(f"  Layer {idx}: '{layer['name']}' - Shape: {layer['data'].shape}")
            
            #checking for its wavelengths attribute

            # Keep a single instance of the window to avoid duplicates
            if self.raster_analysis_window and self.raster_analysis_window.isVisible():
                logging.info("Raster Analysis window already open, activating it")
                self.raster_analysis_window.activateWindow()
                return
            
            logging.info("Creating new Raster Calculator window")
            # Pass the ENTIRE list of layers to the calculator
            self.raster_analysis_window = RasterCalculatorWindow(
                all_layers=self.layers, 
                parent=self
            )
            
            # The signal/slot connection remains the same
            self.raster_analysis_window.calculation_complete.connect(self._add_new_layer_from_analysis)
            logging.info("Raster Calculator window created and connected")
            
            self.raster_analysis_window.show()
            logging.info("COMPLETED: Raster Calculator window displayed")
            logging.info("="*80)
            
        except Exception as e:
            logging.error(f"ERROR in Raster Analysis: {str(e)}", exc_info=True)
            logging.error("="*80)
            QErrorMessage(self).showMessage(f"Raster Analysis error: {e}")
            
# --- ADD THIS ENTIRE FUNCTION ---
    def _add_new_layer_from_analysis(self, result_array, layer_name, parent_layer_name):
            """
            This slot receives the data from the RasterCalculatorWindow and adds it
            as a new layer to the application.
            """
            logging.info("="*80)
            logging.info("START: Adding new layer from analysis/calculation")
            logging.info(f"New layer name: '{layer_name}'")
            logging.info(f"Result array shape: {result_array.shape}")
            logging.info(f"Data type: {result_array.dtype}")
            logging.info(f"Parent layer: '{parent_layer_name}'")
            
            try:
                # 1. Get metadata from the specific parent layer passed by the calculator
                parent_metadata = {}
                parent_geotransform = None
                parent_projection = None
                #checking the attribute of layers
                logging.info(f"Current layers before addition: {[lyr['name'] for lyr in self.layers]}")
                if parent_layer_name:
                    # parent_layer = self._find_layer_by_name(parent_layer_name)
                    parent_layer = next((layer for layer in self.layers if layer["name"] == parent_layer_name), None)
                    
                    if parent_layer:
                        parent_metadata = parent_layer.get("metadata", {})
                        parent_geotransform = parent_layer.get("GeoTransform", None)
                        parent_projection = parent_layer.get("Projection", None)
                        logging.info(f"Using metadata from parent layer '{parent_layer_name}'")
                        logging.info(f"Parent projection: {parent_projection}")
                    else:
                        logging.warning(f"Parent layer '{parent_layer_name}' not found. Using default metadata.")
                else:
                    logging.info("No parent layer specified. Using default metadata.")

                layer_metadata = parent_metadata.copy() if parent_metadata else {}
                # Remove wavelength fields if present
                layer_metadata.pop("wavelength", None)
                layer_metadata.pop("Wavelengths", None)
                layer_metadata.pop("wavelength_units", None)
                layer_metadata.pop("bands", None)
                layer_metadata.pop("fwhm", None)
                layer_metadata.pop("FWHM", None)
                layer_metadata.pop("band_names", None)

                # Determine band count
                if result_array.ndim == 2:
                    band_count = 1
                elif result_array.ndim == 3:
                    band_count = result_array.shape[2]
                else:
                    raise ValueError(f"Unexpected array shape: {result_array.shape}")

                logging.info(f"Band count in result: {band_count}")

                # Update band count in metadata
                layer_metadata["band_count"] = band_count
                layer_metadata["RasterCount"] = band_count  # keep consistency with GDAL-style key               

                layer_metadata["Data Type"] = str(result_array.dtype)


                # 1. Create a new layer dictionary for your application
                new_layer = {
                    "name": layer_name,
                    "data": result_array,
                    "band_names": (
                            ["Band 1"] if result_array.ndim == 2 
                            else [f"Band {i+1}" for i in range(result_array.shape[2])]
                        ),  # The result is a single-band raster
                    "metadata": layer_metadata,  # Use parent layer's metadata if available
                    "geotransform": parent_geotransform,
                    "projection": parent_projection,
                    # "Band_Count": result_array.shape[2] if result_array.ndim == 3 else 1,
                    "dtype": str(result_array.dtype),
                    "visible": True
                }
                logging.info(f"New layer dictionary created with {band_count} band(s)")
                
                #adding metadata to new layer
                new_layer["metadata"]["Data Type"] = new_layer["dtype"]
                
                # This assumes your main window has a list called `self.layers`
                self.layers.insert(0, new_layer)  # Add to the top of the list
                logging.info(f"Layer '{layer_name}' inserted at position 0")
                logging.info(f"Total layers now: {len(self.layers)}")
                logging.info(f"Current layers: {[lyr['name'] for lyr in self.layers]}")
                
                self._refresh_layer_list()  # Refresh the UI list to show the new layer
                logging.info("Layer list UI refreshed")
                
                self.layer_list.setCurrentRow(0)  # Select the new layer
                logging.info(f"New layer '{layer_name}' set as active")
                
                self._update_band_combos_for_active_layer()  # Update band combos
                logging.info("Band combos updated")
                
                self._update_display()  # Refresh the main display to include the new layer
                logging.info("Display updated")
            
                logging.info("="*80)
                logging.info(f"COMPLETED: New layer '{layer_name}' added successfully")
                logging.info("="*80)
                QMessageBox.information(self, "Success", f"Successfully added layer:\n'{layer_name}'")

            except Exception as e:
                logging.error(f"ERROR while adding new layer from analysis: {str(e)}", exc_info=True)
                logging.error("="*80)
                QMessageBox.critical(self, "Error", f"Could not add new layer: {e}")

    # ---------------- PPI CALCULATOR ---------------
# 
    def _PPI_Calculator(self):
        print("PPI button Clicked")
        logging.info("PPI Button Clicked")

        self.PPI_window = PPI_Workflow_Window(layers=self.layers)
        print("Successfully craeted window:::::::::::::::::::::::::")
        self.PPI_window.show()


