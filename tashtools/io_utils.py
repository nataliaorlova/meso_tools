import tifffile
import h5py


def read_tiff(path):
    im = tifffile.imread(path)
    return im


def write_tiff(path, data):
    tifffile.imsave(path, data)
    return


def read_h5(path):
    with h5py.File(path, "r") as f:
        data = f["data"].value
    return data


def write_h5(path, h5_data):
    with h5py.File(path, 'w') as f:
        f.create_dataset('data', data=h5_data)
    return

