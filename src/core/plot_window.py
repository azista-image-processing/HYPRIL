
# from PySide6.QtWidgets import (
#     QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QGroupBox,
#     QLabel, QProgressBar, QSpinBox, QTabWidget, QWidget, QCheckBox,
#     QApplication, QMessageBox, QMainWindow, QDockWidget, QToolBar,QDoubleSpinBox
# )
# from matplotlib.figure import Figure
# from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
# from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
# from vispy import scene, app, color
# import numpy as np

# class PlotWindow_2D(QMainWindow):
#     def __init__(self, title: str, parent=None):
#         super().__init__(parent)
#         self.setWindowTitle(title)
#         self.setMinimumSize(1000, 800)
#         self.central_widget = QWidget()
#         self.setCentralWidget(self.central_widget)
#         self.layout = QVBoxLayout(self.central_widget)
#         self.figure = Figure(figsize=(6, 5))
#         self.canvas = FigureCanvas(self.figure)
#         self.toolbar = NavigationToolbar(self.canvas, self)
#         self.layout.addWidget(self.toolbar)
#         self.layout.addWidget(self.canvas)
#     def update_plot(self, update_func):
#         self.figure.clear()
#         ax = update_func(self.figure)
#         self.canvas.draw()


# class PlotWindow(QMainWindow):
#     def __init__(self, title="VisPy Plot", parent=None):
#         super().__init__(parent)
#         self.setWindowTitle(title)
#         self.setMinimumSize(1000, 800)

#         self.central_widget = QWidget()
#         self.setCentralWidget(self.central_widget)
#         self.layout = QVBoxLayout(self.central_widget)

#         # VisPy canvas and 3D viewport
#         self.canvas = scene.SceneCanvas(keys='interactive', bgcolor='black', size=(1000, 700))
#         self.view = self.canvas.central_widget.add_view()
#         self.view.camera = scene.cameras.TurntableCamera(fov=45, distance=5)
#         self.view.camera.up = '+z'

#         self.axis = scene.visuals.XYZAxis(parent=self.view.scene)

#         self.layout.addWidget(self.canvas.native)

#         # Auto Rotate button
#         self.rotate_button = QPushButton("Auto Rotate", self)
#         self.layout.addWidget(self.rotate_button)
#         self.rotate_button.clicked.connect(self.toggle_rotation)

#         self.timer = app.Timer('auto', connect=self.rotate, start=False)
#         self.rotating = False
#         self.angle = 0

#     def toggle_rotation(self):
#         if not self.rotating:
#             self.timer.start()
#             self.rotate_button.setText("Stop Rotate")
#         else:
#             self.timer.stop()
#             self.rotate_button.setText("Auto Rotate")
#         self.rotating = not self.rotating

#     def rotate(self, event):
#         self.angle = (self.angle + 1) % 360
#         self.view.camera.azimuth = self.angle
#         self.canvas.update()

#     def plot_points(self, points, values=None, size=5):
#         """
#         points: ndarray (N, 3)
#         values: 1D array for colormap, optional
#         """
#         points = points.astype(np.float32)
#         # self.view.clear()
#         for child in list(self.view.scene.children):
#             if child is not self.axis:
#                 child.parent = None
#         scatter = scene.visuals.Markers()
#         if values is not None:
#             # Normalize values and map to 'jet' colormap
#             norm_vals = (values - values.min()) / (values.max() - values.min())
#             colors = color.get_colormap('jet').map(norm_vals)
#         else:
#             colors = (1, 1, 1, 1)  # white default

#         scatter.set_data(points, edge_color=None, face_color=colors, size=size)
#         self.view.add(scatter)

#     def plot_image(self, image):
#         """
#         image: 2D ndarray
#         """
#         # Remove all visuals except the axis
#         for visual in list(self.view.scene.children):
#             if visual is not self.axis:
#                 visual.parent = None  # Correct way to remove from scene
#         image_visual = scene.visuals.Image(image, parent=self.view.scene)
#         # Instead of replacing the camera, configure the existing one:
#         if not isinstance(self.view.camera, scene.cameras.PanZoomCamera):
#             self.view.camera = scene.cameras.PanZoomCamera(aspect=1)
#         self.view.camera.set_range()
#         self.canvas.update()


#     def closeEvent(self, event):
#         """Clean up the canvas on close."""
#         self.figure.clear()
#         self.canvas.closeEvent()
#         self.canvas.deleteLater()
#         super().closeEvent(event)



