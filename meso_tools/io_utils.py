## this file has input/output related functions
### reading/writing tiff, hdf5s, reading metadata

import tifffile
import h5py

def read_tiff(path):
    im = tifffile.imread(path)
    return im

def write_tiff(path, data):
    tifffile.imsave(path, data)
    return

def read_h5(path, field):
    """
    function to read a field form hdf5 file, wrapping h5py
    :param path: path to hdf5 file
    :param field: datafield to read
    :return: raed data
    """
    with h5py.File(path, "r") as f:
        data = f[field][()]
    return data

def write_h5(path, h5_data):
    with h5py.File(path, 'w') as f:
        f.create_dataset('data', data=h5_data)
    return

def read_si_metadata(path_to_tiff):
    """
    function to read scnaimage metadata in full
    path: path to tiff file
    returns: dict w metadata
    """
    meta_data = tifffile.read_scanimage_metadata(open(path_to_tiff, 'rb'))
    return meta_data

def get_roi_data(path_to_tiff):
    """
    function to read scnaimage metadata's ROI structure part
    path: path to tiff file
    returns: dict w metadata
    """
    meta_data = tifffile.read_scanimage_metadata(open(path_to_tiff, 'rb'))
    return meta_data[1]
