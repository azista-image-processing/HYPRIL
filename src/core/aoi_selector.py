# src/core/aoi_selector.py
from PySide6.QtCore import QObject, Signal
from matplotlib.widgets import RectangleSelector

class AOISelector(QObject):
    finished = Signal(tuple)  # (x1, y1, x2, y2) in pixel coords

    def __init__(self, ax, canvas, parent=None):
        super().__init__(parent)
        self.ax = ax
        self.canvas = canvas
        self.selector = None
        self._active = False

    def start(self):
        if self._active:
            return
        self._active = True
        # Use RectangleSelector; draw from click-drag; finalize on release
        self.selector = RectangleSelector(
            self.ax,
            onselect=self._on_select,
            useblit=True,
            interactive=False,
            button=[1],          # left mouse
            minspanx=2, minspany=2,
            spancoords='data',
            props=dict(edgecolor='yellow', facecolor='none', linewidth=1.5)
        )
        self.canvas.draw_idle()

    def _on_select(self, eclick, erelease):
        # Convert to integer pixel box
        x1, y1 = eclick.xdata, eclick.ydata
        x2, y2 = erelease.xdata, erelease.ydata
        if x1 is None or y1 is None or x2 is None or y2 is None:
            self.stop()
            return
        xi1, xi2 = sorted([int(round(x1)), int(round(x2))])
        yi1, yi2 = sorted([int(round(y1)), int(round(y2))])
        self.finished.emit((xi1, yi1, xi2, yi2))
        self.stop()

    def stop(self):
        if self.selector:
            self.selector.set_visible(False)
            self.selector.disconnect_events()
            self.selector = None
        self.canvas.draw_idle()
        self._active = False
