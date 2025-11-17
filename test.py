from osgeo import gdal, gdal_array
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from tqdm import tqdm
import matplotlib.pyplot as plt
import rasterio

file = r"D:\__Rohit\Hperspectral\Project\misc\Dataset\TIFF\PRS_L2D_STD_20250119061830_20250119061834_0001_HCO_VNIR.tif"


with rasterio.open(file) as src:
    # read as masked array
    arr = src.read(masked=True)
    nodata_value = src.nodata
    print("NoData Value:", nodata_value)
    
    
# Count masked pixels
print("NoData pixels in first band:", np.sum(arr[11].mask))

# Replace masked pixels with 0
arr_filled = arr.filled(0)


plt.imshow(arr_filled[0], cmap='gray', vmin=np.nanpercentile(arr_filled, 2), vmax=np.nanpercentile(arr_filled, 98))











with rasterio.open(file) as src:
    arr = src.read(masked=True)
    nodata_value = src.nodata
    print("NoData Value:", nodata_value)



print(f"before {np.sum(arr==nodata_value)}")
# --- Replace NoData with 0
if nodata_value is not None:
    arr[arr == nodata_value] = 0
    print("Converted")

print(f"After {np.sum(arr==nodata_value)}")
print(src.nodata)




# --- Display the first band
plt.imshow(data, cmap='gray', vmin=np.nanpercentile(data, 2), vmax=np.nanpercentile(data, 98))







ds = gdal.Open(file, gdal.GA_ReadOnly)



image_data_gdal = ds.ReadAsArray()

print("GeoTransform:", ds.GetGeoTransform())
print("NoDataValue:", ds.GetRasterBand(1).GetNoDataValue())






ds = gdal.Open(file, gdal.GA_ReadOnly)



image_data_gdal = ds.ReadAsArray()




print("GeoTransform:", ds.GetGeoTransform())
print("NoDataValue:", ds.GetRasterBand(1).GetNoDataValue())


band = ds.GetRasterBand(1)
data = band.ReadAsArray()
data = np.where(data == 0, np.nan, data)


plt.imshow(data, cmap='gray', vmin=np.nanpercentile(data, 2), vmax=np.nanpercentile(data, 98))












from osgeo import gdal, gdal_array
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from tqdm import tqdm
import matplotlib.pyplot as plt
file = r"D:\__Rohit\Hperspectral\Project\misc\Dataset\TIFF\PRS_L2D_STD_20250119061830_20250119061834_0001_HCO_VNIR.tif"

dataset = gdal.Open(file, gdal.GA_ReadOnly)



rows, cols, bands = dataset.RasterYSize, dataset.RasterXSize, dataset.RasterCount

band0 = dataset.GetRasterBand(1)
gdal_dtype = band0.DataType
np_dtype = gdal_array.GDALTypeCodeToNumericTypeCode(gdal_dtype)
del dataset  # Close the original (not needed anymore)

image_data = np.zeros((bands, rows, cols), dtype=np_dtype)


def read_band(b):
    """Thread-safe band reading with NoData set to 0"""
    ds = gdal.Open(file, gdal.GA_ReadOnly)
    band = ds.GetRasterBand(b + 1)

    # Set NoData to 0 (in-memory, affects the band object)
    # band.SetNoDataValue(0)

    # Read data
    data = band.ReadAsArray().astype(np_dtype)  # optional: convert to float for consistency

    # Replace original NoData (if present) with 0
    nodata = band.GetNoDataValue()
    if nodata is not None:
        data[data == nodata] = 0

    ds = None  # close dataset
    return b, data








def read_band(b):
    """Thread-safe band reading"""
    ds = gdal.Open(file, gdal.GA_ReadOnly)
    band = ds.GetRasterBand(b + 1)
    band = band.SetNoDataValue(0)
    data = band.ReadAsArray()#.astype(np_dtype)
    ds = None  # Close dataset to free memory
    return b, data

# def read_band(b):
#     """Thread-safe band reading"""
#     ds = gdal.Open(file, gdal.GA_ReadOnly)
#     band = ds.GetRasterBand(b + 1)
    
#     nodata = band.GetNoDataValue()
#     data_arr = band.ReadAsArray().astype(np_dtype)
    
#     # Replace NoData values with np.nan (optional)
#     if nodata is not None:
#         print(f"Band number{b+1}",nodata)
#         data_arr[data_arr == nodata] = 0 #np.nan
#     else:
#         # Optionally treat zeros as NoData
#         data_arr[data_arr == 0] = np.nan
        

    
#     ds = None  # close
#     return b, data_arr



with ThreadPoolExecutor(max_workers=8) as executor:
    for b, data in tqdm(executor.map(read_band, range(bands)) , total = bands):
        image_data[:, :,b] = data

print("Shape:", image_data.shape)


image_data = np.moveaxis(image_data, 0, -1)

print("Shape:", image_data.shape)

data = image_data[:,:,0]

plt.imshow(data, cmap='gray', vmin=np.nanpercentile(data, 2), vmax=np.nanpercentile(data, 98))









plt.imshow(image_data[:, :, 0], cmap='gray', 
           vmin=np.nanpercentile(image_data[:, :, 0], 2), 
           vmax=np.nanpercentile(image_data[:, :, 0], 98))
plt.colorbar()
plt.title("Band 1 with 2-98% contrast stretch")
plt.show()
























