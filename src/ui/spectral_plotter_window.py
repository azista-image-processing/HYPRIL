# src/ui/spectral_plotter_window.py
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout

class SpectralPlotterWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Spectral Plotter")
        self.setGeometry(200, 200, 500, 400)
        
        layout = QVBoxLayout()
        label = QLabel("This window will plot spectral signatures.\nClick on a pixel in the viewer to see its graph here.")
        layout.addWidget(label)
        self.setLayout(layout)