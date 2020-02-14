from . import read_tiff, read_h5
import numpy as np


def to_uint16(path):
	if ".tiff" in path :
		data  = read_tiff(path)
	if ".h5" in path:
		data = read_h5(path)

	data_min = np.min(data)

	if data_min < 0:
		data -= data_min

	data_max = np.max(data)

	if data_max > 65355 :
		raise ValueError('Conversion will truncate the data')
	else:
		data_uint16 = data.astype(np.uint16)
	return data_uint16




