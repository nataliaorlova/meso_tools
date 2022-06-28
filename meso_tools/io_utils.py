## this file has input/output related functions
### reading/writing tiff, hdf5s, reading metadata

import tifffile
import h5py

def read_tiff(path_to_tiff, page_num=None):
    """ reads either entire tiff file, or if n is given, N pages of it
        path_to_tiff: str: local path to the tifffile
        page_num : int : number of pages to read, if none provide,d willa teempt to read entire tiff file. Will limlit to 5000 if tiff has more that 5000 pages.
    Return:
        tiff_array: 3D numpy array representing timeseries that was read
    """
    with tifffile.TiffFile(path_to_tiff, mode ='rb') as tiff:
        if page_num: 
                tiff_array = tiff.asarray(range(0, page_num))
        else: # number of pages is not provided: 
            if len(tiff.pages) >=5000:
                print(f"This timeseries has more than 5000 frames to not overload RAM, we will only read 5000 first pages.")
                print(f"To read more pages,in case large amount of RAM is available, provide number of pages to read by calling read_tiff(path_to_tiff, page_num=value)")
                page_num = 5000
                with tifffile.TiffFile(path_to_tiff, mode ='rb') as tiff:
                    tiff_array = tiff.asarray(range(0, page_num))
    return tiff_array

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