# from PySide6.QtWidgets import (
#     QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QGroupBox,
#     QLabel, QProgressBar, QSpinBox, QTabWidget, QWidget, QCheckBox,
#     QApplication, QMessageBox, QMainWindow, QDockWidget, QToolBar, QDoubleSpinBox,
#     QSlider, QFormLayout
# )
# from matplotlib.figure import Figure
# from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
# from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
# from vispy import scene, app, color
# import numpy as np
# from PySide6.QtCore import Qt
# from vispy.visuals import LineVisual, MeshVisual
# from vispy.color import ColorArray
# from vispy.geometry import create_sphere

# class PlotWindow(QMainWindow):
#     def __init__(self, title="Advanced VisPy Plot", parent=None):
#         super().__init__(parent)
#         self.setWindowTitle(title)
#         self.setMinimumSize(1200, 900)

#         # Initialize central widget and layout
#         self.central_widget = QWidget()
#         self.setCentralWidget(self.central_widget)
#         self.main_layout = QVBoxLayout(self.central_widget)

#         # VisPy canvas and view
#         self.canvas = scene.SceneCanvas(keys='interactive', bgcolor='black', size=(1000, 700))
#         self.view = self.canvas.central_widget.add_view()
#         self.view.camera = scene.cameras.TurntableCamera(fov=45, distance=5, up='+z')
        
#         # Add coordinate axis
#         self.axis = scene.visuals.XYZAxis(parent=self.view.scene)
#         self.main_layout.addWidget(self.canvas.native)

#         # Data storage for multiple layers
#         self.visuals = []
#         self.animations = []
        
#         # Setup control panel
#         self.setup_control_panel()

#         # Animation timer
#         self.timer = app.Timer('auto', connect=self.update_animations, start=False)
#         self.is_animating = False
#         self.animation_speed = 1.0

#     def setup_control_panel(self):
#         """Create a dockable control panel with visualization options"""
#         self.dock = QDockWidget("Control Panel", self)
#         self.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        
#         control_widget = QWidget()
#         self.dock.setWidget(control_widget)
#         control_layout = QVBoxLayout(control_widget)
        
#         # Tabs for different controls
#         tabs = QTabWidget()
#         control_layout.addWidget(tabs)
        
#         # Visualization settings tab
#         vis_widget = QWidget()
#         vis_layout = QFormLayout(vis_widget)
        
#         # Visualization type selection
#         self.vis_type = QComboBox()
#         self.vis_type.addItems(['Points', 'Lines', 'Surface', 'Image'])
#         vis_layout.addRow("Visualization Type:", self.vis_type)
        
#         # Point size slider
#         self.size_slider = QSlider(Qt.Horizontal)
#         self.size_slider.setRange(1, 20)
#         self.size_slider.setValue(5)
#         vis_layout.addRow("Point/Line Size:", self.size_slider)
        
#         # Colormap selection
#         self.colormap = QComboBox()
#         self.colormap.addItems(['jet', 'viridis', 'hot', 'cool', 'spring'])
#         vis_layout.addRow("Colormap:", self.colormap)
        
#         # Opacity slider
#         self.opacity = QDoubleSpinBox()
#         self.opacity.setRange(0.0, 1.0)
#         self.opacity.setSingleStep(0.1)
#         self.opacity.setValue(1.0)
#         vis_layout.addRow("Opacity:", self.opacity)
        
#         tabs.addTab(vis_widget, "Visualization")
        
#         # Camera settings tab
#         cam_widget = QWidget()
#         cam_layout = QFormLayout(cam_widget)
        
#         # Camera type selection
#         self.camera_type = QComboBox()
#         self.camera_type.addItems(['Turntable', 'PanZoom', 'Arcball'])
#         cam_layout.addRow("Camera Type:", self.camera_type)
#         self.camera_type.currentTextChanged.connect(self.change_camera)
        
#         # Auto rotate checkbox
#         self.rotate_check = QCheckBox("Auto Rotate")
#         cam_layout.addRow(self.rotate_check)
#         self.rotate_check.stateChanged.connect(self.toggle_rotation)
        
#         tabs.addTab(cam_widget, "Camera")
        
#         # Animation controls
#         anim_widget = QWidget()
#         anim_layout = QFormLayout(anim_widget)
        
