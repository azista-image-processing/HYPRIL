# correct usage in a script
from PySide6.QtWidgets import QApplication
import sys
from src.ui.ppi_workflow_window import PPI_Workflow_Window
import numpy as np
app = QApplication.instance() or QApplication(sys.argv)
h,w,b = 80,80,10
mock = np.random.rand(h,w,b)
layers = [{'name':'sample','data':mock,'band_names':np.arange(b)}]
window = PPI_Workflow_Window(layers=layers)
window.show()
sys.exit(app.exec())
