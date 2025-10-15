from osgeo import gdal
import numpy as np
import numexpr as ne
import re
import logging
from typing import Dict, Set

# --- Configure logging for clear feedback ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Use GDAL exceptions for error handling ---
gdal.UseExceptions()

class RasterCalculator:
    """
    A robust, memory-efficient raster calculator using GDAL for backend processing.

    This class performs mathematical operations on raster bands by processing
    large files in chunks (blocks) to ensure low memory consumption. It uses
    `numexpr` for fast and safe evaluation of mathematical expressions.

    It is implemented as a context manager to ensure that GDAL dataset handles
    are properly managed.

    Example Usage:
        ndvi_expression = '(B5 - B4) / (B5 + B4)'
        input_raster = 'path/to/your/landsat_image.tif'
        output_raster = 'path/to/your/ndvi_result.tif'

        try:
            with RasterCalculator(input_raster) as calc:
                calc.calculate_and_save(ndvi_expression, output_raster)
            logging.info(f"Successfully created NDVI image at {output_raster}")
        except Exception as e:
            logging.error(f"An error occurred: {e}")
    """

    def __init__(self, input_raster_path: str):
        """
        Initializes the RasterCalculator with the path to the input raster.

        Args:
            input_raster_path (str): The file path for the source raster image.
        """
        if not input_raster_path:
            raise ValueError("Input raster path cannot be empty.")
        self.input_raster_path = input_raster_path
        self.src_dataset = None

    def __enter__(self):
        """Opens the source raster file for reading."""
        try:
            self.src_dataset = gdal.Open(self.input_raster_path, gdal.GA_ReadOnly)
            logging.info(f"Successfully opened {self.input_raster_path}")
            return self
        except RuntimeError as e:
            logging.error(f"Failed to open raster file with GDAL: {self.input_raster_path}")
            raise IOError(f"GDAL Error: {e}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Closes the source raster file by dereferencing the dataset."""
        if self.src_dataset:
            self.src_dataset = None
            logging.info(f"Closed {self.input_raster_path}")

    @staticmethod
    def _parse_expression(expression: str) -> Set[int]:
        """
        Parses the mathematical expression to identify required band numbers.
        Band variables should be in the format 'B{number}', e.g., 'B1', 'B4', 'B12'.

        Args:
            expression (str): The mathematical formula string.

        Returns:
            Set[int]: A set of unique band numbers required for the calculation.
        """
        band_matches = re.findall(r'B(\d+)', expression, re.IGNORECASE)
        if not band_matches:
            raise ValueError("Expression does not contain any valid band identifiers (e.g., 'B1', 'B2').")
        
        band_numbers = {int(b) for b in band_matches}
        logging.info(f"Parsed expression. Required bands: {sorted(list(band_numbers))}")
        return band_numbers

    def calculate_and_save(self, expression: str, output_raster_path: str):
        """
        Calculates a new raster based on the provided expression and saves it to a file.
        This method processes the raster in chunks to handle large files efficiently.

        Args:
            expression (str): The mathematical formula to apply. Bands must be
                              referenced as 'B1', 'B2', etc.
            output_raster_path (str): The file path to save the resulting raster.
        """
        if self.src_dataset is None:
            raise RuntimeError("RasterCalculator must be used within a 'with' statement.")

        band_numbers = self._parse_expression(expression)

        # --- Validate that all required bands exist in the source dataset ---
        max_required_band = max(band_numbers)
        if max_required_band > self.src_dataset.RasterCount:
            raise ValueError(
                f"Expression requires band {max_required_band}, but the input "
                f"raster only has {self.src_dataset.RasterCount} bands."
            )

        # --- Prepare the output raster file ---
        driver = gdal.GetDriverByName('GTiff')
        dst_dataset = driver.Create(
            output_raster_path,
            self.src_dataset.RasterXSize,
            self.src_dataset.RasterYSize,
            1,
            gdal.GDT_Float32, # Calculations often result in floats
            options=['COMPRESS=LZW'] # A good default compression
        )
        dst_dataset.SetGeoTransform(self.src_dataset.GetGeoTransform())
        dst_dataset.SetProjection(self.src_dataset.GetProjectionRef())
        
        dst_band = dst_dataset.GetRasterBand(1)
        nodata_val = -9999.0 # A common nodata value for float rasters
        dst_band.SetNoDataValue(nodata_val)

        # --- Process the raster in blocks ---
        # Get block size from the first band (it's usually the same for all)
        src_band_one = self.src_dataset.GetRasterBand(1)
        block_xsize, block_ysize = src_band_one.GetBlockSize()
        xsize = self.src_dataset.RasterXSize
        ysize = self.src_dataset.RasterYSize

        logging.info(f"Starting calculation with block size {block_xsize}x{block_ysize}.")

        for y in range(0, ysize, block_ysize):
            # Determine the vertical block size (may be smaller at the edge)
            win_ysize = min(block_ysize, ysize - y)
            for x in range(0, xsize, block_xsize):
                logging.info(f"Processing block at offset ({x}, {y})...")
                # Determine the horizontal block size
                win_xsize = min(block_xsize, xsize - x)

                # Read data for the current block from all required bands
                bands_data: Dict[str, np.ndarray] = {}
                for b_num in band_numbers:
                    src_band = self.src_dataset.GetRasterBand(b_num)
                    band_array = src_band.ReadAsArray(x, y, win_xsize, win_ysize)
                    bands_data[f'B{b_num}'] = band_array.astype(np.float32)
                
                # Perform the calculation safely
                with np.errstate(divide='ignore', invalid='ignore'):
                    result = ne.evaluate(expression, local_dict=bands_data)

                # Set the output data type and fill NaNs
                result = result.astype(np.float32)
                np.nan_to_num(result, nan=nodata_val, copy=False)
                
                # Write the resulting block to the destination raster
                dst_band.WriteArray(result, x, y)
        
        # Flush the cache to ensure all data is written to the file
        dst_band.FlushCache()
        dst_dataset = None # Dereference to close the file
        
        logging.info(f"Calculation complete. Result saved to {output_raster_path}")


# # --- Example of how to integrate and use the class ---
# if __name__ == '__main__':
#     def create_dummy_raster_gdal(path: str, bands: int, height: int, width: int):
#         """Creates a dummy GeoTIFF file using GDAL for demonstration purposes."""
#         driver = gdal.GetDriverByName('GTiff')
#         dst_ds = driver.Create(path, width, height, bands, gdal.GDT_UInt16)
        
#         # Set dummy geotransform (origin and pixel size)
#         # Origin (top left) x, pixel width, rotation, origin y, rotation, pixel height (negative)
#         dst_ds.SetGeoTransform([440720, 60, 0, 3751320, 0, -60])
        
#         # Set dummy projection (WGS 84 / UTM zone 10N)
#         dst_ds.SetProjection('PROJCS["WGS 84 / UTM zone 10N",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",-123],PARAMETER["scale_factor",0.9996],PARAMETER["false_easting",500000],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH],AUTHORITY["EPSG","32610"]]')

#         for i in range(1, bands + 1):
#             band = dst_ds.GetRasterBand(i)
#             data = np.random.randint(1000 * i, 2000 * i, (height, width)).astype(np.uint16)
#             if i == 4: # Simulate lower values for a "red" band
#                 data = np.random.randint(500, 1500, (height, width)).astype(np.uint16)
#             band.WriteArray(data)
#             band.FlushCache()
            
#         dst_ds = None # Close the dataset
#         logging.info(f"Created GDAL dummy raster at {path}")

#     # --- Configuration ---
#     DUMMY_INPUT_RASTER = 'dummy_multiband_image_gdal.tif'
#     NDVI_OUTPUT = 'ndvi_output_gdal.tif'
#     SAVI_OUTPUT = 'savi_output_gdal.tif'

#     # Create the dummy file with 5 bands
#     create_dummy_raster_gdal(path=DUMMY_INPUT_RASTER, bands=5, height=512, width=512)

#     # --- 1. Calculate NDVI ---
#     ndvi_formula = '(B5 - B4) / (B5 + B4)'
    
#     logging.info("\n--- Calculating NDVI with GDAL backend ---")
#     try:
#         with RasterCalculator(DUMMY_INPUT_RASTER) as calculator:
#             calculator.calculate_and_save(ndvi_formula, NDVI_OUTPUT)
#         logging.info(f"NDVI calculation finished successfully.")
#     except Exception as e:
#         logging.error(f"NDVI calculation failed: {e}")

#     # --- 2. Calculate SAVI ---
#     savi_formula = '((B5 - B4) / (B5 + B4 + 0.5)) * 1.5'

#     logging.info("\n--- Calculating SAVI with GDAL backend ---")
#     try:
#         with RasterCalculator(DUMMY_INPUT_RASTER) as calculator:
#             calculator.calculate_and_save(savi_formula, SAVI_OUTPUT)
#         logging.info(f"SAVI calculation finished successfully.")
#     except Exception as e:
#         logging.error(f"SAVI calculation failed: {e}")