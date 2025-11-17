#src/ui/raster_calculator.py
import re
import os
import ast
import numpy as np
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, QGridLayout,
    QApplication, QMessageBox, QLabel, QDialogButtonBox, QComboBox, QPushButton,
    QTabWidget, QWidget, QGroupBox, QTextEdit, QTableWidget, QTableWidgetItem, 
    QProgressBar, QCheckBox, QFileDialog, QListWidgetItem
)
from PySide6.QtCore import Signal, Qt, QThread, Signal
from PySide6.QtGui import QFont

PRESET_WAVELENGTHS = {
    'NDVI': {'Red': 650, 'NIR': 840},
    'NDWI': {'Green': 550, 'NIR': 840},
    'EVI': {'Blue': 450, 'Red': 650, 'NIR': 840},
    'Band Ratio': {},  # user selects manually
    'Band Difference': {},
    'Normalized Difference': {}
}

class BandSelectionDialog(QDialog):
    """Dialog for selecting bands for preset calculations"""
    
    def __init__(self, preset_name, all_layers, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Select Bands for {preset_name}")
        self.setMinimumSize(500, 400)
        self.preset_name = preset_name
        self.all_layers = all_layers
        self.selected_bands = {}
        self.selected_layer = ""
        
        self._setup_ui()
        self._connect_signals()
        self._update_band_combos()
        self._update_preview()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Instructions
        instruction_text = self._get_instruction_text()
        instruction_label = QLabel(instruction_text)
        instruction_label.setWordWrap(True)
        instruction_label.setStyleSheet("background-color: #e8f4fd; padding: 10px; border-radius: 5px;")
        layout.addWidget(instruction_label)
        
        # Layer selection
        layer_group = QGroupBox("Select Layer")
        layer_layout = QVBoxLayout(layer_group)
        
        self.layer_combo = QComboBox()
        self.layer_combo.addItems([layer['name'] for layer in self.all_layers])
        layer_layout.addWidget(QLabel("Choose the layer to use:"))
        layer_layout.addWidget(self.layer_combo)
        layout.addWidget(layer_group)
        
        # Band selection based on preset type
        bands_group = QGroupBox("Select Required Bands")
        bands_layout = QVBoxLayout(bands_group)
        
        self.band_selections = {}
        required_bands = self._get_required_bands()
        
        for band_key, description in required_bands.items():
            band_layout = QHBoxLayout()
            
            # Create label with fixed width for alignment
            label = QLabel(f"{band_key}:")
            label.setMinimumWidth(80)
            label.setStyleSheet("font-weight: bold;")
            band_layout.addWidget(label)
            
            desc_label = QLabel(description)
            desc_label.setStyleSheet("color: #666;")
            band_layout.addWidget(desc_label)
            
            band_combo = QComboBox()
            band_combo.setMinimumWidth(150)
            self._populate_band_combo(band_combo)
            band_layout.addWidget(band_combo)
            
            bands_layout.addLayout(band_layout)
            self.band_selections[band_key] = band_combo
        
        layout.addWidget(bands_group)
        
        # Preview section
        preview_group = QGroupBox("Expression Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_label = QLabel("Select bands to see expression preview...")
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet("font-family: monospace; background-color: #f5f5f5; padding: 5px; border: 1px solid #ddd;")
        preview_layout.addWidget(self.preview_label)
        layout.addWidget(preview_group)
        
        # Dialog buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(self.button_box)
    
    def _connect_signals(self):
        self.layer_combo.currentTextChanged.connect(self._update_band_combos)
        self.layer_combo.currentTextChanged.connect(self._update_preview)
        
        # Connect all band selection combos to preview update
        for combo in self.band_selections.values():
            combo.currentTextChanged.connect(self._update_preview)
        
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)
    
    def _get_instruction_text(self):
        instructions = {
            'NDVI': 'NDVI (Normalized Difference Vegetation Index) requires Red and Near-Infrared bands.\nFormula: (NIR - Red) / (NIR + Red)',
            'NDWI': 'NDWI (Normalized Difference Water Index) requires Green and Near-Infrared bands.\nFormula: (Green - NIR) / (Green + NIR)',
            'EVI': 'EVI (Enhanced Vegetation Index) requires Blue, Red, and Near-Infrared bands.\nFormula: 2.5 * ((NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1))',
            'Band Ratio': 'Band Ratio calculation requires two bands.\nFormula: Band1 / Band2',
            'Band Difference': 'Band Difference calculation requires two bands.\nFormula: Band1 - Band2',
            'Normalized Difference': 'Normalized Difference requires two bands.\nFormula: (Band1 - Band2) / (Band1 + Band2)'
        }
        return instructions.get(self.preset_name, 'Select the required bands for this calculation.')
    
    def _get_required_bands(self):
        band_requirements = {
            'NDVI': {'Red': 'Red band (~650nm)', 'NIR': 'Near-Infrared band (~840nm)'},
            'NDWI': {'Green': 'Green band (~560nm)', 'NIR': 'Near-Infrared band (~840nm)'},
            'EVI': {'Blue': 'Blue band (~470nm)', 'Red': 'Red band (~660nm)', 'NIR': 'Near-Infrared band (~840nm)'},
            'Band Ratio': {'Band1': 'First band (numerator)', 'Band2': 'Second band (denominator)'},
            'Band Difference': {'Band1': 'First band (minuend)', 'Band2': 'Second band (subtrahend)'},
            'Normalized Difference': {'Band1': 'First band', 'Band2': 'Second band'}
        }
        return band_requirements.get(self.preset_name, {'Band1': 'First band', 'Band2': 'Second band'})
    
    # def _populate_band_combo(self, combo):
    #     if self.all_layers:
    #         current_layer = self.all_layers[0]
    #         band_names = current_layer.get("band_names", [])
    #         self.wavelengths = current_layer.get("metadata", {}).get("wavelength", [])
            
    #         # I want to store both band number and its wavelength
            




    #         combo.addItem("-- Select Band --", "")  # Add default option
    #         for i, name in enumerate(band_names):
    #             # combo.addItem(f"b{i+1}: {name}", f"b{i+1}")
    #             combo.addItem(f"b{i+1}: {name}", {"id": f"b{i+1}", "name": name})
    def _populate_band_combo(self, combo, layer=None):
        """
        Populate a single QComboBox with band items.
        Each item's data is a dict: {"id": "bX", "name": name, "wavelength": wl}
        """
        combo.clear()
        combo.addItem("-- Select Band --", None)

        if not self.all_layers:
            return

        # Use given layer or default to first one
        target_layer = layer if layer is not None else self.all_layers[0]
        print(f"target_layer: {target_layer['name']}")
        band_names = target_layer.get("band_names", [])
        wavelengths = target_layer.get("metadata", {}).get("Wavelengths", [None] * len(band_names))
        if type(wavelengths) is not list:
            wavelengths = [float(x)*1000 if float(x)<100 else float(x) for x in target_layer.get("metadata", {}).get("Wavelengths", "").replace("{","").replace("}","").split(",") if x.strip()]
        for i, name in enumerate(band_names):
            wl = wavelengths[i] if i < len(wavelengths) else None
            display = f"b{i+1}: {name}"
            if wl is not None:
                display += f" ({wl:.1f} nm)"
            data = {"id": f"b{i+1}", "name": name, "wavelength": wl}
            combo.addItem(display, data)

    def _update_band_combos(self):
        layer_name = self.layer_combo.currentText()
        if not layer_name:
            return

        # Find selected layer
        selected_layer = None
        for layer in self.all_layers:
            if layer["name"] == layer_name:
                selected_layer = layer
                break

        if not selected_layer:
            return

        # Repopulate each combo using selected layer
        for combo in self.band_selections.values():
            self._populate_band_combo(combo, layer=selected_layer)

        # Auto-select closest bands based on wavelength
        auto_bands = self._auto_select_bands(selected_layer)
        for band_key, combo in self.band_selections.items():
            if band_key in auto_bands:
                target_id = auto_bands[band_key]["id"]
                for i in range(combo.count()):
                    data = combo.itemData(i)
                    if isinstance(data, dict) and data.get("id") == target_id:
                        combo.setCurrentIndex(i)
                        break



    # def _update_band_combos(self):
    #     layer_name = self.layer_combo.currentText()
    #     if not layer_name:
    #         return
            
    #     # Find the selected layer
    #     selected_layer = None
    #     for layer in self.all_layers:
    #         if layer['name'] == layer_name:
    #             selected_layer = layer
    #             break
        
    #     if selected_layer:
    #         band_names = selected_layer.get("band_names", [])
    #         for combo in self.band_selections.values():
    #             combo.clear()
    #             combo.addItem("-- Select Band --", "")
    #             for i, name in enumerate(band_names):
    #                 combo.addItem(f"b{i+1}: {name}", f"b{i+1}")


    #         # Auto-select bands based on wavelength if possible
    #         auto_bands = self._auto_select_bands(selected_layer)
    #         for band_key, combo in self.band_selections.items():
    #             if band_key in auto_bands:
    #                 for i in range(combo.count()):
    #                     data = combo.itemData(i)
    #                     if data and data["id"] == auto_bands[band_key]["id"]:
    #                         combo.setCurrentIndex(i)
    #                         break
    
    def _update_preview(self):
        """Update expression preview"""
        try:
            layer_name = self.layer_combo.currentText()
            if not layer_name:
                self.preview_label.setText("Select a layer first...")
                print("wretertwert")
                return
            
            # Check if all bands are selected
            temp_bands = {}
            for band_key, combo in self.band_selections.items():
                band_data = combo.currentData()

                if not band_data:  # Not selected or default option
                    self.preview_label.setText("Select all required bands to see preview...")
                    return
                band_id = band_data["id"]
                band_name = band_data["name"]
                # temp_bands[band_key] = band_data
                temp_bands[band_key] = {
                    "id" :band_id,
                    "name":band_name
                }
            
            # Generate preview expression
            preview_expr = self._generate_expression_preview(layer_name, temp_bands)
            self.preview_label.setText(f"Expression: {preview_expr}")
            
        except Exception as e:
            self.preview_label.setText("Error generating preview...")
    def _generate_expression_preview(self, layer_name, bands):
        """Generate expression preview using band IDs for math and band names for readability"""
        
        expressions = {
            'NDVI': lambda: (
                f'("{layer_name}@{bands["NIR"]["id"]}" - "{layer_name}@{bands["Red"]["id"]}") / '
                f'("{layer_name}@{bands["NIR"]["id"]}" + "{layer_name}@{bands["Red"]["id"]}")'
                f'   -- NIR({bands["NIR"]["name"]}) - Red({bands["Red"]["name"]})'
            ),
            'NDWI': lambda: (
                f'("{layer_name}@{bands["Green"]["id"]}" - "{layer_name}@{bands["NIR"]["id"]}") / '
                f'("{layer_name}@{bands["Green"]["id"]}" + "{layer_name}@{bands["NIR"]["id"]}")'
                f'   -- Green({bands["Green"]["name"]}) - NIR({bands["NIR"]["name"]})'
            ),
            'EVI': lambda: (
                f'2.5 * (("{layer_name}@{bands["NIR"]["id"]}" - "{layer_name}@{bands["Red"]["id"]}") / '
                f'("{layer_name}@{bands["NIR"]["id"]}" + 6 * "{layer_name}@{bands["Red"]["id"]}" '
                f'- 7.5 * "{layer_name}@{bands["Blue"]["id"]}" + 1))'
                f'   -- NIR({bands["NIR"]["name"]}), Red({bands["Red"]["name"]}), Blue({bands["Blue"]["name"]})'
            ),
            # ... same for others
        }

        expr_func = expressions.get(self.preset_name)
        print(expr_func)
        if expr_func:
            return expr_func()
        else:
            return f'"{layer_name}@{bands.get("Band1", {"id": "b1"})["id"]}" op "{layer_name}@{bands.get("Band2", {"id": "b2"})["id"]}"'

    def _auto_select_bands(self, layer):
        """
        Automatically select bands based on wavelength for the preset.
        Returns a dict like {'Red': {...}, 'NIR': {...}}
        """
        selected = {}
        target_wavelengths = PRESET_WAVELENGTHS.get(self.preset_name, {})
        wavelengths = layer.get("metadata", {}).get("Wavelengths", [])
        band_names = layer.get("band_names", [])
        if wavelengths:
            if type(wavelengths) is not list:
                wavelengths = [float(x)*1000 if float(x)<100 else float(x) for x in layer.get("metadata", {}).get("Wavelengths", "").replace("{","").replace("}","").split(",") if x.strip()]
            for band_key, target_wl in target_wavelengths.items():
                closest_idx = None
                min_diff = float('inf')
                for i, wl in enumerate(wavelengths):
                    if wl is None:
                        continue
                    diff = abs(wl - target_wl)
                    if diff < min_diff:
                        min_diff = diff
                        closest_idx = i
                if closest_idx is not None:
                    selected[band_key] = {
                        "id": f"b{closest_idx+1}",
                        "name": band_names[closest_idx],
                        "wavelength": wavelengths[closest_idx]
                    }
            return selected
        return {}


    def _validate_and_accept(self):
        layer_name = self.layer_combo.currentText()
        if not layer_name:
            QMessageBox.warning(self, "Selection Error", "Please select a layer.")
            return
        
        # Validate all required bands are selected
        required_bands = self._get_required_bands()
        for band_key, combo in self.band_selections.items():
            band_data = combo.currentData()
            if not band_data:
                QMessageBox.warning(self, "Selection Error", f"Please select {band_key} ({required_bands[band_key]}).")
                return
            self.selected_bands[band_key] = band_data
        print(f"selected Band{self.selected_bands}")
        self.selected_layer = layer_name
        self.accept()
    def get_expression(self):
        """Generate expression based on preset and selected bands"""
        if not self.selected_layer or not self.selected_bands:
            return ""
        
        try:
            # Debug print to see what we have
            print(f"Generating expression for {self.preset_name}")
            print(f"Available bands: {list(self.selected_bands.keys())}")
            print(f"Required bands: {list(self._get_required_bands().keys())}")
            
            expressions = {
                'NDVI': lambda: f'("{self.selected_layer}@{self.selected_bands["NIR"]["id"]}" - "{self.selected_layer}@{self.selected_bands["Red"]["id"]}") / ("{self.selected_layer}@{self.selected_bands["NIR"]["id"]}" + "{self.selected_layer}@{self.selected_bands["Red"]["id"]}")',
                'NDWI': lambda: f'("{self.selected_layer}@{self.selected_bands["Green"]["id"]}" - "{self.selected_layer}@{self.selected_bands["NIR"]["id"]}") / ("{self.selected_layer}@{self.selected_bands["Green"]["id"]}" + "{self.selected_layer}@{self.selected_bands["NIR"]["id"]}")',
                'EVI': lambda: f'2.5 * (("{self.selected_layer}@{self.selected_bands["NIR"]["id"]}" - "{self.selected_layer}@{self.selected_bands["Red"]["id"]}") / ("{self.selected_layer}@{self.selected_bands["NIR"]["id"]}" + 6 * "{self.selected_layer}@{self.selected_bands["Red"]["id"]}" - 7.5 * "{self.selected_layer}@{self.selected_bands["Blue"]["id"]}" + 1))',
                'Band Ratio': lambda: f'"{self.selected_layer}@{self.selected_bands["Band1"]["id"]}" / "{self.selected_layer}@{self.selected_bands["Band2"]["id"]}"',
                'Band Difference': lambda: f'"{self.selected_layer}@{self.selected_bands["Band1"]["id"]}" - "{self.selected_layer}@{self.selected_bands["Band2"]["id"]}"',
                'Normalized Difference': lambda: f'("{self.selected_layer}@{self.selected_bands["Band1"]["id"]}" - "{self.selected_layer}@{self.selected_bands["Band2"]["id"]}") / ("{self.selected_layer}@{self.selected_bands["Band1"]["id"]}" + "{self.selected_layer}@{self.selected_bands["Band2"]["id"]}")'
            }
            
            if self.preset_name in expressions:
                print(self.preset_name)
                return expressions[self.preset_name]()
            else:
                print(f"Warning: Unknown preset name: {self.preset_name}")
                return ""
                
        except KeyError as e:
            print(f"KeyError in get_expression: {e}")
            print(f"Available keys: {list(self.selected_bands.keys())}")
            print(f"Required for {self.preset_name}: {list(self._get_required_bands().keys())}")
            
            # Return empty string instead of crashing
            return ""
        except Exception as e:
            print(f"Unexpected error in get_expression: {e}")
            return ""

class ExpressionValidator:
    """Validates mathematical expressions for raster calculations"""
    
    @staticmethod
    def validate_syntax(expression):
        """Validate Python syntax of expression"""
        try:
            # Replace band identifiers with dummy variables for syntax checking
            test_expr = re.sub(r'"[^"]+@b\d+"', 'x', expression)
            ast.parse(test_expr, mode='eval')
            return True, "Valid syntax"
        except SyntaxError as e:
            return False, f"Syntax error: {str(e)}"
    
    @staticmethod
    def validate_band_references(expression, layer_map):
        """Validate that all band references exist"""
        band_identifiers = set(re.findall(r'"([^"]+@b\d+)"', expression))
        
        for identifier in band_identifiers:
            try:
                layer_name, band_id = identifier.split('@')
                band_index = int(band_id[1:]) - 1
                
                if layer_name not in layer_map:
                    return False, f"Layer '{layer_name}' not found"
                
                layer_data = layer_map[layer_name]['data']
                if not (0 <= band_index < layer_data.shape[2]):
                    return False, f"Band index {band_index+1} is out of bounds for layer '{layer_name}'"
                    
            except (ValueError, IndexError):
                return False, f"Invalid band identifier: {identifier}"
        
        if not band_identifiers:
            return False, "No valid band identifiers found"
        
        return True, "All band references are valid"
    
    @staticmethod
    def validate_complete(expression, layer_map):
        """Complete validation of expression"""
        # Check syntax
        syntax_valid, syntax_msg = ExpressionValidator.validate_syntax(expression)
        if not syntax_valid:
            return False, syntax_msg
        
        # Check band references
        bands_valid, bands_msg = ExpressionValidator.validate_band_references(expression, layer_map)
        if not bands_valid:
            return False, bands_msg
        
        return True, "Expression is valid"

class CalculationWorker(QThread):
    calculation_finished = Signal(np.ndarray, str, str, str)  # Added save_path parameter
    calculation_error = Signal(str)
    progress_updated = Signal(int)

    def __init__(self, expression, layer_map, variable_map, output_name, parent_layer, save_path=None):
        super().__init__()
        self.expression = expression
        self.layer_map = layer_map
        self.variable_map = variable_map
        self.output_name = output_name
        self.parent_layer = parent_layer
        self.save_path = save_path

    def run(self):
        try:
            local_namespace = {'np': np}
            # Add mathematical functions
            math_functions = {
                'sin': np.sin, 'cos': np.cos, 'tan': np.tan, 'asin': np.arcsin,
                'acos': np.arccos, 'atan': np.arctan, 'sqrt': np.sqrt,
                'exp': np.exp, 'log': np.log, 'log10': np.log10, 'abs': np.abs,
                'ceil': np.ceil, 'floor': np.floor, 'round': np.round,
                'min': np.minimum, 'max': np.maximum, 'mean': np.mean,
                'median': np.median, 'std': np.std, 'var': np.var
            }
            local_namespace.update(math_functions)
            self.progress_updated.emit(20)

            for identifier, var_name in self.variable_map.items():
                layer_name, band_id = identifier.split('@')
                band_index = int(band_id[1:]) - 1
                layer_data = self.layer_map[layer_name]['data']
                local_namespace[var_name] = layer_data[:, :, band_index].astype(np.float64)

            self.progress_updated.emit(50)
            processed_expression = self.expression
            for identifier, var_name in self.variable_map.items():
                processed_expression = processed_expression.replace(f'"{identifier}"', var_name)

            self.progress_updated.emit(70)
            with np.errstate(divide='ignore', invalid='ignore'):
                result_array = eval(processed_expression, {"__builtins__": {}}, local_namespace)

            if np.isscalar(result_array):
                result_array = np.full_like(list(local_namespace.values())[0], result_array)

            result_array = np.nan_to_num(result_array, nan=0.0, posinf=0.0, neginf=0.0)
            if result_array.ndim == 2:
                result_array = result_array[:, :, np.newaxis]

            self.progress_updated.emit(100)
            self.calculation_finished.emit(result_array, self.output_name, self.parent_layer, self.save_path)
        except Exception as e:
            self.calculation_error.emit(str(e))

class RasterCalculatorWindow(QDialog):
    calculation_complete = Signal(np.ndarray, str, str)

    def __init__(self, all_layers: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Raster Calculator")
        self.setMinimumSize(900, 700)
        self.all_layers = all_layers if all_layers is not None else []
        self.layer_map = {layer['name']: layer for layer in self.all_layers}
        self.calculation_worker = None
        self.save_path = None  # Store save path
        
        self._setup_ui()
        self._connect_signals()
        self._populate_presets()
        if self.all_layers:
            self._update_band_list(0)
            self._update_layer_info()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Calculator Tab
        calc_tab = QWidget()
        self.tab_widget.addTab(calc_tab, "Calculator")
        self._setup_calculator_tab(calc_tab)
        
        # Functions Tab
        func_tab = QWidget()
        self.tab_widget.addTab(func_tab, "Functions")
        self._setup_functions_tab(func_tab)
        
        # Statistics Tab
        stats_tab = QWidget()
        self.tab_widget.addTab(stats_tab, "Statistics")
        self._setup_statistics_tab(stats_tab)
        
        # Progress bar and Buttons
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Close)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Execute")
        main_layout.addWidget(self.button_box)

    def _setup_calculator_tab(self, parent):
        layout = QHBoxLayout(parent)
        left_panel = QVBoxLayout()
        
        # Layer selection
        layer_group = QGroupBox("Raster Layers")
        layer_layout = QVBoxLayout(layer_group)
        self.layer_selector = QComboBox()
        self.layer_selector.addItems([layer['name'] for layer in self.all_layers])
        layer_layout.addWidget(QLabel("Select Layer:"))
        layer_layout.addWidget(self.layer_selector)
        self.layer_info = QLabel("No layer selected")
        layer_layout.addWidget(QLabel("Layer Information:"))
        layer_layout.addWidget(self.layer_info)
        left_panel.addWidget(layer_group)
        
        # Bands list
        bands_group = QGroupBox("Available Bands")
        bands_layout = QVBoxLayout(bands_group)
        self.bands_list = QListWidget()
        bands_layout.addWidget(QLabel("Double-click to add to expression:"))
        bands_layout.addWidget(self.bands_list)
        left_panel.addWidget(bands_group)
        
        # Right panel
        right_panel = QVBoxLayout()
        expr_group = QGroupBox("Expression")
        expr_layout = QVBoxLayout(expr_group)
        self.expression_edit = QTextEdit()
        self.expression_edit.setMaximumHeight(100)
        self.expression_edit.setPlaceholderText('Enter your raster calculation expression...')
        expr_layout.addWidget(self.expression_edit)
        
        # Expression validation
        validation_layout = QHBoxLayout()
        self.validate_btn = QPushButton("Validate Expression")
        self.validation_status = QLabel("Not validated")
        validation_layout.addWidget(self.validate_btn)
        validation_layout.addWidget(self.validation_status)
        expr_layout.addLayout(validation_layout)
        
        # Preset expressions
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Presets:"))
        self.preset_combo = QComboBox()
        preset_layout.addWidget(self.preset_combo)
        self.apply_preset_btn = QPushButton("Apply")
        preset_layout.addWidget(self.apply_preset_btn)
        expr_layout.addLayout(preset_layout)
        right_panel.addWidget(expr_group)
        
        # Operators panel
        operators_group = QGroupBox("Basic Operators")
        operators_layout = QGridLayout(operators_group)
        basic_ops = ['+', '-', '*', '/', '(', ')', '**', 'sqrt()']
        for i, op in enumerate(basic_ops):
            btn = QPushButton(op)
            btn.clicked.connect(lambda checked, o=op: self._add_to_expression(o))
            operators_layout.addWidget(btn, i // 4, i % 4)
        right_panel.addWidget(operators_group)
        
        # Output settings
        output_group = QGroupBox("Output Settings")
        output_layout = QVBoxLayout(output_group)
        
        self.output_name_edit = QLineEdit()
        self.output_name_edit.setPlaceholderText('Enter output layer name...')
        output_layout.addWidget(QLabel("Output Layer Name:"))
        output_layout.addWidget(self.output_name_edit)
        
        # Save options
        save_layout = QHBoxLayout()
        self.save_to_file_cb = QCheckBox("Save to file")
        self.choose_location_btn = QPushButton("Choose Location")
        self.choose_location_btn.setEnabled(False)
        self.save_location_label = QLabel("No location selected")
        save_layout.addWidget(self.save_to_file_cb)
        save_layout.addWidget(self.choose_location_btn)
        output_layout.addLayout(save_layout)
        output_layout.addWidget(self.save_location_label)
        
        options_layout = QHBoxLayout()
        self.add_to_project_cb = QCheckBox("Add result to project")
        self.add_to_project_cb.setChecked(True)
        options_layout.addWidget(self.add_to_project_cb)
        output_layout.addLayout(options_layout)
        right_panel.addWidget(output_group)
        
        layout.addLayout(left_panel, 1)
        layout.addLayout(right_panel, 2)

    def _setup_functions_tab(self, parent):
        layout = QVBoxLayout(parent)
        math_group = QGroupBox("Mathematical Functions")
        math_layout = QGridLayout(math_group)
        math_functions = [
            ('sin', 'sin()'), ('cos', 'cos()'), ('tan', 'tan()'),
            ('sqrt', 'sqrt()'), ('exp', 'exp()'), ('log', 'log()'),
            ('abs', 'abs()'), ('ceil', 'ceil()'), ('floor', 'floor()')
        ]
        for i, (name, func) in enumerate(math_functions):
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, f=func: self._add_function_to_expression(f))
            math_layout.addWidget(btn, i // 3, i % 3)
        layout.addWidget(math_group)

    def _setup_statistics_tab(self, parent):
        layout = QVBoxLayout(parent)
        stats_group = QGroupBox("Statistical Functions")
        stats_layout = QGridLayout(stats_group)
        stat_functions = [
            ('min', 'np.minimum'), ('max', 'np.maximum'), ('mean', 'np.mean'),
            ('std', 'np.std'), ('sum', 'np.sum')
        ]
        for i, (name, func) in enumerate(stat_functions):
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, f=func: self._add_function_to_expression(f + '()'))
            stats_layout.addWidget(btn, i // 3, i % 3)
        layout.addWidget(stats_group)
        
        # Band statistics
        band_stats_group = QGroupBox("Band Statistics")
        band_stats_layout = QVBoxLayout(band_stats_group)
        self.stats_table = QTableWidget(0, 4)
        self.stats_table.setHorizontalHeaderLabels(['Band', 'Min', 'Max', 'Mean'])
        band_stats_layout.addWidget(self.stats_table)
        refresh_stats_btn = QPushButton("Refresh Statistics")
        refresh_stats_btn.clicked.connect(self._refresh_band_statistics)
        band_stats_layout.addWidget(refresh_stats_btn)
        layout.addWidget(band_stats_group)

    def _connect_signals(self):
        self.layer_selector.currentIndexChanged.connect(self._update_band_list)
        self.layer_selector.currentIndexChanged.connect(self._update_layer_info)
        self.bands_list.itemDoubleClicked.connect(self._add_band_to_expression)
        self.apply_preset_btn.clicked.connect(self._apply_preset)
        self.validate_btn.clicked.connect(self._validate_expression)
        self.save_to_file_cb.toggled.connect(self._on_save_to_file_toggled)
        self.choose_location_btn.clicked.connect(self._choose_save_location)
        self.button_box.accepted.connect(self._execute_calculation)
        self.button_box.rejected.connect(self.reject)

    def _populate_presets(self):
        presets = ['NDVI', 'NDWI', 'EVI', 'Band Ratio', 'Band Difference', 'Normalized Difference']
        self.preset_combo.addItem("Select preset...")
        for preset in presets:
            self.preset_combo.addItem(preset)

    def _update_band_list(self, index: int):
        if not self.all_layers:
            return
        self.bands_list.clear()
        selected_layer = self.all_layers[index]
        band_names = selected_layer.get("band_names", [])
        wavelengths = selected_layer.get("metadata", {}).get("wavelength", [])
        

        #checking type of wavelengths and if it is having any value or not
        if type(wavelengths) is not list:
            wavelengths = [float(x)*1000 if float(x)<100 else float(x) for x in selected_layer.get("metadata", {}).get("wavelength", "").replace("{","").replace("}","").split(",") if x.strip()]

        if len(wavelengths) == len(band_names):
            self.bands_list.addItems([f'b{i+1}: {name} ({wavelengths[i]:.2f} nm)' for i, name in enumerate(band_names)])
        else:
            self.bands_list.addItems([f'b{i+1}: {name}' for i, name in enumerate(band_names)])

    def _update_layer_info(self):
        if not self.all_layers:
            return
        index = self.layer_selector.currentIndex()
        layer = self.all_layers[index]
        info_text = f"Name: {layer['name']}\n"
        info_text += f"Dimensions: {layer['data'].shape}\n"
        info_text += f"Data Type: {layer['data'].dtype}\n"
        info_text += f"Bands: {layer['data'].shape[2]}\n"
        # self.metadata = layer['metadata']['Wavelengths']
 
        self.layer_info.setText(info_text)

    def _add_band_to_expression(self, item):
        layer_name = self.layer_selector.currentText()
        band_id = item.text().split(':')[0]
        formatted_band = f'"{layer_name}@{band_id}"'
        cursor = self.expression_edit.textCursor()
        cursor.insertText(formatted_band)

    def _add_to_expression(self, text):
        cursor = self.expression_edit.textCursor()
        cursor.insertText(text)

    def _add_function_to_expression(self, func):
        cursor = self.expression_edit.textCursor()
        if '()' in func:
            cursor.insertText(func[:-1])
            cursor.insertText(')')
            cursor.movePosition(cursor.MoveOperation.Left)
            self.expression_edit.setTextCursor(cursor)
        else:
            cursor.insertText(func)

    def _apply_preset(self):
        """Apply selected preset with band selection dialog"""
        preset_name = self.preset_combo.currentText()
        if preset_name == "Select preset...":
            return
        
        
        if not self.all_layers:
            QMessageBox.warning(self, "No Layers", "Please load raster layers first.")
            return
        
        # Show band selection dialog
        band_dialog = BandSelectionDialog(preset_name, self.all_layers, self)
        if band_dialog.exec() == QDialog.DialogCode.Accepted:
            expression = band_dialog.get_expression()
            print(expression)
            if expression:  # Only set if we got a valid expression
                self.expression_edit.setPlainText(expression)
                # Auto-validate after applying preset
                self._validate_expression()
                print(f"Successfully applied {preset_name} preset")
            else:
                QMessageBox.warning(self, "Expression Error", 
                                f"Could not generate expression for {preset_name}. "
                                "Please check that you selected the correct bands.")
        else:
            print("Band selection dialog was cancelled")

    def _validate_expression(self):
        """Validate the current expression"""
        expression = self.expression_edit.toPlainText().strip()
        if not expression:
            self.validation_status.setText("No expression to validate")
            self.validation_status.setStyleSheet("color: orange;")
            return
        
        is_valid, message = ExpressionValidator.validate_complete(expression, self.layer_map)
        
        if is_valid:
            self.validation_status.setText("✓ Valid expression")
            self.validation_status.setStyleSheet("color: green;")
        else:
            self.validation_status.setText(f"✗ {message}")
            self.validation_status.setStyleSheet("color: red;")

    def _on_save_to_file_toggled(self, checked):
        """Enable/disable save location selection"""
        self.choose_location_btn.setEnabled(checked)
        if not checked:
            self.save_path = None
            self.save_location_label.setText("No location selected")

    def _choose_save_location(self):
        """Choose save location for output file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Calculation Result",
            "",
            "NumPy Arrays (*.npy);;TIFF Images (*.tif);;All Files (*)"
        )
        
        if file_path:
            self.save_path = file_path
            self.save_location_label.setText(f"Save to: {os.path.basename(file_path)}")

    def _refresh_band_statistics(self):
        if not self.all_layers:
            return
        index = self.layer_selector.currentIndex()
        layer = self.all_layers[index]
        data = layer['data']
        self.stats_table.setRowCount(data.shape[2])
        for i in range(data.shape[2]):
            band_data = data[:, :, i]
            band_data = band_data[~np.isnan(band_data)]
            if len(band_data) > 0:
                min_val = np.min(band_data)
                max_val = np.max(band_data)
                mean_val = np.mean(band_data)
                self.stats_table.setItem(i, 0, QTableWidgetItem(f"Band {i+1}"))
                self.stats_table.setItem(i, 1, QTableWidgetItem(f"{min_val:.4f}"))
                self.stats_table.setItem(i, 2, QTableWidgetItem(f"{max_val:.4f}"))
                self.stats_table.setItem(i, 3, QTableWidgetItem(f"{mean_val:.4f}"))

    def _execute_calculation(self):
        """Execute the raster calculation with validation"""
        expression = self.expression_edit.toPlainText().strip()
        if not expression:
            QMessageBox.warning(self, "Input Error", "Expression cannot be empty.")
            return

        # Validate expression first
        is_valid, message = ExpressionValidator.validate_complete(expression, self.layer_map)
        if not is_valid:
            QMessageBox.critical(self, "Expression Error", f"Invalid expression: {message}")
            return

        # Check save location if saving to file
        if self.save_to_file_cb.isChecked() and not self.save_path:
            QMessageBox.warning(self, "Save Location", "Please choose a save location.")
            return

        try:
            # Find band identifiers and create variable mapping
            band_identifiers = set(re.findall(r'"([^"]+@b\d+)"', expression))
            variable_map = {}
            for i, identifier in enumerate(band_identifiers):
                variable_map[identifier] = f'var_{i}'

            output_name = self.output_name_edit.text().strip()
            if not output_name:
                output_name = "Calculated_Raster"

            parent_layer = list(band_identifiers)[0].split('@')[0]

            # Start calculation
            self.calculation_worker = CalculationWorker(
                expression, self.layer_map, variable_map, output_name, parent_layer, self.save_path
            )
            self.calculation_worker.calculation_finished.connect(self._on_calculation_finished)
            self.calculation_worker.calculation_error.connect(self._on_calculation_error)
            self.calculation_worker.progress_updated.connect(self._on_progress_updated)
            
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            
            self.calculation_worker.start()

        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", f"An error occurred:\n{e}")

    def _on_calculation_finished(self, result_array, output_name, parent_layer, save_path):
        """Handle successful calculation completion"""
        self.progress_bar.setVisible(False)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
        
        # Save to file if requested
        if save_path:
            try:
                if save_path.endswith('.npy'):
                    np.save(save_path, result_array)
                elif save_path.endswith('.tif') or save_path.endswith('.tiff'):
                    # Basic TIFF save (you might want to use rasterio for more advanced features)
                    try:
                        from PIL import Image
                        # Normalize for display
                        normalized = ((result_array[:,:,0] - result_array[:,:,0].min()) / 
                                    (result_array[:,:,0].max() - result_array[:,:,0].min()) * 255).astype(np.uint8)
                        Image.fromarray(normalized).save(save_path)
                    except ImportError:
                        # Fallback to numpy save if PIL not available
                        np.save(save_path.replace('.tif', '.npy'), result_array)
                        QMessageBox.information(self, "Format Note", "PIL not available. Saved as .npy format instead.")
                
                QMessageBox.information(self, "File Saved", f"Result saved to {save_path}")
            except Exception as e:
                QMessageBox.warning(self, "Save Error", f"Could not save file: {str(e)}")
        
        # Emit signal for adding to project
        self.calculation_complete.emit(result_array, output_name, parent_layer)
        
        if self.add_to_project_cb.isChecked():
            QMessageBox.information(self, "Success", f"Calculation completed successfully!\nOutput: {output_name}")
        
        self.accept()

    def _on_calculation_error(self, error_message):
        """Handle calculation error"""
        self.progress_bar.setVisible(False)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
        QMessageBox.critical(self, "Calculation Error", f"An error occurred:\n{error_message}")

    def _on_progress_updated(self, value):
        """Update progress bar"""
        self.progress_bar.setValue(value)


























# import sys
# import re
# import os
# import ast
# import numpy as np
# from PySide6.QtWidgets import (
#     QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, QGridLayout,
#     QApplication, QMessageBox, QLabel, QDialogButtonBox, QComboBox, QPushButton,
#     QTabWidget, QWidget, QGroupBox, QTextEdit, QTableWidget, QTableWidgetItem, 
#     QProgressBar, QCheckBox, QFileDialog, QListWidgetItem
# )
# from PySide6.QtCore import Signal, Qt, QThread
# from PySide6.QtGui import QFont

# class BandSelectionDialog(QDialog):
#     """Dialog for selecting bands for preset calculations"""
    
#     def __init__(self, preset_name, all_layers, parent=None):
#         super().__init__(parent)
#         self.setWindowTitle(f"Select Bands for {preset_name}")
#         self.setMinimumSize(400, 300)
#         self.preset_name = preset_name
#         self.all_layers = all_layers
#         self.selected_bands = {}
        
#         self._setup_ui()
#         self._connect_signals()
        
#     def _setup_ui(self):
#         layout = QVBoxLayout(self)
        
#         # Instructions
#         instruction_text = self._get_instruction_text()
#         instruction_label = QLabel(instruction_text)
#         instruction_label.setWordWrap(True)
#         layout.addWidget(instruction_label)
        
#         # Layer selection
#         layer_group = QGroupBox("Select Layer")
#         layer_layout = QVBoxLayout(layer_group)
        
#         self.layer_combo = QComboBox()
#         self.layer_combo.addItems([layer['name'] for layer in self.all_layers])
#         layer_layout.addWidget(self.layer_combo)
#         layout.addWidget(layer_group)
        
#         # Band selection based on preset type
#         bands_group = QGroupBox("Select Required Bands")
#         bands_layout = QVBoxLayout(bands_group)
        
#         self.band_selections = {}
#         required_bands = self._get_required_bands()
        
#         for band_name, description in required_bands.items():
#             band_layout = QHBoxLayout()
#             band_layout.addWidget(QLabel(f"{band_name}: {description}"))
            
#             band_combo = QComboBox()
#             self._populate_band_combo(band_combo)
#             band_layout.addWidget(band_combo)
            
#             bands_layout.addLayout(band_layout)
#             self.band_selections[band_name] = band_combo
        
#         layout.addWidget(bands_group)
        
#         # Dialog buttons
#         self.button_box = QDialogButtonBox(
#             QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
#         )
#         layout.addWidget(self.button_box)
    
#     def _connect_signals(self):
#         self.layer_combo.currentTextChanged.connect(self._update_band_combos)
#         self.button_box.accepted.connect(self._validate_and_accept)
#         self.button_box.rejected.connect(self.reject)
    
#     def _get_instruction_text(self):
#         instructions = {
#             'NDVI': 'NDVI requires Red and Near-Infrared bands. Select the appropriate bands below.',
#             'NDWI': 'NDWI requires Green and Near-Infrared bands. Select the appropriate bands below.',
#             'EVI': 'EVI requires Blue, Red, and Near-Infrared bands. Select the appropriate bands below.',
#             'Band Ratio': 'Select two bands for ratio calculation.',
#             'Band Difference': 'Select two bands for difference calculation.',
#             'Normalized Difference': 'Select two bands for normalized difference calculation.'
#         }
#         return instructions.get(self.preset_name, 'Select the required bands for this calculation.')
    
#     def _get_required_bands(self):
#         band_requirements = {
#             'NDVI': {'Red': 'Red band (~660nm)', 'NIR': 'Near-Infrared band (~840nm)'},
#             'NDWI': {'Green': 'Green band (~560nm)', 'NIR': 'Near-Infrared band (~840nm)'},
#             'EVI': {'Blue': 'Blue band (~470nm)', 'Red': 'Red band (~660nm)', 'NIR': 'Near-Infrared band (~840nm)'},
#             'Band Ratio': {'Band1': 'First band', 'Band2': 'Second band'},
#             'Band Difference': {'Band1': 'First band', 'Band2': 'Second band'},
#             'Normalized Difference': {'Band1': 'First band', 'Band2': 'Second band'}
#         }
#         return band_requirements.get(self.preset_name, {'Band1': 'First band', 'Band2': 'Second band'})
    
#     def _populate_band_combo(self, combo):
#         if self.all_layers:
#             current_layer = self.all_layers[0]
#             band_names = current_layer.get("band_names", [])
#             for i, name in enumerate(band_names):
#                 combo.addItem(f"b{i+1}: {name}")
    
#     def _update_band_combos(self):
#         layer_name = self.layer_combo.currentText()
#         if not layer_name:
#             return
            
#         # Find the selected layer
#         selected_layer = None
#         for layer in self.all_layers:
#             if layer['name'] == layer_name:
#                 selected_layer = layer
#                 break
        
#         if selected_layer:
#             band_names = selected_layer.get("band_names", [])
#             for combo in self.band_selections.values():
#                 combo.clear()
#                 for i, name in enumerate(band_names):
#                     combo.addItem(f"b{i+1}: {name}")
    
#     def _validate_and_accept(self):
#         layer_name = self.layer_combo.currentText()
#         if not layer_name:
#             QMessageBox.warning(self, "Selection Error", "Please select a layer.")
#             return
        
#         # Store selected bands
#         for band_key, combo in self.band_selections.items():
#             if combo.currentIndex() == -1:
#                 QMessageBox.warning(self, "Selection Error", f"Please select {band_key}.")
#                 return
#             self.selected_bands[band_key] = combo.currentText().split(':')[0]  # Get 'b1', 'b2', etc.
        
#         self.selected_layer = layer_name
#         self.accept()
    
#     def get_expression(self):
#         """Generate expression based on preset and selected bands"""
#         expressions = {
#             'NDVI': f'("{self.selected_layer}@{self.selected_bands["NIR"]}" - "{self.selected_layer}@{self.selected_bands["Red"]}") / ("{self.selected_layer}@{self.selected_bands["NIR"]}" + "{self.selected_layer}@{self.selected_bands["Red"]}")',
#             'NDWI': f'("{self.selected_layer}@{self.selected_bands["Green"]}" - "{self.selected_layer}@{self.selected_bands["NIR"]}") / ("{self.selected_layer}@{self.selected_bands["Green"]}" + "{self.selected_layer}@{self.selected_bands["NIR"]}")',
#             'EVI': f'2.5 * (("{self.selected_layer}@{self.selected_bands["NIR"]}" - "{self.selected_layer}@{self.selected_bands["Red"]}") / ("{self.selected_layer}@{self.selected_bands["NIR"]}" + 6 * "{self.selected_layer}@{self.selected_bands["Red"]}" - 7.5 * "{self.selected_layer}@{self.selected_bands["Blue"]}" + 1))',
#             'Band Ratio': f'"{self.selected_layer}@{self.selected_bands["Band1"]}" / "{self.selected_layer}@{self.selected_bands["Band2"]}"',
#             'Band Difference': f'"{self.selected_layer}@{self.selected_bands["Band1"]}" - "{self.selected_layer}@{self.selected_bands["Band2"]}"',
#             'Normalized Difference': f'("{self.selected_layer}@{self.selected_bands["Band1"]}" - "{self.selected_layer}@{self.selected_bands["Band2"]}") / ("{self.selected_layer}@{self.selected_bands["Band1"]}" + "{self.selected_layer}@{self.selected_bands["Band2"]}")'
#         }
#         return expressions.get(self.preset_name, '')

# class ExpressionValidator:
#     """Validates mathematical expressions for raster calculations"""
    
#     @staticmethod
#     def validate_syntax(expression):
#         """Validate Python syntax of expression"""
#         try:
#             # Replace band identifiers with dummy variables for syntax checking
#             test_expr = re.sub(r'"[^"]+@b\d+"', 'x', expression)
#             ast.parse(test_expr, mode='eval')
#             return True, "Valid syntax"
#         except SyntaxError as e:
#             return False, f"Syntax error: {str(e)}"
    
#     @staticmethod
#     def validate_band_references(expression, layer_map):
#         """Validate that all band references exist"""
#         band_identifiers = set(re.findall(r'"([^"]+@b\d+)"', expression))
        
#         for identifier in band_identifiers:
#             try:
#                 layer_name, band_id = identifier.split('@')
#                 band_index = int(band_id[1:]) - 1
                
#                 if layer_name not in layer_map:
#                     return False, f"Layer '{layer_name}' not found"
                
#                 layer_data = layer_map[layer_name]['data']
#                 if not (0 <= band_index < layer_data.shape[2]):
#                     return False, f"Band index {band_index+1} is out of bounds for layer '{layer_name}'"
                    
#             except (ValueError, IndexError):
#                 return False, f"Invalid band identifier: {identifier}"
        
#         if not band_identifiers:
#             return False, "No valid band identifiers found"
        
#         return True, "All band references are valid"
    
#     @staticmethod
#     def validate_complete(expression, layer_map):
#         """Complete validation of expression"""
#         # Check syntax
#         syntax_valid, syntax_msg = ExpressionValidator.validate_syntax(expression)
#         if not syntax_valid:
#             return False, syntax_msg
        
#         # Check band references
#         bands_valid, bands_msg = ExpressionValidator.validate_band_references(expression, layer_map)
#         if not bands_valid:
#             return False, bands_msg
        
#         return True, "Expression is valid"

# class CalculationWorker(QThread):
#     calculation_finished = Signal(np.ndarray, str, str, str)  # Added save_path parameter
#     calculation_error = Signal(str)
#     progress_updated = Signal(int)

#     def __init__(self, expression, layer_map, variable_map, output_name, parent_layer, save_path=None):
#         super().__init__()
#         self.expression = expression
#         self.layer_map = layer_map
#         self.variable_map = variable_map
#         self.output_name = output_name
#         self.parent_layer = parent_layer
#         self.save_path = save_path

#     def run(self):
#         try:
#             local_namespace = {'np': np}
#             # Add mathematical functions
#             math_functions = {
#                 'sin': np.sin, 'cos': np.cos, 'tan': np.tan, 'asin': np.arcsin,
#                 'acos': np.arccos, 'atan': np.arctan, 'sqrt': np.sqrt,
#                 'exp': np.exp, 'log': np.log, 'log10': np.log10, 'abs': np.abs,
#                 'ceil': np.ceil, 'floor': np.floor, 'round': np.round,
#                 'min': np.minimum, 'max': np.maximum, 'mean': np.mean,
#                 'median': np.median, 'std': np.std, 'var': np.var
#             }
#             local_namespace.update(math_functions)
#             self.progress_updated.emit(20)

#             for identifier, var_name in self.variable_map.items():
#                 layer_name, band_id = identifier.split('@')
#                 band_index = int(band_id[1:]) - 1
#                 layer_data = self.layer_map[layer_name]['data']
#                 local_namespace[var_name] = layer_data[:, :, band_index].astype(np.float64)

#             self.progress_updated.emit(50)
#             processed_expression = self.expression
#             for identifier, var_name in self.variable_map.items():
#                 processed_expression = processed_expression.replace(f'"{identifier}"', var_name)

#             self.progress_updated.emit(70)
#             with np.errstate(divide='ignore', invalid='ignore'):
#                 result_array = eval(processed_expression, {"__builtins__": {}}, local_namespace)

#             if np.isscalar(result_array):
#                 result_array = np.full_like(list(local_namespace.values())[0], result_array)

#             result_array = np.nan_to_num(result_array, nan=0.0, posinf=0.0, neginf=0.0)
#             if result_array.ndim == 2:
#                 result_array = result_array[:, :, np.newaxis]

#             self.progress_updated.emit(100)
#             self.calculation_finished.emit(result_array, self.output_name, self.parent_layer, self.save_path)
#         except Exception as e:
#             self.calculation_error.emit(str(e))

# class RasterCalculatorWindow(QDialog):
#     calculation_complete = Signal(np.ndarray, str, str)

#     def __init__(self, all_layers: list, parent=None):
#         super().__init__(parent)
#         self.setWindowTitle("Advanced Raster Calculator")
#         self.setMinimumSize(900, 700)
#         self.all_layers = all_layers if all_layers is not None else []
#         self.layer_map = {layer['name']: layer for layer in self.all_layers}
#         self.calculation_worker = None
#         self.save_path = None  # Store save path
        
#         self._setup_ui()
#         self._connect_signals()
#         self._populate_presets()
#         if self.all_layers:
#             self._update_band_list(0)
#             self._update_layer_info()

#     def _setup_ui(self):
#         main_layout = QVBoxLayout(self)
#         self.tab_widget = QTabWidget()
#         main_layout.addWidget(self.tab_widget)
        
#         # Calculator Tab
#         calc_tab = QWidget()
#         self.tab_widget.addTab(calc_tab, "Calculator")
#         self._setup_calculator_tab(calc_tab)
        
#         # Functions Tab
#         func_tab = QWidget()
#         self.tab_widget.addTab(func_tab, "Functions")
#         self._setup_functions_tab(func_tab)
        
#         # Statistics Tab
#         stats_tab = QWidget()
#         self.tab_widget.addTab(stats_tab, "Statistics")
#         self._setup_statistics_tab(stats_tab)
        
#         # Progress bar and Buttons
#         self.progress_bar = QProgressBar()
#         self.progress_bar.setVisible(False)
#         main_layout.addWidget(self.progress_bar)
        
#         self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Close)
#         self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Execute")
#         main_layout.addWidget(self.button_box)

#     def _setup_calculator_tab(self, parent):
#         layout = QHBoxLayout(parent)
#         left_panel = QVBoxLayout()
        
#         # Layer selection
#         layer_group = QGroupBox("Raster Layers")
#         layer_layout = QVBoxLayout(layer_group)
#         self.layer_selector = QComboBox()
#         self.layer_selector.addItems([layer['name'] for layer in self.all_layers])
#         layer_layout.addWidget(QLabel("Select Layer:"))
#         layer_layout.addWidget(self.layer_selector)
#         self.layer_info = QLabel("No layer selected")
#         layer_layout.addWidget(QLabel("Layer Information:"))
#         layer_layout.addWidget(self.layer_info)
#         left_panel.addWidget(layer_group)
        
#         # Bands list
#         bands_group = QGroupBox("Available Bands")
#         bands_layout = QVBoxLayout(bands_group)
#         self.bands_list = QListWidget()
#         bands_layout.addWidget(QLabel("Double-click to add to expression:"))
#         bands_layout.addWidget(self.bands_list)
#         left_panel.addWidget(bands_group)
        
#         # Right panel
#         right_panel = QVBoxLayout()
#         expr_group = QGroupBox("Expression")
#         expr_layout = QVBoxLayout(expr_group)
#         self.expression_edit = QTextEdit()
#         self.expression_edit.setMaximumHeight(100)
#         self.expression_edit.setPlaceholderText('Enter your raster calculation expression...')
#         expr_layout.addWidget(self.expression_edit)
        
#         # Expression validation
#         validation_layout = QHBoxLayout()
#         self.validate_btn = QPushButton("Validate Expression")
#         self.validation_status = QLabel("Not validated")
#         validation_layout.addWidget(self.validate_btn)
#         validation_layout.addWidget(self.validation_status)
#         expr_layout.addLayout(validation_layout)
        
#         # Preset expressions
#         preset_layout = QHBoxLayout()
#         preset_layout.addWidget(QLabel("Presets:"))
#         self.preset_combo = QComboBox()
#         preset_layout.addWidget(self.preset_combo)
#         self.apply_preset_btn = QPushButton("Apply")
#         preset_layout.addWidget(self.apply_preset_btn)
#         expr_layout.addLayout(preset_layout)
#         right_panel.addWidget(expr_group)
        
#         # Operators panel (keeping it simple for space)
#         operators_group = QGroupBox("Basic Operators")
#         operators_layout = QGridLayout(operators_group)
#         basic_ops = ['+', '-', '*', '/', '(', ')', '**', 'sqrt()']
#         for i, op in enumerate(basic_ops):
#             btn = QPushButton(op)
#             btn.clicked.connect(lambda checked, o=op: self._add_to_expression(o))
#             operators_layout.addWidget(btn, i // 4, i % 4)
#         right_panel.addWidget(operators_group)
        
#         # Output settings
#         output_group = QGroupBox("Output Settings")
#         output_layout = QVBoxLayout(output_group)
        
#         self.output_name_edit = QLineEdit()
#         self.output_name_edit.setPlaceholderText('Enter output layer name...')
#         output_layout.addWidget(QLabel("Output Layer Name:"))
#         output_layout.addWidget(self.output_name_edit)
        
#         # Save options
#         save_layout = QHBoxLayout()
#         self.save_to_file_cb = QCheckBox("Save to file")
#         self.choose_location_btn = QPushButton("Choose Location")
#         self.choose_location_btn.setEnabled(False)
#         self.save_location_label = QLabel("No location selected")
#         save_layout.addWidget(self.save_to_file_cb)
#         save_layout.addWidget(self.choose_location_btn)
#         output_layout.addLayout(save_layout)
#         output_layout.addWidget(self.save_location_label)
        
#         options_layout = QHBoxLayout()
#         self.add_to_project_cb = QCheckBox("Add result to project")
#         self.add_to_project_cb.setChecked(True)
#         options_layout.addWidget(self.add_to_project_cb)
#         output_layout.addLayout(options_layout)
#         right_panel.addWidget(output_group)
        
#         layout.addLayout(left_panel, 1)
#         layout.addLayout(right_panel, 2)

#     def _setup_functions_tab(self, parent):
#         layout = QVBoxLayout(parent)
#         math_group = QGroupBox("Mathematical Functions")
#         math_layout = QGridLayout(math_group)
#         math_functions = [
#             ('sin', 'sin()'), ('cos', 'cos()'), ('tan', 'tan()'),
#             ('sqrt', 'sqrt()'), ('exp', 'exp()'), ('log', 'log()'),
#             ('abs', 'abs()'), ('ceil', 'ceil()'), ('floor', 'floor()')
#         ]
#         for i, (name, func) in enumerate(math_functions):
#             btn = QPushButton(name)
#             btn.clicked.connect(lambda checked, f=func: self._add_function_to_expression(f))
#             math_layout.addWidget(btn, i // 3, i % 3)
#         layout.addWidget(math_group)

#     def _setup_statistics_tab(self, parent):
#         layout = QVBoxLayout(parent)
#         stats_group = QGroupBox("Statistical Functions")
#         stats_layout = QGridLayout(stats_group)
#         stat_functions = [
#             ('min', 'np.minimum'), ('max', 'np.maximum'), ('mean', 'np.mean'),
#             ('std', 'np.std'), ('sum', 'np.sum')
#         ]
#         for i, (name, func) in enumerate(stat_functions):
#             btn = QPushButton(name)
#             btn.clicked.connect(lambda checked, f=func: self._add_function_to_expression(f + '()'))
#             stats_layout.addWidget(btn, i // 3, i % 3)
#         layout.addWidget(stats_group)
        
#         # Band statistics
#         band_stats_group = QGroupBox("Band Statistics")
#         band_stats_layout = QVBoxLayout(band_stats_group)
#         self.stats_table = QTableWidget(0, 4)
#         self.stats_table.setHorizontalHeaderLabels(['Band', 'Min', 'Max', 'Mean'])
#         band_stats_layout.addWidget(self.stats_table)
#         refresh_stats_btn = QPushButton("Refresh Statistics")
#         refresh_stats_btn.clicked.connect(self._refresh_band_statistics)
#         band_stats_layout.addWidget(refresh_stats_btn)
#         layout.addWidget(band_stats_group)

#     def _connect_signals(self):
#         self.layer_selector.currentIndexChanged.connect(self._update_band_list)
#         self.layer_selector.currentIndexChanged.connect(self._update_layer_info)
#         self.bands_list.itemDoubleClicked.connect(self._add_band_to_expression)
#         self.apply_preset_btn.clicked.connect(self._apply_preset)
#         self.validate_btn.clicked.connect(self._validate_expression)
#         self.save_to_file_cb.toggled.connect(self._on_save_to_file_toggled)
#         self.choose_location_btn.clicked.connect(self._choose_save_location)
#         self.button_box.accepted.connect(self._execute_calculation)
#         self.button_box.rejected.connect(self.reject)

#     def _populate_presets(self):
#         presets = ['NDVI', 'NDWI', 'EVI', 'Band Ratio', 'Band Difference', 'Normalized Difference']
#         self.preset_combo.addItem("Select preset...")
#         for preset in presets:
#             self.preset_combo.addItem(preset)

#     def _update_band_list(self, index: int):
#         if not self.all_layers:
#             return
#         self.bands_list.clear()
#         selected_layer = self.all_layers[index]
#         band_names = selected_layer.get("band_names", [])
#         self.bands_list.addItems([f'b{i+1}: {name}' for i, name in enumerate(band_names)])

#     def _update_layer_info(self):
#         if not self.all_layers:
#             return
#         index = self.layer_selector.currentIndex()
#         layer = self.all_layers[index]
#         info_text = f"Name: {layer['name']}\n"
#         info_text += f"Dimensions: {layer['data'].shape}\n"
#         info_text += f"Data Type: {layer['data'].dtype}\n"
#         info_text += f"Bands: {layer['data'].shape[2]}"
#         self.layer_info.setText(info_text)

#     def _add_band_to_expression(self, item):
#         layer_name = self.layer_selector.currentText()
#         band_id = item.text().split(':')[0]
#         formatted_band = f'"{layer_name}@{band_id}"'
#         cursor = self.expression_edit.textCursor()
#         cursor.insertText(formatted_band)

#     def _add_to_expression(self, text):
#         cursor = self.expression_edit.textCursor()
#         cursor.insertText(text)

#     def _add_function_to_expression(self, func):
#         cursor = self.expression_edit.textCursor()
#         if '()' in func:
#             cursor.insertText(func[:-1])
#             cursor.insertText(')')
#             cursor.movePosition(cursor.MoveOperation.Left)
#             self.expression_edit.setTextCursor(cursor)
#         else:
#             cursor.insertText(func)

#     def _apply_preset(self):
#         """Apply selected preset with band selection dialog"""
#         preset_name = self.preset_combo.currentText()
#         if preset_name == "Select preset...":
#             return
        
#         if not self.all_layers:
#             QMessageBox.warning(self, "No Layers", "Please load raster layers first.")
#             return
        
#         # Show band selection dialog
#         band_dialog = BandSelectionDialog(preset_name, self.all_layers, self)
#         if band_dialog.exec() == QDialog.DialogCode.Accepted:
#             expression = band_dialog.get_expression()
#             print(expression)
#             self.expression_edit.setPlainText(expression)
#             # Auto-validate after applying preset
#             self._validate_expression()

#     def _validate_expression(self):
#         """Validate the current expression"""
#         expression = self.expression_edit.toPlainText().strip()
#         if not expression:
#             self.validation_status.setText("No expression to validate")
#             self.validation_status.setStyleSheet("color: orange;")
#             return
        
#         is_valid, message = ExpressionValidator.validate_complete(expression, self.layer_map)
        
#         if is_valid:
#             self.validation_status.setText("✓ Valid expression")
#             self.validation_status.setStyleSheet("color: green;")
#         else:
#             self.validation_status.setText(f"✗ {message}")
#             self.validation_status.setStyleSheet("color: red;")

#     def _on_save_to_file_toggled(self, checked):
#         """Enable/disable save location selection"""
#         self.choose_location_btn.setEnabled(checked)
#         if not checked:
#             self.save_path = None
#             self.save_location_label.setText("No location selected")

#     def _choose_save_location(self):
#         """Choose save location for output file"""
#         file_path, _ = QFileDialog.getSaveFileName(
#             self,
#             "Save Calculation Result",
#             "",
#             "NumPy Arrays (*.npy);;TIFF Images (*.tif);;All Files (*)"
#         )
        
#         if file_path:
#             self.save_path = file_path
#             self.save_location_label.setText(f"Save to: {os.path.basename(file_path)}")

#     def _refresh_band_statistics(self):
#         if not self.all_layers:
#             return
#         index = self.layer_selector.currentIndex()
#         layer = self.all_layers[index]
#         data = layer['data']
#         self.stats_table.setRowCount(data.shape[2])
#         for i in range(data.shape[2]):
#             band_data = data[:, :, i]
#             band_data = band_data[~np.isnan(band_data)]
#             if len(band_data) > 0:
#                 min_val = np.min(band_data)
#                 max_val = np.max(band_data)
#                 mean_val = np.mean(band_data)
#                 self.stats_table.setItem(i, 0, QTableWidgetItem(f"Band {i+1}"))
#                 self.stats_table.setItem(i, 1, QTableWidgetItem(f"{min_val:.4f}"))
#                 self.stats_table.setItem(i, 2, QTableWidgetItem(f"{max_val:.4f}"))
#                 self.stats_table.setItem(i, 3, QTableWidgetItem(f"{mean_val:.4f}"))

#     def _execute_calculation(self):
#         """Execute the raster calculation with validation"""
#         expression = self.expression_edit.toPlainText().strip()
#         if not expression:
#             QMessageBox.warning(self, "Input Error", "Expression cannot be empty.")
#             return

#         # Validate expression first
#         is_valid, message = ExpressionValidator.validate_complete(expression, self.layer_map)
#         if not is_valid:
#             QMessageBox.critical(self, "Expression Error", f"Invalid expression: {message}")
#             return

#         # Check save location if saving to file
#         if self.save_to_file_cb.isChecked() and not self.save_path:
#             QMessageBox.warning(self, "Save Location", "Please choose a save location.")
#             return

#         try:
#             # Find band identifiers and create variable mapping
#             band_identifiers = set(re.findall(r'"([^"]+@b\d+)"', expression))
#             variable_map = {}
#             for i, identifier in enumerate(band_identifiers):
#                 variable_map[identifier] = f'var_{i}'

#             output_name = self.output_name_edit.text().strip()
#             if not output_name:
#                 output_name = "Calculated_Raster"

#             parent_layer = list(band_identifiers)[0].split('@')[0]

#             # Start calculation
#             self.calculation_worker = CalculationWorker(
#                 expression, self.layer_map, variable_map, output_name, parent_layer, self.save_path
#             )
#             self.calculation_worker.calculation_finished.connect(self._on_calculation_finished)
#             self.calculation_worker.calculation_error.connect(self._on_calculation_error)
#             self.calculation_worker.progress_updated.connect(self._on_progress_updated)
            
#             self.progress_bar.setVisible(True)
#             self.progress_bar.setValue(0)
#             self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            
#             self.calculation_worker.start()

#         except Exception as e:
#             QMessageBox.critical(self, "Calculation Error", f"An error occurred:\n{e}")

#     def _on_calculation_finished(self, result_array, output_name, parent_layer, save_path):
#         """Handle successful calculation completion"""
#         self.progress_bar.setVisible(False)
#         self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
        
#         # Save to file if requested
#         if save_path:
#             try:
#                 if save_path.endswith('.npy'):
#                     np.save(save_path, result_array)
#                 elif save_path.endswith('.tif') or save_path.endswith('.tiff'):
#                     # Basic TIFF save (you might want to use rasterio for more advanced features)
#                     from PIL import Image
#                     # Normalize for display
#                     normalized = ((result_array[:,:,0] - result_array[:,:,0].min()) / 
#                                 (result_array[:,:,0].max() - result_array[:,:,0].min()) * 255).astype(np.uint8)
#                     Image.fromarray(normalized).save(save_path)
                
#                 QMessageBox.information(self, "File Saved", f"Result saved to {save_path}")
#             except Exception as e:
#                 QMessageBox.warning(self, "Save Error", f"Could not save file: {str(e)}")
        
#         # Emit signal for adding to project
#         self.calculation_complete.emit(result_array, output_name, parent_layer)
        
#         if self.add_to_project_cb.isChecked():
#             QMessageBox.information(self, "Success", f"Calculation completed successfully!\nOutput: {output_name}")
        
#         self.accept()

#     def _on_calculation_error(self, error_message):
#         """Handle calculation error"""
#         self.progress_bar.setVisible(False)
#         self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
#         QMessageBox.critical(self, "Calculation Error", f"An error occurred:\n{error_message}")

#     def _on_progress_updated(self, value):
#         """Update progress bar"""
#         self.progress_bar.setValue(value)





















































# import sys
# import re
# import numpy as np
# from PySide6.QtWidgets import (
#     QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, QGridLayout,
#     QApplication, QMessageBox, QLabel, QDialogButtonBox, QComboBox, QPushButton,
#     QTabWidget, QWidget, QGroupBox, QTextEdit, QTableWidget, QTableWidgetItem, QProgressBar, QCheckBox
# )
# from PySide6.QtCore import Signal, Qt, QThread

# class CalculationWorker(QThread):
#     calculation_finished = Signal(np.ndarray, str, str)
#     calculation_error = Signal(str)
#     progress_updated = Signal(int)

#     def __init__(self, expression, layer_map, variable_map, output_name, parent_layer):
#         super().__init__()
#         self.expression = expression
#         self.layer_map = layer_map
#         self.variable_map = variable_map
#         self.output_name = output_name
#         self.parent_layer = parent_layer

#     def run(self):
#         try:
#             local_namespace = {'np': np}
#             # Add mathematical functions
#             math_functions = {
#                 'sin': np.sin, 'cos': np.cos, 'tan': np.tan, 'asin': np.arcsin,
#                 'acos': np.arccos, 'atan': np.arctan, 'sqrt': np.sqrt,
#                 'exp': np.exp, 'log': np.log, 'log10': np.log10, 'abs': np.abs,
#                 'ceil': np.ceil, 'floor': np.floor, 'round': np.round,
#                 'min': np.minimum, 'max': np.maximum, 'mean': np.mean,
#                 'median': np.median, 'std': np.std, 'var': np.var
#             }
#             local_namespace.update(math_functions)
#             self.progress_updated.emit(20)

#             for identifier, var_name in self.variable_map.items():
#                 layer_name, band_id = identifier.split('@')
#                 band_index = int(band_id[1:]) - 1
#                 layer_data = self.layer_map[layer_name]['data']
#                 local_namespace[var_name] = layer_data[:, :, band_index].astype(np.float64)

#             self.progress_updated.emit(50)
#             processed_expression = self.expression
#             for identifier, var_name in self.variable_map.items():
#                 processed_expression = processed_expression.replace(f'"{identifier}"', var_name)

#             self.progress_updated.emit(70)
#             with np.errstate(divide='ignore', invalid='ignore'):
#                 result_array = eval(processed_expression, {"__builtins__": {}}, local_namespace)

#             if np.isscalar(result_array):
#                 result_array = np.full_like(list(local_namespace.values())[0], result_array)

#             result_array = np.nan_to_num(result_array, nan=0.0, posinf=0.0, neginf=0.0)
#             if result_array.ndim == 2:
#                 result_array = result_array[:, :, np.newaxis]

#             self.progress_updated.emit(100)
#             self.calculation_finished.emit(result_array, self.output_name, self.parent_layer)
#         except Exception as e:
#             self.calculation_error.emit(str(e))

# class RasterCalculatorWindow(QDialog):
#     calculation_complete = Signal(np.ndarray, str, str)

#     def __init__(self, all_layers: list, parent=None):
#         super().__init__(parent)
#         self.setWindowTitle("Advanced Raster Calculator")
#         self.setMinimumSize(900, 700)
#         self.all_layers = all_layers if all_layers is not None else []
#         self.layer_map = {layer['name']: layer for layer in self.all_layers}
#         self.calculation_worker = None
#         self._setup_ui()
#         self._connect_signals()
#         self._populate_presets()
#         if self.all_layers:
#             self._update_band_list(0)
#             self._update_layer_info()

#     def _setup_ui(self):
#         main_layout = QVBoxLayout(self)
#         self.tab_widget = QTabWidget()
#         main_layout.addWidget(self.tab_widget)
#         # Calculator Tab
#         calc_tab = QWidget()
#         self.tab_widget.addTab(calc_tab, "Calculator")
#         self._setup_calculator_tab(calc_tab)
#         # Functions Tab
#         func_tab = QWidget()
#         self.tab_widget.addTab(func_tab, "Functions")
#         self._setup_functions_tab(func_tab)
#         # Statistics Tab
#         stats_tab = QWidget()
#         self.tab_widget.addTab(stats_tab, "Statistics")
#         self._setup_statistics_tab(stats_tab)
#         # Progress bar and Buttons
#         self.progress_bar = QProgressBar()
#         self.progress_bar.setVisible(False)
#         main_layout.addWidget(self.progress_bar)
#         self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Close)
#         self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Execute")
#         main_layout.addWidget(self.button_box)

#     def _setup_calculator_tab(self, parent):
#         layout = QHBoxLayout(parent)
#         left_panel = QVBoxLayout()
#         # Layer selection
#         layer_group = QGroupBox("Raster Layers")
#         layer_layout = QVBoxLayout(layer_group)
#         self.layer_selector = QComboBox()
#         self.layer_selector.addItems([layer['name'] for layer in self.all_layers])
#         layer_layout.addWidget(QLabel("Select Layer:"))
#         layer_layout.addWidget(self.layer_selector)
#         self.layer_info = QLabel("No layer selected")
#         layer_layout.addWidget(QLabel("Layer Information:"))
#         layer_layout.addWidget(self.layer_info)
#         left_panel.addWidget(layer_group)
#         # Bands list
#         bands_group = QGroupBox("Available Bands")
#         bands_layout = QVBoxLayout(bands_group)
#         self.bands_list = QListWidget()
#         bands_layout.addWidget(QLabel("Double-click to add to expression:"))
#         bands_layout.addWidget(self.bands_list)
#         left_panel.addWidget(bands_group)
#         # Right panel
#         right_panel = QVBoxLayout()
#         expr_group = QGroupBox("Expression")
#         expr_layout = QVBoxLayout(expr_group)
#         self.expression_edit = QTextEdit()
#         self.expression_edit.setMaximumHeight(100)
#         self.expression_edit.setPlaceholderText('Enter your raster calculation expression...')
#         expr_layout.addWidget(self.expression_edit)
#         # Preset expressions
#         preset_layout = QHBoxLayout()
#         preset_layout.addWidget(QLabel("Presets:"))
#         self.preset_combo = QComboBox()
#         preset_layout.addWidget(self.preset_combo)
#         self.apply_preset_btn = QPushButton("Apply")
#         preset_layout.addWidget(self.apply_preset_btn)
#         expr_layout.addLayout(preset_layout)
#         right_panel.addWidget(expr_group)
#         # Operators panel
#         operators_group = QGroupBox("Operators")
#         operators_layout = QGridLayout(operators_group)
#         basic_ops = ['+', '-', '*', '/', '(', ')', '^', '%']
#         for i, op in enumerate(basic_ops):
#             btn = QPushButton(op)
#             btn.clicked.connect(lambda checked, o=op: self._add_to_expression(o))
#             operators_layout.addWidget(btn, 0, i)
#         comp_ops = ['==', '!=', '<', '>', '<=', '>=']
#         for i, op in enumerate(comp_ops):
#             btn = QPushButton(op)
#             btn.clicked.connect(lambda checked, o=op: self._add_to_expression(o))
#             operators_layout.addWidget(btn, 1, i)
#         logic_ops = ['&', '|', '~', 'and', 'or', 'not']
#         for i, op in enumerate(logic_ops):
#             btn = QPushButton(op)
#             btn.clicked.connect(lambda checked, o=op: self._add_to_expression(f' {o} '))
#             operators_layout.addWidget(btn, 2, i)
#         right_panel.addWidget(operators_group)
#         # Output settings
#         output_group = QGroupBox("Output Settings")
#         output_layout = QVBoxLayout(output_group)
#         self.output_name_edit = QLineEdit()
#         self.output_name_edit.setPlaceholderText('Enter output layer name...')
#         output_layout.addWidget(QLabel("Output Layer Name:"))
#         output_layout.addWidget(self.output_name_edit)
#         options_layout = QHBoxLayout()
#         self.add_to_project_cb = QCheckBox("Add result to project")
#         self.add_to_project_cb.setChecked(True)
#         options_layout.addWidget(self.add_to_project_cb)
#         self.create_virtual_cb = QCheckBox("Create virtual raster")
#         options_layout.addWidget(self.create_virtual_cb)
#         output_layout.addLayout(options_layout)
#         right_panel.addWidget(output_group)
#         layout.addLayout(left_panel, 1)
#         layout.addLayout(right_panel, 2)

#     def _setup_functions_tab(self, parent):
#         layout = QVBoxLayout(parent)
#         math_group = QGroupBox("Mathematical Functions")
#         math_layout = QGridLayout(math_group)
#         math_functions = [
#             ('sin', 'sin()'), ('cos', 'cos()'), ('tan', 'tan()'),
#             ('asin', 'asin()'), ('acos', 'acos()'), ('atan', 'atan()'),
#             ('sqrt', 'sqrt()'), ('exp', 'exp()'), ('log', 'log()'),
#             ('log10', 'log10()'), ('abs', 'abs()'), ('ceil', 'ceil()'),
#             ('floor', 'floor()'), ('round', 'round()'), ('power', '**')
#         ]
#         for i, (name, func) in enumerate(math_functions):
#             btn = QPushButton(name)
#             btn.clicked.connect(lambda checked, f=func: self._add_function_to_expression(f))
#             math_layout.addWidget(btn, i // 3, i % 3)
#         layout.addWidget(math_group)
#         cond_group = QGroupBox("Conditional Functions")
#         cond_layout = QVBoxLayout(cond_group)
#         if_layout = QHBoxLayout()
#         if_layout.addWidget(QLabel("IF Statement:"))
#         self.if_condition = QLineEdit()
#         self.if_condition.setPlaceholderText("condition")
#         self.if_true = QLineEdit()
#         self.if_true.setPlaceholderText("value if true")
#         self.if_false = QLineEdit()
#         self.if_false.setPlaceholderText("value if false")
#         if_layout.addWidget(self.if_condition)
#         if_layout.addWidget(QLabel("?"))
#         if_layout.addWidget(self.if_true)
#         if_layout.addWidget(QLabel(":"))
#         if_layout.addWidget(self.if_false)
#         build_if_btn = QPushButton("Build IF")
#         build_if_btn.clicked.connect(self._build_if_statement)
#         if_layout.addWidget(build_if_btn)
#         cond_layout.addLayout(if_layout)
#         layout.addWidget(cond_group)

#     def _setup_statistics_tab(self, parent):
#         layout = QVBoxLayout(parent)
#         stats_group = QGroupBox("Statistical Functions")
#         stats_layout = QGridLayout(stats_group)
#         stat_functions = [
#             ('min', 'np.minimum'), ('max', 'np.maximum'), ('mean', 'np.mean'),
#             ('median', 'np.median'), ('std', 'np.std'), ('var', 'np.var'),
#             ('sum', 'np.sum'), ('percentile', 'np.percentile')
#         ]
#         for i, (name, func) in enumerate(stat_functions):
#             btn = QPushButton(name)
#             btn.clicked.connect(lambda checked, f=func: self._add_function_to_expression(f + '()'))
#             stats_layout.addWidget(btn, i // 3, i % 3)
#         layout.addWidget(stats_group)
#         band_stats_group = QGroupBox("Band Statistics")
#         band_stats_layout = QVBoxLayout(band_stats_group)
#         self.stats_table = QTableWidget(0, 4)
#         self.stats_table.setHorizontalHeaderLabels(['Band', 'Min', 'Max', 'Mean'])
#         band_stats_layout.addWidget(self.stats_table)
#         refresh_stats_btn = QPushButton("Refresh Statistics")
#         refresh_stats_btn.clicked.connect(self._refresh_band_statistics)
#         band_stats_layout.addWidget(refresh_stats_btn)
#         layout.addWidget(band_stats_group)

#     def _connect_signals(self):
#         self.layer_selector.currentIndexChanged.connect(self._update_band_list)
#         self.layer_selector.currentIndexChanged.connect(self._update_layer_info)
#         self.bands_list.itemDoubleClicked.connect(self._add_band_to_expression)
#         self.apply_preset_btn.clicked.connect(self._apply_preset)
#         self.button_box.accepted.connect(self._execute_calculation)
#         self.button_box.rejected.connect(self.reject)

#     def _populate_presets(self):
#         presets = {
#             'NDVI': '("Layer@b4" - "Layer@b3") / ("Layer@b4" + "Layer@b3")',
#             'NDWI': '("Layer@b2" - "Layer@b4") / ("Layer@b2" + "Layer@b4")',
#             'EVI': '2.5 * (("Layer@b4" - "Layer@b3") / ("Layer@b4" + 6 * "Layer@b3" - 7.5 * "Layer@b1" + 1))',
#             'Band Ratio': '"Layer@b1" / "Layer@b2"',
#             'Band Difference': '"Layer@b1" - "Layer@b2"',
#             'Normalized Difference': '("Layer@b1" - "Layer@b2") / ("Layer@b1" + "Layer@b2")'
#         }
#         self.preset_combo.addItem("Select preset...")
#         for name, expr in presets.items():
#             self.preset_combo.addItem(name)
#         self.presets = presets

#     def _update_band_list(self, index: int):
#         if not self.all_layers:
#             return
#         self.bands_list.clear()
#         selected_layer = self.all_layers[index]
#         band_names = selected_layer.get("band_names", [])
#         self.bands_list.addItems([f'b{i+1}: {name}' for i, name in enumerate(band_names)])

#     def _update_layer_info(self):
#         if not self.all_layers:
#             return
#         index = self.layer_selector.currentIndex()
#         layer = self.all_layers[index]
#         info_text = f"Name: {layer['name']}\n"
#         info_text += f"Dimensions: {layer['data'].shape}\n"
#         info_text += f"Data Type: {layer['data'].dtype}\n"
#         info_text += f"Bands: {layer['data'].shape[2]}"
#         self.layer_info.setText(info_text)

#     def _add_band_to_expression(self, item):
#         layer_name = self.layer_selector.currentText()
#         band_id = item.text().split(':')[0]
#         formatted_band = f'"{layer_name}@{band_id}"'
#         cursor = self.expression_edit.textCursor()
#         cursor.insertText(formatted_band)

#     def _add_to_expression(self, text):
#         cursor = self.expression_edit.textCursor()
#         cursor.insertText(text)

#     def _add_function_to_expression(self, func):
#         cursor = self.expression_edit.textCursor()
#         if '()' in func:
#             cursor.insertText(func[:-1])
#             cursor.insertText(')')
#             cursor.movePosition(cursor.MoveOperation.Left)
#             self.expression_edit.setTextCursor(cursor)
#         else:
#             cursor.insertText(func)

#     def _build_if_statement(self):
#         condition = self.if_condition.text()
#         true_val = self.if_true.text()
#         false_val = self.if_false.text()
#         if condition and true_val and false_val:
#             if_statement = f"np.where({condition}, {true_val}, {false_val})"
#             cursor = self.expression_edit.textCursor()
#             cursor.insertText(if_statement)

#     def _apply_preset(self):
#         preset_name = self.preset_combo.currentText()
#         if preset_name in self.presets:
#             self.expression_edit.setPlainText(self.presets[preset_name])

#     def _refresh_band_statistics(self):
#         if not self.all_layers:
#             return
#         index = self.layer_selector.currentIndex()
#         layer = self.all_layers[index]
#         data = layer['data']
#         self.stats_table.setRowCount(data.shape[2])
#         for i in range(data.shape[2]):
#             band_data = data[:, :, i]
#             band_data = band_data[~np.isnan(band_data)]
#             if len(band_data) > 0:
#                 min_val = np.min(band_data)
#                 max_val = np.max(band_data)
#                 mean_val = np.mean(band_data)
#                 self.stats_table.setItem(i, 0, QTableWidgetItem(f"Band {i+1}"))
#                 self.stats_table.setItem(i, 1, QTableWidgetItem(f"{min_val:.4f}"))
#                 self.stats_table.setItem(i, 2, QTableWidgetItem(f"{max_val:.4f}"))
#                 self.stats_table.setItem(i, 3, QTableWidgetItem(f"{mean_val:.4f}"))

#     def _execute_calculation(self):
#         expression = self.expression_edit.toPlainText().strip()
#         if not expression:
#             QMessageBox.warning(self, "Input Error", "Expression cannot be empty.")
#             return
#         try:
#             band_identifiers = set(re.findall(r'"([^"]+@b\d+)"', expression))
#             if not band_identifiers:
#                 QMessageBox.warning(self, "Input Error", "No valid band identifiers found in expression.")
#                 return
#             variable_map = {}
#             for i, identifier in enumerate(band_identifiers):
#                 layer_name, band_id = identifier.split('@')
#                 if layer_name not in self.layer_map:
#                     raise NameError(f"Layer '{layer_name}' not found.")
#                 band_index = int(band_id[1:]) - 1
#                 layer_data = self.layer_map[layer_name]['data']
#                 if not (0 <= band_index < layer_data.shape[2]):
#                     raise IndexError(f"Band index {band_index+1} is out of bounds for layer '{layer_name}'.")
#                 variable_map[identifier] = f'var_{i}'
#             output_name = self.output_name_edit.text().strip()
#             if not output_name:
#                 output_name = "Calculated_Raster"
#             parent_layer = list(band_identifiers)[0].split('@')[0]
#             self.calculation_worker = CalculationWorker(
#                 expression, self.layer_map, variable_map, output_name, parent_layer
#             )
#             self.calculation_worker.calculation_finished.connect(self._on_calculation_finished)
#             self.calculation_worker.calculation_error.connect(self._on_calculation_error)
#             self.calculation_worker.progress_updated.connect(self._on_progress_updated)
#             self.progress_bar.setVisible(True)
#             self.progress_bar.setValue(0)
#             self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
#             self.calculation_worker.start()
#         except Exception as e:
#             QMessageBox.critical(self, "Calculation Error", f"An error occurred:\n{e}")

#     def _on_calculation_finished(self, result_array, output_name, parent_layer):
#         self.progress_bar.setVisible(False)
#         self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
#         self.calculation_complete.emit(result_array, output_name, parent_layer)
#         if self.add_to_project_cb.isChecked():
#             QMessageBox.information(self, "Success", f"Calculation completed successfully!\nOutput: {output_name}")
#         self.accept()

#     def _on_calculation_error(self, error_message):
#         self.progress_bar.setVisible(False)
#         self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
#         QMessageBox.critical(self, "Calculation Error", f"An error occurred:\n{error_message}")

#     def _on_progress_updated(self, value):
#         self.progress_bar.setValue(value)


























































# import re
# import numpy as np
# from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLineEdit, QListWidget, QGridLayout, 
#                              QApplication, QMessageBox, QLabel, QDialogButtonBox, QComboBox)

# from PySide6.QtCore import Signal


# class RasterCalculatorWindow(QDialog):
#     """
#     A dialog for performing multi-layer raster calculations.
#     It is aware of all layers loaded in the main application.
#     """
#     calculation_complete = Signal(np.ndarray, str,str )

#     def __init__(self, all_layers: list, parent=None):
#         super().__init__(parent)
#         self.setWindowTitle("Raster Calculator")
#         self.setMinimumSize(500, 450)
#         self.setStyleSheet("background-color: #F0F0F0;")

#         # Gracefully handle the case where all_layers might be None or empty
#         self.all_layers = all_layers if all_layers is not None else []
#         self.layer_map = {layer['name']: layer for layer in self.all_layers}       

#         self.main_layout = QVBoxLayout(self)
#         self._setup_ui()
#         self._connect_signals()
        
#         # Initially populate the band list with the first layer's bands
#         if self.all_layers:
#             self._update_band_list(0)
#         else:
#             # If no layers are loaded, disable widgets and show a message
#             self.layer_selector.setEnabled(False)
#             self.bands_list.setEnabled(False)
#             self.expression_edit.setEnabled(False)
#             self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            
#             self.expression_edit.setPlaceholderText("Please load a raster layer to begin.")
#             self.bands_list.addItem("No layers loaded")


#     def _setup_ui(self):
#         """Builds the user interface."""
#         # 1. Layer Selection Dropdown
#         self.main_layout.addWidget(QLabel("Select Layer to View Bands:"))
#         self.layer_selector = QComboBox()
#         self.layer_selector.addItems([layer['name'] for layer in self.all_layers])
#         self.main_layout.addWidget(self.layer_selector)

#         # 2. Band List (now dynamically updated)
#         self.main_layout.addWidget(QLabel("Available Bands (Double-click to add):"))
#         self.bands_list = QListWidget()
#         self.main_layout.addWidget(self.bands_list)

#         # 3. Taking input for layer name .i.e NDVI or any other name
#         self.main_layout.addWidget(QLabel("Output Layer Name (optional):"))
#         self.output_name_edit = QLineEdit()
#         self.output_name_edit.setPlaceholderText('e.g., NDVI')
#         self.main_layout.addWidget(self.output_name_edit)

#         # 4. Expression Editor
#         self.main_layout.addWidget(QLabel("Raster Calculation Expression:"))
#         self.expression_edit = QLineEdit()
#         self.expression_edit.setPlaceholderText('e.g., ("MyLayer@Band2" - "MyLayer@Band1") / ("MyLayer@Band2" + "MyLayer@Band1")')
#         self.main_layout.addWidget(self.expression_edit)

#         # 4. Standard Dialog Buttons
#         self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Close)
#         self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Execute")
#         self.main_layout.addWidget(self.button_box)

#     def _connect_signals(self):
#         """Connects widget signals to corresponding slots."""
#         self.layer_selector.currentIndexChanged.connect(self._update_band_list)
#         self.bands_list.itemDoubleClicked.connect(self._add_band_to_expression)
#         self.button_box.accepted.connect(self._execute_calculation)
#         self.button_box.rejected.connect(self.reject)

#     def _update_band_list(self, index: int):
#         """Clears and repopulates the band list when a new layer is selected."""
#         self.bands_list.clear()
#         selected_layer = self.all_layers[index]
#         band_names = selected_layer.get("band_names", [])
#         self.bands_list.addItems([f'b{i+1}: {name}' for i, name in enumerate(band_names)])

#     def _add_band_to_expression(self, item):
#         """Formats the band identifier and adds it to the expression."""
#         layer_name = self.layer_selector.currentText()
#         print("Selected layer for band addition:", layer_name)

#         # Extract 'b1', 'b2', etc., from the list item text
#         band_id = item.text().split(':')[0]
        
#         # Format as "Layer Name@b1" to ensure it's unique
#         formatted_band = f'"{layer_name}@{band_id}"'
#         self.expression_edit.insert(f' {formatted_band} ')
#         self.expression_edit.setFocus()

#     def _execute_calculation(self):
#         """Parses the multi-layer expression and computes the result."""
#         expression = self.expression_edit.text()
#         if not expression:
#             QMessageBox.warning(self, "Input Error", "Expression cannot be empty.")
#             return

#         try:
#             # --- START OF NEW CODE ---
#             # 1. Find the first layer referenced in the expression to use as the parent.
#             #printing the parent layer name
#             print("Expression entered:", expression)
#             # --- END OF NEW CODE ---

#             local_namespace = {'np': np}
#             variable_map = {}
            
#             # Find all unique band identifiers like "Layer Name@b1"
#             band_identifiers = set(re.findall(r'"([^"]+@b\d+)"', expression))
#             print(band_identifiers)

#             for i, identifier in enumerate(band_identifiers):
#                 layer_name, band_id = identifier.split('@')
#                 band_index = int(band_id[1:]) - 1 # Convert 'b1' to index 0
#                 self.layer_name = layer_name

#                 if layer_name not in self.layer_map:
#                     raise NameError(f"Layer '{layer_name}' not found.")
                
#                 layer_data = self.layer_map[layer_name]['data']
#                 if not (0 <= band_index < layer_data.shape[2]):
#                     raise IndexError(f"Band index {band_index+1} is out of bounds for layer '{layer_name}'.")

#                 # Create a safe variable name like 'var_0', 'var_1', etc.
#                 var_name = f'var_{i}'
#                 variable_map[identifier] = var_name
#                 local_namespace[var_name] = layer_data[:, :, band_index].astype(np.float32)

#             # Replace the long identifiers in the expression with the safe variable names
#             processed_expression = expression
#             for identifier, var_name in variable_map.items():
#                 processed_expression = processed_expression.replace(f'"{identifier}"', var_name)
            
#             # Evaluate the processed expression
#             with np.errstate(divide='ignore', invalid='ignore'):
#                 result_array = eval(processed_expression, {"__builtins__": {}}, local_namespace)
            
#             result_array = np.nan_to_num(result_array, nan=0.0, posinf=0.0, neginf=0.0)
            
#             if result_array.ndim == 2:
#                 result_array = result_array[:, :, np.newaxis]

#             self.output_layer_name = self.output_name_edit.text().strip()
#             if not self.output_layer_name:
#                 self.output_layer_name = "Default Name"

#             # output_layer_name = f"Result: {expression[:50]}..."
#             self.calculation_complete.emit(result_array, self.output_layer_name,self.layer_name)
#             self.accept()

#         except Exception as e:
#             QMessageBox.critical(self, "Calculation Error", f"An error occurred:\n{e}")