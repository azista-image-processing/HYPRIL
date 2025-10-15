# src/core/MNFProcessor.py

import numpy as np
import hyperspy.api as hs
from spectral import noise_from_diffs
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSlider, QSpinBox, QLabel, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
import  logging 

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MNFViewerWindow(QMainWindow):
    """
    An interactive window to view MNF components with navigation, animation,
    and an option to add the result as a new layer.
    """
    def __init__(self, mnf_components, eigenvalues, parent_viewer=None):
        super().__init__()
        self.mnf_components = mnf_components
        self.eigenvalues = eigenvalues
        self.num_components = mnf_components.shape[2]
        self.current_component = 0
        self.parent_viewer = parent_viewer  # Reference to the main ImageViewerWindow
        self.setWindowTitle("Interactive MNF Viewer")
        self.setGeometry(150, 150, 800, 700)

        # --- Main Layout ---
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # --- Matplotlib Canvas ---
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.addToolBar(self.toolbar)

        # --- Controls Layout ---
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
        self.jump_spinbox.setRange(1, self.num_components)
        self.jump_spinbox.valueChanged.connect(self.jump_to_component)
        controls_layout.addWidget(self.jump_spinbox)
        self.layout.addLayout(controls_layout)

        #adding selected component
        controls_layout.addWidget(QLabel("Component "))
        self.selected_component = QSpinBox()
        # self.selected_component.setMinimum(1)   # Component numbers start at 1
        self.selected_component.setMaximum(self.num_components)  # Set max number of MNF components
        controls_layout.addWidget(self.selected_component)
        # Later, get integer input
        # selected_component = self.selected_component.value()
            
            # Add after your component selection SpinBox
        self.show_eigen_button = QPushButton("Show Eigenvalues")
        controls_layout.addWidget(self.show_eigen_button)

        # Connect the button click to the plotting function
        self.show_eigen_button.clicked.connect(self.plot_mnf_eigenvalues)

        # --- Animation Controls ---
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
        
        # --- Add to Layers Button ---
        if self.parent_viewer:
            self.add_layer_button = QPushButton("Add MNF Components to Viewer")
            self.add_layer_button.setStyleSheet("background-color: #4CAF50; color: white;")
            self.add_layer_button.clicked.connect(self.add_as_layer)
            self.layout.addWidget(self.add_layer_button)

        # --- Timer for Animation ---
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.animate_frame)
        
        self.show_component() # Initial display
        logger.info("MNF Viewer initialized.")
    def add_as_layer(self):
        """Adds the full MNF components cube as a new layer in the main viewer."""
            
        
        if self.parent_viewer:
            if self.selected_component is not None:
                comp_index = self.selected_component.value()
                print(f" mnf component shape: {self.mnf_components.shape}" )
                print(f" {comp_index} component selected for export")
                self.mnf_components= self.mnf_components[ : , : ,:comp_index]
                print(f" selected  component shape: {self.mnf_components.shape}" )

            self.parent_viewer.add_layer(
                image_data=self.mnf_components,
                name="MNF Components"
            )
            QMessageBox.information(self, "Success", "MNF components added as a new layer.")
            self.close() # Close the viewer after adding the layer

    def show_component(self):
        xlim, ylim = None, None
        if self.ax.images:
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()


        self.ax.imshow(self.mnf_components[:, :, self.current_component], cmap='gray')


        self.ax.set_title(f'MNF Component {self.current_component + 1} / {self.num_components}')
        self.ax.axis('off')

        if xlim and ylim:
            self.ax.set_xlim(xlim)
            self.ax.set_ylim(ylim)


        self.figure.tight_layout()
        self.canvas.draw()
        
        self.jump_spinbox.blockSignals(True)
        self.jump_spinbox.setValue(self.current_component + 1)
        self.jump_spinbox.blockSignals(False)

    def show_previous(self):
        if self.current_component > 0:
            self.current_component -= 1
            self.show_component()

    def show_next(self):
        if self.current_component < self.num_components - 1:
            self.current_component += 1
            self.show_component()

    def jump_to_component(self, value):
        self.current_component = value - 1
        self.show_component()

    def toggle_animation(self, checked):
        if checked:
            self.animation_timer.start(self.speed_slider.value())
            self.animate_button.setText("Stop Animation")
        else:
            self.animation_timer.stop()
            self.animate_button.setText("Animate")

    def animate_frame(self):
        self.current_component = (self.current_component + 1) % self.num_components
        self.show_component()

    def set_animation_speed(self, speed):
        self.speed_value_label.setText(f"{speed} ms")
        if self.animation_timer.isActive():
            self.animation_timer.setInterval(speed)

    def plot_mnf_eigenvalues(self):
        logger.info("Plot MNF Eigen Values Clicked")
        if hasattr(self, 'eigenvalues') and self.eigenvalues is not None:
            plt.figure(figsize=(20,8))
            plt.plot(range(1, len(self.eigenvalues)+1), self.eigenvalues)
            plt.xlabel("MNF Component")
            plt.ylabel("Eigenvalue / Variance")
            plt.title("MNF Component Eigenvalues")
            # plt.xticks(1,np.max(self.eigenvalues), 1)
            plt.yticks(np.arange(1, int(np.max(self.eigenvalues)) + 1))
            plt.grid(True)
            plt.show()
        else:
            QMessageBox.warning(self, "Warning", "Eigenvalues not available.")

    def closeEvent(self, event):
        self.animation_timer.stop()
        plt.close(self.figure)
        super().closeEvent(event)




