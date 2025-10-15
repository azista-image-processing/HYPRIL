from importlib import metadata
import os
import sys
import time
import logging
import numpy as np
from osgeo import gdal
import xarray as xr
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QFileDialog,
                               QWidget, QDialog, QListWidget, QLabel, 
                               QDialogButtonBox, QAbstractItemView)
from typing import Optional, Tuple, List, Dict


# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- GDAL Exception Handling ---
gdal.UseExceptions()


class SubdatasetSelectionDialog(QDialog):
    """
    A custom dialog window that displays a list of subdatasets found in a file
    and allows the user to select one or more to load.
    """
    def __init__(self, subdatasets: Dict[str, str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Subdatasets to Load")
        self.setMinimumWidth(500)
        self.subdatasets_map = {}

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("The selected file contains multiple datasets.\nPlease select which ones you want to load:"))

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        for i in range(1, (len(subdatasets) // 2) + 1):
            name_key = f'SUBDATASET_{i}_NAME'
            desc_key = f'SUBDATASET_{i}_DESC'
            if name_key in subdatasets and desc_key in subdatasets:
                path = subdatasets[name_key]
                desc = subdatasets[desc_key]
                display_text = f"{i}: {desc}" 
                self.list_widget.addItem(display_text)
                self.subdatasets_map[display_text] = path

        layout.addWidget(self.list_widget)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_selected_paths(self) -> List[str]:
        selected_paths = []
        for item in self.list_widget.selectedItems():
            selected_paths.append(self.subdatasets_map[item.text()])
        return selected_paths


class HyperspectralImageLoader:
    """
    A robust class to load and encapsulate hyperspectral image data using GDAL.
    Supports ENVI, GeoTIFF, HDF5, and NetCDF formats with interactive subdataset handling.
    """
    def __init__(self, file_path: Optional[str] = None, parent=None):
        self.parent = parent
        self._initial_file_path = file_path
        self.file_path = None
        self.image_data = None
        self.metadata = {}
        self.band_names = []
        self.wavelengths = []
        self.wavelength_units = "Unknown"
        self.geotransform = None
        self.projection = ""
        self.is_loaded = False
        self._dataset = None

    @classmethod
    def open_file_dialog(cls, parent=None) -> List['HyperspectralImageLoader']:
        """
        Opens a file dialog. If the file has subdatasets, it prompts the user
        to select which ones to load, returning each as a separate object in a list.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            parent,
            "Open Hyperspectral Image",
            "",
            "All Supported Files (*.hdr *.tif *.tiff *.h5 *.hdf *.nc *.jp2);;"
            "ENVI Files (*.hdr);;" 
            "GeoTIFF Files (*.tif *.tiff);;"
            "Sentinel-2 Files (*.jp2);;"
            "HDF/NetCDF Files (*.h5 *.hdf *.nc);;"
        )
        print("file_path in open_file_dialog:", file_path)
        if not file_path:
            logger.info("No file selected by the user.")
            return []
        #making file_path global to be used in ahead

        paths_to_load = []

        try:
            if file_path.lower().endswith('.hdr'):
                logger.info("HDR file detected, searching for corresponding data file.")
                real_file_path = cls(file_path=file_path)._find_data_file()
            else:
                real_file_path = file_path
            temp_dataset = gdal.Open(real_file_path, gdal.GA_ReadOnly)
            if temp_dataset is None:
                raise IOError("GDAL could not open the initial file path.")
            subdatasets = temp_dataset.GetMetadata('SUBDATASETS')
            temp_dataset = None

            if subdatasets:
                logger.info(f"Found {len(subdatasets) // 2} subdatasets. Prompting user.")
                dialog = SubdatasetSelectionDialog(subdatasets, parent)
                if dialog.exec():
                    paths_to_load = dialog.get_selected_paths()
                    if not paths_to_load:
                        logger.info("User did not select any subdatasets.")
                else:
                    logger.info("User cancelled subdataset selection.")
            else:
                paths_to_load.append(file_path)

        except Exception as e:
            logger.error(f"Error during subdataset check for {file_path}: {e}", exc_info=True)
            return []
        
        loaded_images = []
        for i, path in enumerate(paths_to_load):
            logger.info(f"Loading item {i+1}/{len(paths_to_load)}...")
            loader = cls(file_path=path, parent=parent)
            if loader.load():
                loaded_images.append(loader)
            else:
                logger.warning(f"Failed to load item: {path}")

        return loaded_images

    def load(self, chunk_size: Optional[Tuple[int, int]] = None) -> bool:
        try:
            start_time = time.time()
            
            self.file_path = self._find_data_file()
            if not self.file_path: return False

            logger.info(f"Attempting to load: {self.file_path}")

            self._dataset = self._read_gdal_dataset()
            self._read_image_data(chunk_size)
            self._parse_metadata()
            
            self.geotransform = self._dataset.GetGeoTransform()
            # print(f"Geotransform from image_loader: {self.geotransform}")
            self.projection = self._dataset.GetProjection()
            # print(f"Projection from image_loader: {self.projection}")

            if self.image_data is None or self.image_data.ndim != 3 or self.image_data.shape[2] < 1:
                raise ValueError("Loaded data is not a valid 3D hyperspectral cube.")

            self.is_loaded = True
            duration = time.time() - start_time

            self.file_name = os.path.splitext(os.path.basename(str(self.file_path)))[0]

            logger.info(f"Successfully loaded image in {duration:.2f} seconds.")
            logger.info(f"Image dimensions (rows, cols, bands): {self.image_data.shape}")
            return True

        except Exception as e:
            logger.error(f"Failed to load image '{self._initial_file_path}': {e}", exc_info=True)
            return False
        finally:
            self.close()

    def _find_data_file(self) -> Optional[str]:
        if not self._initial_file_path: return None
        if not self._initial_file_path.lower().endswith('.hdr'):
            return self._initial_file_path

        folder = os.path.dirname(self._initial_file_path)
        base_name = os.path.splitext(os.path.basename(self._initial_file_path))[0]
        files_lower_map = {f.lower(): f for f in os.listdir(folder)}

        for ext in ['', '.bil', '.bsq', '.dat', '.img', '.hdf', '.h5', '.nc', '.l1r', '.int', '.raw']:
            target_file_lower = (base_name + ext).lower()
            if target_file_lower in files_lower_map:
                original_filename = files_lower_map[target_file_lower]
                potential_file = os.path.join(folder, original_filename)
                if potential_file.lower() != self._initial_file_path.lower():
                    logger.info(f"Found corresponding data file: {potential_file}")
                    return potential_file
        raise FileNotFoundError(f"No corresponding data file found for {self._initial_file_path}")

    def _read_gdal_dataset(self) -> gdal.Dataset:
        dataset = gdal.Open(self.file_path, gdal.GA_ReadOnly)
        if dataset is None:
            raise ValueError(f"GDAL could not open resource: {self.file_path}")
        return dataset

    def _read_image_data(self, chunk_size: Optional[Tuple[int, int]] = None):
        logger.info("Reading pixel data...")
        start = time.time()
        if chunk_size:
            rows, cols = chunk_size
            xsize, ysize = self._dataset.RasterXSize, self._dataset.RasterYSize
            
            bands = self._dataset.RasterCount
            self.image_data = np.zeros((ysize, xsize, bands), dtype=np.float32)
            for y in range(0, ysize, rows):
                for x in range(0, xsize, cols):
                    chunk_rows = min(rows, ysize - y)
                    chunk_cols = min(cols, xsize - x)
                    chunk = self._dataset.ReadAsArray(x, y, chunk_cols, chunk_rows)
                    if chunk.ndim == 2: chunk = chunk[:, :, np.newaxis]
                    self.image_data[y:y+chunk_rows, x:x+chunk_cols, :] = np.moveaxis(chunk, 0, -1)
        else:
            image_data_gdal = self._dataset.ReadAsArray().astype(np.float32)
             # Count problematic values
            zero_count = np.sum(image_data_gdal == 0)
            negative_count = np.sum(image_data_gdal < 0)
            nan_count = np.sum(np.isnan(image_data_gdal))
            total_pixels = image_data_gdal.size
            
            print(f"Data quality assessment:")
            print(f"  Total pixels: {total_pixels}")
            print(f"  Zero values: {zero_count} ({zero_count/total_pixels*100:.2f}%)")
            print(f"  Negative values: {negative_count} ({negative_count/total_pixels*100:.2f}%)")
            print(f"  NaN values: {nan_count} ({nan_count/total_pixels*100:.2f}%)")
            # eps = 1e-03
            # if zero_count > 0 or negative_count > 0 or nan_count > 0:
            #     # Create comprehensive mask for all problematic values
            #     problematic_mask = (image_data_gdal == 0) | (image_data_gdal < 0) | np.isnan(image_data_gdal)
                
            #     # Apply eps replacement
            #     image_data_gdal[problematic_mask] = eps
                
            #     # Verify cleaning
            #     verification_zero = np.sum(image_data_gdal == 0)
            #     verification_negative = np.sum(image_data_gdal < 0)
            #     verification_nan = np.sum(np.isnan(image_data_gdal))
                
            #     logging.info(f"Data cleaning completed: {zero_count} zeros, {negative_count} negatives, {nan_count} NaNs replaced with {eps}")
            #     logging.info(f"Post-cleaning verification: {verification_zero} zeros, {verification_negative} negatives, {verification_nan} NaNs remaining")
                
            #     if verification_zero > 0 or verification_negative > 0 or verification_nan > 0:
            #         logging.warning("Some problematic values may still remain after cleaning!")
            if image_data_gdal.ndim == 3:
                self.image_data = np.moveaxis(image_data_gdal, 0, -1).astype(np.float32)
            elif image_data_gdal.ndim == 2:
                self.image_data = image_data_gdal[:, :, np.newaxis].astype(np.float32)
            else:
                raise ValueError(f"Unsupported image dimension: {image_data_gdal.ndim}")
        end = time.time()
        logger.info(f"Image data read in {end - start:.2f} seconds.")


    def _subsample_for_display(self, max_display_size: int = 2048) -> np.ndarray:
        """Subsample large images for faster display without loading full resolution"""
        if self.image_data is None:
            return None
        
        rows, cols = self.image_data.shape[:2]
        
        if rows <= max_display_size and cols <= max_display_size:
            return self.image_data
        
        # Calculate subsampling factor
        factor = max(rows // max_display_size, cols // max_display_size) + 1
        
        # Subsample spatially but keep all bands
        return self.image_data[::factor, ::factor, :]
    

    def fast_percentile_normalization(self, band_data: np.ndarray, sample_size: int = 10000) -> tuple:
        """Fast percentile calculation using sampling for large arrays"""
        if band_data.size <= sample_size:
            return np.percentile(band_data, [2, 98])
        
        # Random sampling for large arrays
        flat_data = band_data.flatten()
        sample_indices = np.random.choice(flat_data.size, sample_size, replace=False)
        sample_data = flat_data[sample_indices]
        
        return np.percentile(sample_data, [2, 98])


    # 
    def _parse_metadata(self):

        wavelengths = []
        print("file_path in parse_metadata:", self.file_path)
        if self.file_path and self.file_path.lower().endswith('.hdr'):
            with open(self.file_path, "r") as f:
                text = f.read()
                # Extract the block inside { }
                import re
                match = re.search(r"wavelength\s*=\s*{([^}]*)}", text, re.IGNORECASE | re.DOTALL)
                if match:
                    wl_str = match.group(1)
                    self.wavelengths = [float(w) for w in wl_str.replace(",", " ").split()]
                    # print("Wavelengths:", self.wavelengths)   
                    # print("Total bands:", len(self.wavelengths))
                else:
                    print("No wavelength found")


        self.metadata = self._dataset.GetMetadata("ENVI") or self._dataset.GetMetadata()
        if "RasterXSize" not in self.metadata:
            self.metadata["RasterXSize"] = self._dataset.RasterXSize

        if "Wavelengths" not in self.metadata:
            self.metadata["Wavelengths"] = self.wavelengths

        if "RasterYSize" not in self.metadata:
            self.metadata["RasterYSize"] = self._dataset.RasterYSize

        if "RasterCount" not in self.metadata:
            self.metadata["RasterCount"] = self._dataset.RasterCount

        if "Driver" not in self.metadata:
            self.metadata["Driver"] = self._dataset.GetDriver().ShortName

        if "Projection" not in self.metadata:
            self.metadata["Projection"] = self._dataset.GetProjection()

        if "GeoTransform" not in self.metadata:
            self.metadata["GeoTransform"] = (
                self._dataset.GetGeoTransform() if self._dataset.GetGeoTransform() else None
            )
        if "Data_type" not in self.metadata:
            band = self._dataset.GetRasterBand(1)
            dtype_code = band.DataType
            dtype_name = gdal.GetDataTypeName(dtype_code)
            self.metadata["Data_type"] = dtype_name


        bands = self._dataset.RasterCount
        if 'band names' not in self.metadata:
            try:
                band_names_str = self.metadata['band names']
                self.band_names = [name.strip() for name in band_names_str.strip('{} \n').split(',')]
                if len(self.band_names) != bands: self.band_names = []
            except Exception: self.band_names = []
        if not self.band_names and 'wavelength' in self.metadata:
            try:
                self.wavelength_units = self.metadata.get('wavelength units', 'nm')
                # wl_str = self.metadata['wavelength'].strip('{} \n')
                # self.wavelengths = [float(w) for w in (wl_str.split(',') if ',' in wl_str else wl_str.split()) if w.strip()]
                if len(self.wavelengths) == bands:
                    self.band_names = [f"Band {i+1} ({w:.3f} {self.wavelength_units})" for i, w in enumerate(self.wavelengths)]
            except Exception: pass

        if not self.band_names:
            self.band_names = [f"Band {i+1}" for i in range(bands)]

        # print(f"Metadata from image_loader: {self.metadata}")

        

    def close(self):
        if self._dataset:
            self._dataset = None
            logger.info(f"Closed dataset for {self.file_path} but retained image data in memory.")

    def __repr__(self):
        if self.is_loaded:
            shape_str = str(self.image_data.shape)
            base_file = self._initial_file_path.split(':')[1].strip('"') if ':' in self._initial_file_path else self._initial_file_path
            return f"<HyperspectralImageLoader: {os.path.basename(base_file)} {shape_str}>"
        return f"<HyperspectralImageLoader: Not loaded>"



