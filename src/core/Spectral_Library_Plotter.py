#src/core/Spectral_Library_Plotter.py

import os
import numpy as np
from osgeo import gdal
import h5py
import netCDF4
from PySide6.QtWidgets import QFileDialog, QMainWindow, QVBoxLayout, QWidget
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import logging
from io import StringIO

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SpectralLibraryPlotter:
    """A class to handle loading and plotting of spectral libraries in various formats."""

    @staticmethod
    def plot_spectral_library(parent=None, file_path: str = None) -> None:
        """
        Load and plot a spectral library in a new window.

        Args:
            parent: Optional parent widget for QFileDialog (for GUI integration).
            file_path: Optional file path to load directly (for non-GUI usage).

        Returns:
            None: Opens a new window with the spectral library plot.
        """
        try:
            # If no file path provided, open file dialog
            if not file_path:
                if parent is None:
                    raise ValueError("Parent widget required when no file path is provided")
                file_path, _ = QFileDialog.getOpenFileName(
                    parent,
                    "Open Spectral Library",
                    "",
                    "All Supported Files (*.sli *.txt *.csv *.h5 *.hdf *.nc);;"
                    "ENVI Spectral Library (*.sli);;"
                    "Text/CSV Files (*.txt *.csv);;"
                    "HDF5 Files (*.h5 *.hdf);;"
                    "NetCDF Files (*.nc);;"
                    "All Files (*)"
                )

            if not file_path:
                logger.info("No file selected")
                return

            # Initialize variables
            wavelengths = None
            spectra = None
            spectra_names = []
            metadata = {}

            # Determine file format
            file_ext = os.path.splitext(file_path)[1].lower()

            # Load spectral library based on file format
            if file_ext == '.sli':
                # Handle ENVI Spectral Library
                folder = os.path.dirname(file_path)
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                possible_data = [
                    f for f in os.listdir(folder)
                    if os.path.splitext(f)[0] == base_name
                    and f.lower() != os.path.basename(file_path).lower()
                ]
                if not possible_data:
                    raise ValueError("No corresponding data file found for .sli")
                data_file = os.path.join(folder, possible_data[0])

                # Open with GDAL
                dataset = gdal.Open(data_file, gdal.GA_ReadOnly)
                if dataset is None:
                    raise ValueError(f"GDAL could not open file: {data_file}")

                # Read spectral data (rows = spectra, cols = wavelengths)
                spectra = dataset.ReadAsArray().astype(np.float32)
                if len(spectra.shape) != 2:
                    raise ValueError("Spectral library data is not 2D")

                # Get metadata
                metadata = dataset.GetMetadata()
                print(f"keys of metadata {list(metadata.keys)}")
                if 'wavelength' in metadata:
                    try:
                        wavelengths = metadata['wavelength'].replace('{', '').replace('}', '').split(',')
                        wavelengths = [float(w.strip()) for w in wavelengths if w.strip()]
                    except Exception as e:
                        logger.warning(f"Failed to parse wavelength metadata: {str(e)}")
                if 'spectra names' in metadata:
                    spectra_names = metadata['spectra names'].replace('{', '').replace('}', '').split(',')
                    spectra_names = [name.strip() for name in spectra_names]

                # Default wavelengths if not provided
                if wavelengths is None:
                    wavelengths = np.arange(spectra.shape[1])
                    logger.warning("No wavelength metadata found, using index as wavelength")

                # Default spectra names if not provided
                if not spectra_names:
                    spectra_names = [f"Spectrum {i + 1}" for i in range(spectra.shape[0])]

            elif file_ext in ('.txt', '.csv'):
                # --- MODIFIED BLOCK FOR TXT/CSV ---
                # This block now correctly handles text files with headers.
                try:
                    with open(file_path, 'r') as f:
                        lines = f.readlines()

                    header_lines = []
                    data_lines = []
                    # Use filename as a default name in case 'Name:' field is not found
                    temp_name = os.path.splitext(os.path.basename(file_path))[0]

                    for line in lines:
                        stripped_line = line.strip()
                        if not stripped_line:
                            continue  # Skip empty lines

                        # Attempt to identify data lines by checking if the first element is numeric
                        try:
                            float(stripped_line.split()[0])
                            data_lines.append(line)
                        except (ValueError, IndexError):
                            # Treat as a header line and parse for the spectrum name
                            header_lines.append(stripped_line)
                            if stripped_line.lower().startswith('name:'):
                                temp_name = stripped_line.split(':', 1)[1].strip()

                    if not data_lines:
                        raise ValueError("No numeric data found in the file.")

                    # Load the numeric data
                    data = np.loadtxt(StringIO(''.join(data_lines)))
                    if data.ndim != 2 or data.shape[1] < 2:
                        raise ValueError("Data must have at least two columns (wavelengths, reflectance).")
                    
                    # Assign data to the correct local variables for plotting
                    wavelengths = data[:, 0]
                    # Reshape the single spectrum into a 2D array (1 row, N columns)
                    # as the plotting loop expects an iterable of spectra.
                    spectra = data[:, 1].reshape(1, -1)
                    spectra_names = [temp_name]

                except Exception as e:
                    raise ValueError(f"Failed to read text/CSV file: {str(e)}")
                # --- END OF MODIFIED BLOCK ---

            elif file_ext in ('.h5', '.hdf'):
                # Handle HDF5 files
                with h5py.File(file_path, 'r') as f:
                    dataset_names = [key for key in f.keys() if isinstance(f[key], h5py.Dataset)]
                    if not dataset_names:
                        raise ValueError("No valid dataset found in HDF5 file")

                    spectra_data = f[dataset_names[0]][:]
                    if len(spectra_data.shape) != 2:
                        raise ValueError("HDF5 dataset is not a 2D spectral library")

                    spectra = spectra_data.astype(np.float32)
                    metadata = dict(f.attrs)

                    if 'wavelengths' in f:
                        wavelengths = np.array(f['wavelengths'][:], dtype=np.float32)
                    elif 'wavelengths' in metadata:
                        wavelengths = np.array(metadata['wavelengths'], dtype=np.float32)
                    else:
                        wavelengths = np.arange(spectra.shape[1])
                        logger.warning("No wavelengths found, using index as wavelength")

                    if 'spectra_names' in metadata:
                        spectra_names = list(metadata['spectra_names'])
                    else:
                        spectra_names = [f"Spectrum {i + 1}" for i in range(spectra.shape[0])]

            elif file_ext == '.nc':
                # Handle NetCDF files
                with netCDF4.Dataset(file_path, 'r') as f:
                    data_vars = [var for var in f.variables if len(f.variables[var].shape) == 2]
                    if not data_vars:
                        raise ValueError("No valid 2D variable found in NetCDF file")

                    spectra = f.variables[data_vars[0]][:].astype(np.float32)
                    metadata = dict(f.ncattrs())

                    if 'wavelengths' in f.variables:
                        wavelengths = f.variables['wavelengths'][:].astype(np.float32)
                    elif 'wavelengths' in metadata:
                        wavelengths = np.array(metadata['wavelengths'], dtype=np.float32)
                    else:
                        wavelengths = np.arange(spectra.shape[1])
                        logger.warning("No wavelengths found, using index as wavelength")

                    if 'spectra_names' in metadata:
                        spectra_names = list(metadata['spectra_names'])
                    else:
                        spectra_names = [f"Spectrum {i + 1}" for i in range(spectra.shape[0])]

            else:
                raise ValueError(f"Unsupported file format: {file_ext}")

            # Validate data
            if spectra is None or len(spectra.shape) != 2:
                raise ValueError("Loaded spectral data is not a valid 2D array")
            if wavelengths is None or len(wavelengths) != spectra.shape[1]:
                raise ValueError("Wavelengths do not match spectral data dimensions")
            if len(spectra_names) < spectra.shape[0]:
                spectra_names.extend([f"Spectrum {i + 1}" for i in range(len(spectra_names), spectra.shape[0])])

            # Create a new window for plotting
            plot_window = QMainWindow(parent)
            plot_window.setWindowTitle(f"Spectral Library: {os.path.basename(file_path)}")
            plot_window.setMinimumSize(800, 600)

            # Create Matplotlib figure and canvas
            figure = Figure()
            canvas = FigureCanvas(figure)
            ax = figure.add_subplot(111)

            # Plot each spectrum
            for i, spectrum in enumerate(spectra):
                ax.plot(wavelengths, spectrum, label=spectra_names[i], linewidth=1.5)

            # Customize plot
            ax.set_xlabel("Wavelength (micrometers)")
            ax.set_ylabel("Reflectance")
            ax.set_title("Spectral Library Plot")
            ax.grid(True, linestyle='--', alpha=0.6)
            ax.legend(loc="best", fontsize="small")
            figure.tight_layout()

            # Set up the window layout
            central_widget = QWidget()
            plot_window.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)
            layout.addWidget(canvas)

            # Show the window
            plot_window.show()

            logger.info(f"Successfully plotted spectral library: {file_path}")

        except Exception as e:
            logger.error(f"Error plotting spectral library {file_path}: {str(e)}")
            # This part is for integration with a main app window that has a status bar
            # if parent and hasattr(parent, 'statusBar'):
            #     parent.statusBar().showMessage(f"Error plotting spectral library: {str(e)}", 10000)