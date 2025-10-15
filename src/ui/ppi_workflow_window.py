import os
os.environ["VISPY_BACKEND"] = "pyside6"

import numpy as np
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QGroupBox,
    QLabel, QProgressBar, QSpinBox, QTabWidget, QWidget, QCheckBox,
 QMessageBox, QMainWindow, QDockWidget, QToolBar,QDoubleSpinBox
)
from PySide6.QtCore import QThread, Signal, Slot, Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from PySide6.QtGui import QAction

import cupy as cp
from scipy.stats import gaussian_kde




from src.core.ppi_processor import PPI_Processor
from src.core.plot_window import PlotWindow, PlotWindow_2D

class Worker(QThread):
    """A generic worker thread for running long tasks."""
    finished = Signal(object)
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class PPI_Workflow_Window(QMainWindow):
    
    def __init__(self, layers: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PPI Workflow")
        self.setMinimumSize(1000, 800)
        self.processor = PPI_Processor()
        for layer in layers:
            self.processor.add_layer(layer)
        print("Entered PPI_Workflow_Window...")
        
        # Initialize plot windows
        self.ppi_window = None
        self.endmember_window = None
        self.abundance_window = None
        self.nd_visualizer_window = None
        
        self._setup_ui()
        self._connect_signals()
        self._initialize_layer_selection()
        self._update_workflow_state()

    def _setup_ui(self):
        """Build the main user interface."""
        self.setStyleSheet("QGroupBox { font-weight: bold; } QPushButton { padding: 5px; }")
        main_layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar = QToolBar("Workflow Tools")
        save_action = QAction("Save Results", self)
        save_action.setToolTip("Save current workflow results")
        reset_action = QAction("Reset Workflow", self)
        reset_action.setToolTip("Reset all processing steps")
        toolbar.addAction(save_action)
        toolbar.addAction(reset_action)
        main_layout.addWidget(toolbar)
        
        # Control Panel (Dockable)
        self.control_dock = QDockWidget("Control Panel", self)
        control_widget = QWidget()
        control_layout = QHBoxLayout(control_widget)
        
        # Input Data Group
        input_group = QGroupBox("1. Input Data")
        input_layout = QVBoxLayout(input_group)

        self.processing_layer_combo = QComboBox()
        input_layout.addWidget(QLabel("Select Processing Layer (MNF):"))
        input_layout.addWidget(self.processing_layer_combo)

        self.original_layer_combo = QComboBox()
        input_layout.addWidget(QLabel("Select Original Layer (Full-Band):"))
        input_layout.addWidget(self.original_layer_combo)

        self.set_layers_btn = QPushButton("Set Input Layers")
        input_layout.addWidget(self.set_layers_btn)

        control_layout.addWidget(input_group)
        
        # PPI Group
        ppi_group = QGroupBox("2. Pixel Purity Index (PPI)")
        ppi_layout = QVBoxLayout(ppi_group)
        self.ppi_iterations_spin = QSpinBox()
        self.ppi_iterations_spin.setRange(10,50000)
        self.ppi_iterations_spin.setValue(10000)
        self.ppi_iterations_spin.setSingleStep(1000)
        self.ppi_iterations_spin.setToolTip("Number of iterations for PPI calculation")

        # Threshold input
        self.ppi_threshold_spin = QDoubleSpinBox()
        self.ppi_threshold_spin.setRange(0.0, 5.0)   # Assuming threshold is between 0 and 1
        self.ppi_threshold_spin.setSingleStep(0.01)
        self.ppi_threshold_spin.setValue(0.10)       # Default value
        self.ppi_threshold_spin.setToolTip("Threshold factor for PPI extrema detection")



        self.run_ppi_btn = QPushButton("Run PPI Calculation")
        self.run_ppi_btn.setToolTip("Calculate PPI scores for the selected layer")
        ppi_layout.addWidget(QLabel("Number of Iterations:"))
        ppi_layout.addWidget(self.ppi_iterations_spin)
        ppi_layout.addWidget(self.ppi_threshold_spin)
        ppi_layout.addWidget(self.run_ppi_btn)
        control_layout.addWidget(ppi_group)
        
        # Endmember Extraction Group
        endmember_group = QGroupBox("3. Endmember Extraction")
        endmember_layout = QVBoxLayout(endmember_group)
        self.num_endmembers_spin = QSpinBox()
        self.num_endmembers_spin.setRange(2, 20)
        self.num_endmembers_spin.setValue(5)
        self.num_endmembers_spin.setToolTip("Number of endmembers to extract")
        self.extract_endmembers_btn = QPushButton("Extract Endmembers")
        self.extract_endmembers_btn.setToolTip("Extract endmembers using PPI scores")
        self.nd_visualizer_btn = QPushButton("Open n-D Visualizer")
        self.nd_visualizer_btn.setToolTip("Visualize endmembers in n-D space")
        endmember_layout.addWidget(QLabel("Number of Endmembers to Find:"))
        endmember_layout.addWidget(self.num_endmembers_spin)
        endmember_layout.addWidget(self.extract_endmembers_btn)
        endmember_layout.addWidget(self.nd_visualizer_btn)
        control_layout.addWidget(endmember_group)
        
        # Abundance Mapping Group
        abundance_group = QGroupBox("4. Abundance Mapping (fcls)")
        abundance_layout = QVBoxLayout(abundance_group)
        self.shade_checkbox = QCheckBox("Add Shade Endmember")
        self.shade_checkbox.setChecked(True)
        self.shade_checkbox.setToolTip("Include a shade endmember in abundance mapping")
        self.run_abundance_btn = QPushButton("Generate Abundance Maps")
        self.run_abundance_btn.setToolTip("Generate abundance maps for endmembers")
        abundance_layout.addWidget(self.shade_checkbox)
        abundance_layout.addWidget(self.run_abundance_btn)
        control_layout.addWidget(abundance_group)
        
        self.control_dock.setWidget(control_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.control_dock)
        
        # Status Bar
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Ready. Select a layer to begin.")
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.progress_bar)
        main_layout.addLayout(status_layout)
        
        print("Successfully created all layout...")

    def _initialize_layer_selection(self):
        """Populates both combo boxes with available layer names."""
        # Clear old items first
        self.processing_layer_combo.clear()
        self.original_layer_combo.clear()
        
        for layer in self.processor.all_layers:
            self.processing_layer_combo.addItem(layer['name'])
            self.original_layer_combo.addItem(layer['name'])
        
        if not self.processor.all_layers:
            self.status_label.setText("No layers available.")
            self._update_workflow_state(False)
        else:
            self._update_workflow_state(False) # Layers are available, but not set yet


    @Slot()
    def _on_set_layers(self):
        """Handles setting both layers in the backend processor."""
        proc_idx = self.processing_layer_combo.currentIndex()
        orig_idx = self.original_layer_combo.currentIndex()
        
        if proc_idx < 0 or orig_idx < 0:
            QMessageBox.warning(self, "Input Error", "Please select valid layers.")
            return
            
        if proc_idx >= len(self.processor.all_layers) or orig_idx >= len(self.processor.all_layers):
            QMessageBox.warning(self, "Input Error", "Selected layer index is invalid.")
            return
        
        try:
            self._cleanup_child_windows()  # Clear old plots
            self.processor.set_input_layers(proc_idx, orig_idx)
            self.status_label.setText("Input layers set successfully. Ready for PPI.")
            self._update_workflow_state(True)  # Enable the next step
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to set layers: {str(e)}")
            self.status_label.setText("Error setting layers.")

   
    def _connect_signals(self):
        """Connect UI element signals to handler slots."""
        # Connect the new button for setting input layers
        self.set_layers_btn.clicked.connect(self._on_set_layers)
        
        # Connect processing buttons
        self.run_ppi_btn.clicked.connect(self._run_ppi)
        self.extract_endmembers_btn.clicked.connect(self._extract_endmembers)
        # self.nd_visualizer_btn.clicked.connect(self._open_nd_visualizer)
        self.run_abundance_btn.clicked.connect(self._run_abundance_mapping)

    def _update_workflow_state(self,layerset=None):
        """
        Dynamically enable/disable workflow buttons based on processor state.
        This scales automatically when new steps/buttons are added.
        """

        # Mapping of button attributes to required processor attributes
        workflow_dependencies = {
            'run_ppi_btn': ['processing_layer', 'original_layer'],
            'extract_endmembers_btn': ['ppi_score'],
            'nd_visualizer_btn': ['endmembers'],
            'run_abundance_btn': ['endmembers'],
            # Add new buttons here:
            # 'new_button_attr': ['required_attr1', 'required_attr2'],
        }

        for btn_attr, required_attrs in workflow_dependencies.items():
            # Check if button exists in self
            button = getattr(self, btn_attr, None)
            if button is None:
                continue  # skip if button not defined

            # Check all required processor attributes
            enabled = all(getattr(self.processor, attr, None) is not None for attr in required_attrs)

            button.setEnabled(enabled)


    # def _update_workflow_state(self, layers_set=None):
    #     """Enable/disable buttons based on processing progress."""
    #     if layers_set is None:
    #         # Determine if layers are set based on processor state
    #         layers_set = (hasattr(self.processor, 'processing_layer') and 
    #                     hasattr(self.processor, 'original_layer') and 
    #                     self.processor.processing_layer is not None and 
    #                     self.processor.original_layer is not None)
        
    #     ppi_calculated = (hasattr(self.processor, 'ppi_scores') and 
    #                     self.processor.ppi_scores is not None)
    #     endmembers_extracted = (hasattr(self.processor, 'endmembers') and 
    #                         self.processor.endmembers is not None)
        
    #     self.run_ppi_btn.setEnabled(layers_set)
    #     self.extract_endmembers_btn.setEnabled(ppi_calculated)
    #     self.nd_visualizer_btn.setEnabled(endmembers_extracted)
    #     self.run_abundance_btn.setEnabled(endmembers_extracted)

    def _cleanup_child_windows(self):
        """Close and cleanup all child plot windows."""
        windows_to_close = [
            self.ppi_window, 
            self.endmember_window, 
            self.abundance_window, 
            self.nd_visualizer_window
        ]
        
        for window in windows_to_close:
            if window and not window.isHidden():
                window.close()
        
        # Reset window references
        self.ppi_window = None
        self.endmember_window = None  
        self.abundance_window = None
        self.nd_visualizer_window = None


    def closeEvent(self, event):
        """Handle dialog closing with proper cleanup."""
        # Stop any running worker threads
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            self.worker.finished.disconnect()
            self.worker.error.disconnect() 
            self.worker.quit()
            self.worker.wait(3000)  # Wait up to 3 seconds
            if self.worker.isRunning():
                self.worker.terminate()
                self.worker.wait()
        
        # Close and cleanup plot windows
        self._cleanup_child_windows()
        
        super().closeEvent(event)


    def _start_task(self, func, on_finish_slot, *args):
        """Generic method to start a worker thread for a given task."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self._set_ui_enabled(False)
        
        self.worker = Worker(func, *args)
        self.worker.finished.connect(on_finish_slot)
        self.worker.error.connect(self._on_task_error)
        self.worker.start()

    def _on_task_error(self, error_message):
        """Handles errors from the worker thread."""
        self.progress_bar.setVisible(False)
        self._set_ui_enabled(True)
        if not self.isHidden():
            QMessageBox.critical(self, "Processing Error", f"An error occurred:\n{error_message}")
            self.status_label.setText("Error occurred. Please try again.")

    def _set_ui_enabled(self, enabled: bool):
        """Enable or disable all control buttons."""
        self.set_layers_btn.setEnabled(enabled)
        self.run_ppi_btn.setEnabled(enabled)
        self.extract_endmembers_btn.setEnabled(enabled) 
        self.nd_visualizer_btn.setEnabled(enabled)
        self.run_abundance_btn.setEnabled(enabled)
        if enabled:
            self._update_workflow_state()

    @Slot()
    def _run_ppi(self):
        """Run PPI calculation and display results in a separate window."""
        iterations = self.ppi_iterations_spin.value()
        threshold = self.ppi_threshold_spin.value()

        self.status_label.setText(f"Running PPI with {iterations} iterations...")
        self._start_task(self.processor.calculate_ppi, self._on_ppi_complete, iterations, threshold)

    @Slot(object)
    def _on_ppi_complete(self, result):
        """Handle PPI completion with ENVI-like advanced rendering."""
        # Hide progress and enable UI
        self.progress_bar.setVisible(False)
        self._set_ui_enabled(True)
        
        # Unpack results
        ppi_scores, projections, skewers = result  # skewers: list of (extreme_pos) for lines
        ppi_1d = ppi_scores.flatten()
        print(f"PPI complete: scores shape {ppi_scores.shape}, projections {projections.shape}")

 
    @Slot()
    def _extract_endmembers(self):
        """Run endmember extraction."""
        num_endmembers = self.num_endmembers_spin.value()
        self.status_label.setText(f"Extracting {num_endmembers} endmembers...")
        self._start_task(self.processor.extract_endmembers, self._on_endmembers_complete, num_endmembers)

    @Slot(object)
    def _on_endmembers_complete(self, result):
        """Handle endmember extraction completion."""
        endmembers, _, all_pixel = result
        self.all_pixels = all_pixel
        self.progress_bar.setVisible(False)
        self._set_ui_enabled(True)
        
        if not self.endmember_window:
            self.endmember_window = PlotWindow_2D("Endmember Spectra", self)
        
        def update_endmember_plot(fig):
            ax = fig.add_subplot(111)
            wavelengths = self.processor.original_layer.get('band_names', np.arange(endmembers.shape[1]))
            for i, spectrum in enumerate(endmembers):
                ax.plot(wavelengths, spectrum, label=f"Endmember {i+1}")
            ax.set_title("Extracted Endmember Spectra")
            ax.set_xlabel("Band Number / Wavelength")
            ax.set_ylabel("Reflectance (or DN)")
            ax.legend()
            ax.grid(True)
            fig.tight_layout()
        
        self.endmember_window.update_plot(update_endmember_plot)
        self.endmember_window.show()
        self.status_label.setText("Endmember extraction complete. Ready for abundance mapping or n-D visualization.")



    @Slot()
    def _run_abundance_mapping(self):
        """Run abundance mapping and display results in a separate window."""
        use_shade = self.shade_checkbox.isChecked()
        self.status_label.setText("Generating abundance maps...")
        self._start_task(self.processor.calculate_abundance_maps, self._on_abundance_maps_complete, use_shade)

    @Slot(object)
    def _on_abundance_maps_complete(self, abundance_maps):
        """Handle abundance mapping completion."""
        self.progress_bar.setVisible(False)
        self._set_ui_enabled(True)
        
        if not self.abundance_window:
            self.abundance_window = QMainWindow(self)
            self.abundance_window.setWindowTitle("Abundance Maps")
            central_widget = QWidget()
            self.abundance_window.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)
            self.abundance_tabs = QTabWidget()
            layout.addWidget(self.abundance_tabs)
        
        # Clear previous tabs
        while self.abundance_tabs.count() > 0:
            tab = self.abundance_tabs.widget(0)
            self.abundance_tabs.removeTab(0)
            if tab:
                tab.deleteLater()
        
        # Create new tabs
        num_maps = abundance_maps.shape[2]
        for i in range(num_maps):
            title = f"Endmember {i+1}"
            if self.shade_checkbox.isChecked() and i == num_maps - 1:
                title = "Shade"
            
            tab = QWidget(self.abundance_tabs)
            tab_layout = QVBoxLayout(tab)
            figure = Figure(figsize=(6, 5))
            canvas = FigureCanvas(figure)
            toolbar = NavigationToolbar(canvas, tab)
            canvas.setParent(tab)
            
            ax = figure.add_subplot(111)
            im = ax.imshow(abundance_maps[:, :, i], cmap='viridis', vmin=0, vmax=1)
            figure.colorbar(im, ax=ax)
            ax.axis('off')
            ax.set_title(f"Abundance Map: {title}")
            figure.tight_layout()
            
            tab_layout.addWidget(toolbar)
            tab_layout.addWidget(canvas)
            self.abundance_tabs.addTab(tab, title)
        
        self.abundance_window.show()
        self.status_label.setText("Workflow complete. Abundance maps generated.")



















