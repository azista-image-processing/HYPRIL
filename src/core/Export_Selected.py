#src/core/Export_Selected.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                               QLineEdit, QPushButton, QComboBox, QGroupBox, 
                               QRadioButton, QListWidget, QDialogButtonBox, 
                               QLabel, QCheckBox, QSpinBox)
# from datetime import datetime

class TiffExportDialog(QDialog):
    """Simplified export dialog for GeoTIFF format"""
    
    def __init__(self, layer, parent=None):
        super().__init__(parent)
        self.layer = layer
        self.setWindowTitle(f"Export to GeoTIFF: {layer['name']}")
        self.setMinimumSize(450, 500)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # File selection
        file_group = QGroupBox("Output File")
        file_layout = QVBoxLayout(file_group)
        
        file_path_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select output file path...")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_file)
        
        file_path_layout.addWidget(self.file_path_edit)
        file_path_layout.addWidget(browse_btn)
        file_layout.addLayout(file_path_layout)
        layout.addWidget(file_group)
        
        # Export options
        options_group = QGroupBox("Export Options")
        options_layout = QFormLayout(options_group)
        
        # Extent
        self.extent_combo = QComboBox()
        self.extent_combo.addItems(['Full extent', 'Current view'])
        options_layout.addRow("Extent:", self.extent_combo)
        
        # Data type
        self.data_type_combo = QComboBox()
        self.data_type_combo.addItems(['Float32', 'Float64', 'UInt16', 'Int16', 'UInt32', 'Int32'])
        self.data_type_combo.setCurrentText('Float32')
        options_layout.addRow("Data Type:", self.data_type_combo)
        
        # Compression
        self.compression_combo = QComboBox()
        self.compression_combo.addItems(['None', 'LZW', 'DEFLATE'])
        self.compression_combo.setCurrentText('LZW')
        options_layout.addRow("Compression:", self.compression_combo)
        
        layout.addWidget(options_group)
        
        # Band selection
        band_group = QGroupBox("Band Selection")
        band_layout = QVBoxLayout(band_group)
        
        self.all_bands_radio = QRadioButton("Export all bands")
        self.all_bands_radio.setChecked(True)
        self.selected_bands_radio = QRadioButton("Export selected bands:")
        
        self.band_list = QListWidget()
        self.band_list.setSelectionMode(QListWidget.MultiSelection)
        self.band_list.setEnabled(False)
        
        # Populate band list
        band_names = self.layer.get('band_names', [])
        wavelengths = self.layer.get('wavelengths', [])
        
        for i in range(len(band_names)):
            if i < len(wavelengths):
                item_text = f"Band {i+1}: {band_names[i]} ({wavelengths[i]:.2f} nm)"
            else:
                item_text = f"Band {i+1}: {band_names[i]}"
            self.band_list.addItem(item_text)
        
        # Connect radio button events
        self.selected_bands_radio.toggled.connect(self.band_list.setEnabled)
        
        band_layout.addWidget(self.all_bands_radio)
        band_layout.addWidget(self.selected_bands_radio)
        band_layout.addWidget(self.band_list)
        
        layout.addWidget(band_group)
        
        # Info section
        info_group = QGroupBox("Export Information")
        info_layout = QFormLayout(info_group)
        
        # # Show layer info
        shape = self.layer['data'].shape

        dimensions_label = QLabel(f"{shape[0]} × {shape[1]} × {shape[2]}")
        info_layout.addRow("Dimensions:", dimensions_label)

        georef_label = QLabel("Yes" if self.layer.get('geotransform') else "No")
        info_layout.addRow("Georeferenced:", georef_label)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Set default filename
        default_name = f"{self.layer['name']}_export.tif"
        self.file_path_edit.setText(default_name)
        
    def browse_file(self):
        from PySide6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Export GeoTIFF", 
            f"{self.layer['name']}_export.tif",
            "GeoTIFF Files (*.tif *.tiff);;All Files (*.*)"
        )
        
        if file_path:
            self.file_path_edit.setText(file_path)
    
    def get_export_options(self):
        """Get all export options from the dialog"""
        selected_bands = 'all'
        
        if self.selected_bands_radio.isChecked():
            selected_items = self.band_list.selectedItems()
            if selected_items:
                selected_bands = [self.band_list.row(item) for item in selected_items]
            else:
                # If no bands selected but radio is checked, use all bands
                selected_bands = 'all'
        
        extent = 'full' if self.extent_combo.currentText() == 'Full extent' else 'current_view'
        
        return {
            'file_path': self.file_path_edit.text(),
            'extent': extent,
            'data_type': self.data_type_combo.currentText(),
            'compression': self.compression_combo.currentText(),
            'selected_bands': selected_bands
        }