#         self.anim_speed = QDoubleSpinBox()
#         self.anim_speed.setRange(0.1, 5.0)
#         self.anim_speed.setSingleStep(0.1)
#         self.anim_speed.setValue(1.0)
#         anim_layout.addRow("Animation Speed:", self.anim_speed)
        
#         tabs.addTab(anim_widget, "Animation")
        
#         # Apply button
#         apply_btn = QPushButton("Apply Settings")
#         apply_btn.clicked.connect(self.apply_settings)
#         control_layout.addWidget(apply_btn)

#     def change_camera(self, camera_type):
#         """Change camera type"""
#         camera_map = {
#             'Turntable': scene.cameras.TurntableCamera(fov=45, distance=5, up='+z'),
#             'PanZoom': scene.cameras.PanZoomCamera(aspect=1),
#             'Arcball': scene.cameras.ArcballCamera(fov=45, distance=5)
#         }
#         self.view.camera = camera_map[camera_type]
#         self.view.camera.set_range()

#     def toggle_rotation(self, state):
#         """Toggle auto rotation"""
#         if state:
#             self.timer.start()
#             self.is_animating = True
#         else:
#             self.timer.stop()
#             self.is_animating = False

#     def update_animations(self, event):
#         """Update all animated visuals"""
#         for visual, anim_func in self.animations:
#             anim_func(visual)
#         self.canvas.update()

#     def plot_data(self, data, values=None, vis_type='Points'):
#         """
#         Plot different types of data
#         data: ndarray (N, 3) for 3D, (N, 2) for 2D
#         values: 1D array for colormap
#         vis_type: 'Points', 'Lines', 'Surface', or 'Image'
#         """
#         # Clear existing visuals except axis
#         for visual in self.visuals:
#             visual.parent = None
#         self.visuals.clear()

#         data = data.astype(np.float32)
#         colormap = color.get_colormap(self.colormap.currentText())
        
#         if values is not None:
#             norm_vals = (values - values.min()) / (values.max() - values.min())
#             colors = colormap.map(norm_vals)
#         else:
#             colors = ColorArray('white')

#         size = self.size_slider.value()
#         opacity = self.opacity.value()

#         if vis_type == 'Points':
#             visual = scene.visuals.Markers()
#             visual.set_data(data, edge_color=None, face_color=colors, size=size)
        
#         elif vis_type == 'Lines':
#             visual = LineVisual(data, color=colors, width=size)
        
#         elif vis_type == 'Surface':
#             if data.shape[1] == 3:
#                 meshdata = create_sphere(20, 20)
#                 visual = MeshVisual(meshdata=meshdata, color=colors)
#             else:
#                 raise ValueError("Surface plots require 3D data")
        
#         elif vis_type == 'Image':
#             if len(data.shape) == 2:
#                 visual = scene.visuals.Image(data, cmap=colormap)
#                 if not isinstance(self.view.camera, scene.cameras.PanZoomCamera):
#                     self.view.camera = scene.cameras.PanZoomCamera(aspect=1)
#             else:
#                 raise ValueError("Image plots require 2D data")
        
#         visual.opacity = opacity
#         self.view.add(visual)
#         self.visuals.append(visual)
#         self.view.camera.set_range()
#         self.canvas.update()

#     def add_animation(self, visual, animation_func):
#         """Add animation function for a visual"""
#         self.animations.append((visual, animation_func))
#         if not self.is_animating and self.rotate_check.isChecked():
#             self.timer.start()

#     def apply_settings(self):
#         """Apply current settings to all visuals"""
#         for visual in self.visuals:
#             visual.opacity = self.opacity.value()
#             if hasattr(visual, 'size'):
#                 visual.size = self.size_slider.value()
#         self.animation_speed = self.anim_speed.value()
#         self.canvas.update()

#     def closeEvent(self, event):
#         """Clean up on close"""
#         self.timer.stop()
#         for visual in self.visuals:
#             visual.parent = None
#         self.canvas.close()
#         self.canvas.deleteLater()
#         super().closeEvent(event)




import os
os.environ['VISPY_BACKEND'] = 'pyqt6'  # PySide6 enforcement

from PySide6.QtWidgets import ( QVBoxLayout,  QComboBox, QPushButton,
 QTabWidget, QWidget, QCheckBox,
    QMainWindow, QDockWidget, QDoubleSpinBox,
    QSlider, QFormLayout
)
from PySide6.QtCore import Qt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from vispy import scene, app, color
from vispy.visuals import LineVisual  # For skewers as lines
import numpy as np
from vispy.color import ColorArray

