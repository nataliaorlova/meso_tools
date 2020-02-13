import tifffile

def read_tiff(tiff_path):
    im = tifffile.imread(tiff_path)
    return im
