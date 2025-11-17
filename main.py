# main.py
import sys
import numexpr as ne
ne.set_num_threads(32)   # or any number ≤ cores


from PySide6.QtWidgets import QApplication
from src.ui.Image_Viewer_Window import ImageViewerWindow

if __name__ == '__main__':
    app = QApplication.instance() or QApplication(sys.argv)
    window = ImageViewerWindow()
    window.show()
    sys.exit(app.exec())