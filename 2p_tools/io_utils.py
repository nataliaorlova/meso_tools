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