# Uncommented and fixed PlotWindow_2D for Matplotlib-based histogram (ENVI-like stats)
class PlotWindow_2D(QMainWindow):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(1000, 800)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.figure = Figure(figsize=(6, 5))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)

    def update_plot(self, update_func):
        self.figure.clear()
        ax = update_func(self.figure)
        self.canvas.draw()

# Enhanced PlotWindow (replaces old version)
class PlotWindow(QMainWindow):
    def __init__(self, title="Advanced VisPy Plot", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(1200, 900)

        # Initialize central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # VisPy canvas and view (GPU-ready)
        self.canvas = scene.SceneCanvas(keys='interactive', bgcolor='black', size=(1000, 700))
        self.view = self.canvas.central_widget.add_view()
        self.view.camera = scene.cameras.TurntableCamera(fov=45, distance=5, up='+z')
        
        # Add coordinate axis
        self.axis = scene.visuals.XYZAxis(parent=self.view.scene)
        self.main_layout.addWidget(self.canvas.native)

        # Data storage for multi-layer ENVI-like overlays (e.g., PPI points + skewers)
        self.visuals = []
        self.animations = []
        
        # Setup control panel (dockable, tabbed for advanced controls)
        self.setup_control_panel()

        # GL state setup (post-canvas, PySide6-safe)
        self.setup_gl_state()

        # Animation timer (fixed: use 'auto' if supported, fallback to seconds)
        try:
            self.timer = app.Timer('auto', connect=self.update_animations, start=False)
        except TypeError:
            self.timer = app.Timer(interval=0.016, connect=self.update_animations, start=False)  # ~60 FPS fallback
        self.is_animating = False
        self.animation_speed = 1.0

    def setup_gl_state(self):
        """GPU GL state for blending/depth in PySide6."""
        try:
            self.canvas.context.set_state(
                depth_test=True, blend=True, blend_func=('src_alpha', 'one_minus_src_alpha')
            )
            self.canvas.context.clear_color = (0, 0, 0, 1)
            self.canvas.update()
            print("GL state set for GPU rendering.")
        except Exception as e:
            print(f"GL warning: {e}")

    def setup_control_panel(self):
        """Dockable control panel with ENVI-like tabs."""
        self.dock = QDockWidget("Control Panel", self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        
        control_widget = QWidget()
        self.dock.setWidget(control_widget)
        control_layout = QVBoxLayout(control_widget)
        
        # Tabs for controls
        tabs = QTabWidget()
        control_layout.addWidget(tabs)
        
        # Visualization tab
        vis_widget = QWidget()
        vis_layout = QFormLayout(vis_widget)
        
        self.vis_type = QComboBox()
        self.vis_type.addItems(['Points', 'Lines', 'Surface', 'Image'])
        vis_layout.addRow("Visualization Type:", self.vis_type)
        
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(1, 20)
        self.size_slider.setValue(5)
        vis_layout.addRow("Size:", self.size_slider)
        
        self.colormap = QComboBox()
        self.colormap.addItems(['jet', 'viridis', 'hot', 'cool', 'spring'])
        vis_layout.addRow("Colormap:", self.colormap)
        
        self.opacity = QDoubleSpinBox()
        self.opacity.setRange(0.0, 1.0)
        self.opacity.setSingleStep(0.1)
        self.opacity.setValue(1.0)
        vis_layout.addRow("Opacity:", self.opacity)
        
        tabs.addTab(vis_widget, "Visualization")
        
        # Camera tab
        cam_widget = QWidget()
        cam_layout = QFormLayout(cam_widget)
        
        self.camera_type = QComboBox()
        self.camera_type.addItems(['Turntable', 'PanZoom', 'Arcball'])
        cam_layout.addRow("Camera Type:", self.camera_type)
        self.camera_type.currentTextChanged.connect(self.change_camera)
        
        self.rotate_check = QCheckBox("Auto Rotate")
        cam_layout.addRow(self.rotate_check)
        self.rotate_check.stateChanged.connect(self.toggle_rotation)
        
        tabs.addTab(cam_widget, "Camera")
        
        # Animation tab
        anim_widget = QWidget()
        anim_layout = QFormLayout(anim_widget)
        
        self.anim_speed = QDoubleSpinBox()
        self.anim_speed.setRange(0.1, 5.0)
        self.anim_speed.setSingleStep(0.1)
        self.anim_speed.setValue(1.0)
        anim_layout.addRow("Speed:", self.anim_speed)
        
        tabs.addTab(anim_widget, "Animation")
        
        # Apply button
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.apply_settings)
        control_layout.addWidget(apply_btn)

    def change_camera(self, camera_type):
        """Switch cameras (ENVI-like view modes)."""
        camera_map = {
            'Turntable': scene.cameras.TurntableCamera(fov=45, distance=5, up='+z'),
            'PanZoom': scene.cameras.PanZoomCamera(aspect=1),
            'Arcball': scene.cameras.ArcballCamera(fov=45, distance=5)
        }
        self.view.camera = camera_map.get(camera_type, self.view.camera)
        self.view.camera.set_range()
        self.canvas.update()

    def toggle_rotation(self, state):
        """Toggle orbit rotation (ENVI n-D style)."""
        self.is_animating = bool(state)
        if self.is_animating:
            self.timer.start()
        else:
            self.timer.stop()

    def update_animations(self, event):
        """Update animations (e.g., rotation + pulsing)."""
        import time
        for visual, anim_func in self.animations:
            anim_func(visual, time.time() * self.animation_speed)
        self.canvas.update()

    def plot_data(self, data, values=None, vis_type='Points', layer_name="Layer"):
        """
        Unified plot for ENVI-like visuals: Points (n-D PPI), Image (PPI map), Lines (skewers).
        data: ndarray (N,3) for 3D/2D, or 2D (H,W) for Image.
        values: 1D for colormap (e.g., PPI scores).
        """
        # Clear visuals except axis (supports overlays)
        for visual in self.visuals[:]:  # Copy to avoid modification during iteration
            if visual.name != layer_name:  # Preserve layers
                visual.parent = None
                self.visuals.remove(visual)

        data = data.astype(np.float32)
        colormap = color.get_colormap(self.colormap.currentText())
        
        if values is not None:
            norm_vals = np.clip((values - values.min()) / (values.max() - values.min() + 1e-8), 0, 1)
            colors = colormap.map(norm_vals)
        else:
            colors = ColorArray('white').rgba

        size = self.size_slider.value()
        opacity = self.opacity.value()

        if vis_type == 'Points':  # n-D scatter (PPI projections)
            visual = scene.visuals.Markers()
            visual.set_data(pos=data, edge_color=None, face_color=colors, size=size)
            if len(data) > 0:
                self.view.camera.set_range()

        elif vis_type == 'Image':  # PPI score map as colormapped 2D image
            if len(data.shape) == 2:
                visual = scene.visuals.Image(data, cmap=colormap, parent=self.view.scene)
                self.view.camera = scene.cameras.PanZoomCamera(aspect=1, parent=self.view.scene)
                self.view.camera.set_range()
            else:
                raise ValueError("Image requires 2D data (e.g., PPI scores HxW)")

        elif vis_type == 'Lines':  # Skewers as 3D lines
            if data.shape[1] >= 2:
                visual = LineVisual(pos=data, color=colors, width=float(size), method='gl')
            else:
                raise ValueError("Lines require (N,2+) data")

        elif vis_type == 'Surface':  # Optional volume (not used here)
            raise NotImplementedError("Surface for future volume rendering")

        visual.opacity = opacity
        visual.name = layer_name
        self.view.add(visual)
        self.visuals.append(visual)
        self.canvas.update()

    def add_layer(self, data, values=None, vis_type='Points', layer_name="Overlay"):
        """Add ENVI-like overlay (e.g., skewers on PPI points)."""
        self.plot_data(data, values, vis_type, layer_name)  # Appends without full clear

    def add_animation(self, visual, animation_func):
        """Add animation (e.g., orbit or pulse for n-D)."""
        self.animations.append((visual, animation_func))
        if self.is_animating:
            self.timer.start()

    def apply_settings(self):
        """Update visuals with controls (live ENVI-like tweaks)."""
        for visual in self.visuals:
            visual.opacity = self.opacity.value()
            if hasattr(visual, 'set_data'):  # For Markers/Lines
                # Re-apply size/colormap (simplified)
                pass  # Extend if needed for dynamic updates
        self.animation_speed = self.anim_speed.value()
        self.canvas.update()

    def closeEvent(self, event):
        """Cleanup."""
        self.timer.stop()
        for visual in self.visuals:
            visual.parent = None
        for _, func in self.animations:
            pass  # No-op for funcs
        self.canvas.close()
        self.canvas.deleteLater()
        super().closeEvent(event)