class MNFProcessor:
    def __init__(self, data):
        if not isinstance(data, np.ndarray) or data.ndim != 3:
             raise ValueError("Data must be a 3D numpy array (height, width, bands)")
        self.data = data
        self.mnf_components = None
        self.eigenvalues = None
        self.noise_stats = None
        self.eigenvectors = None
        self.mnf_viewer_window = None
    @staticmethod
    def estimate_noise_cov(cube: np.ndarray) -> np.ndarray:
        print("code updated")
        """Noise covariance via first differences along rows."""
        diff = cube[1:, :, :].astype(np.float64) - cube[:-1, :, :].astype(np.float64)
        Xn = diff.reshape(-1, diff.shape[-1])
        Xn = Xn[~np.isnan(Xn).any(axis=1)]
        if Xn.size == 0:
            raise ValueError("Noise estimation failed (NaNs everywhere after diff).")
        Xn = Xn - Xn.mean(axis=0, keepdims=True)
        Cn = (Xn.T @ Xn) / max(1, Xn.shape[0] - 1)
        return Cn


    def apply_mnf(self):
        print(f"From MNF calculator {self.data.shape}")

        print(f"Zero {np.sum(self.data ==0)}")
        print(f"Nan {np.sum(np.isnan(self.data))}")
        print(f"Negative {np.sum(self.data < 0)}")

        print(f"Infinite values in data: {np.isinf(self.data).any()}")
        print(f"Data range: {self.data.min()} to {self.data.max()}")

        height, width, bands = self.data.shape
        data_2d = self.data.reshape(-1, bands)
        X = np.nan_to_num(data_2d, nan=0.0)
        Cn = self.estimate_noise_cov(self.data)
        mu = X.mean(axis=0, keepdims=True)
        Xc = X - mu
        N = Xc.shape[0]
        Cd = (Xc.T @ Xc) / max(1, N - 1)

        ew, Ev = np.linalg.eigh(Cn)
        eps = 1e-8
        ew = np.clip(ew, eps, None)
        Cn_inv_sqrt = Ev @ np.diag(1.0/np.sqrt(ew)) @ Ev.T

        A = Cn_inv_sqrt @ Cd @ Cn_inv_sqrt.T
        lam, E = np.linalg.eigh(A)
        idx = np.argsort(lam)[::-1]
        self.eigen_values = lam[idx]
        E = E[:, idx]

        P = Cn_inv_sqrt.T @ E  # (bands, bands)
        Y = Xc @ P
        self.mnf_components = Y.reshape(height, width, bands)
        print(f"mnf_component shape:  {self.mnf_components.shape}")

        return self.mnf_components, self.eigen_values


        # height, width, bands = self.data.shape
        # data_2d = self.data.reshape(-1, bands)
        # logger.info(f"Data reshaped to 2D: {data_2d.shape}")


        # self.noise_stats = self.estimate_noise_cov(self.data)

        # signal_cov = np.cov(data_2d, rowvar=False)

        # logger.info("Signal covariance matrix computed.")

        # C = self.noise_stats.sqrt_inv_cov.dot(signal_cov).dot(self.noise_stats.sqrt_inv_cov)
        # logger.info("MNF transformation matrix computed.")
        # eigenvalues, eigenvectors = np.linalg.eig(C)
        # logger.info("Eigen decomposition completed.")
        # idx = np.argsort(eigenvalues)[::-1]
        # self.eigenvalues = eigenvalues[idx]
        # self.eigenvectors = eigenvectors[:, idx]

        # mnf_components_2d = data_2d.dot(self.noise_stats.sqrt_inv_cov).dot(self.eigenvectors)
        # self.mnf_components = mnf_components_2d.reshape(height, width, bands)

        # return self.mnf_components, self.eigenvalues

    def display_interactive_mnf(self, parent_viewer=None):
        if self.mnf_components is None:
            self.apply_mnf()

        if self.mnf_viewer_window and self.mnf_viewer_window.isVisible():
            self.mnf_viewer_window.activateWindow()
            return
        print(f"MNF component from display_interactive_mnf function: {self.mnf_components.shape}")
        self.mnf_viewer_window = MNFViewerWindow(self.mnf_components, self.eigen_values, parent_viewer )
        self.mnf_viewer_window.show()


    def inverse_mnf(self, selected_components):
        if self.mnf_components is None:
            raise ValueError("Run apply_mnf() first.")
        
        # This is the forward transform matrix
        forward_transform = self.noise_stats.sqrt_inv_cov.dot(self.eigenvectors)
        
        # The inverse transform is the pseudoinverse of the forward transform
        inverse_transform = np.linalg.pinv(forward_transform)
        
        # Get the 2D MNF data
        mnf_2d = self.mnf_components.reshape(-1, self.data.shape[2])
        
        # Create a copy and zero out the components we don't want to keep
        denoised_mnf_2d = np.zeros_like(mnf_2d)
        denoised_mnf_2d[:, selected_components] = mnf_2d[:, selected_components]

        # Apply the inverse transform
        reconstructed_2d = denoised_mnf_2d.dot(inverse_transform)
        
        return reconstructed_2d.reshape(self.data.shape)