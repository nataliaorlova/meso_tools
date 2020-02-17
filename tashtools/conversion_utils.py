from . import read_tiff, read_h5
import numpy as np


def to_16bit(path):
	if ".tiff" in path :
		data  = read_tiff(path)
	elif ".h5" in path:
		data = read_h5(path)
	else:
		raise ValueError('Input file has to be *.tiff or *.hdf5')

	data_min = np.min(data)

	if data_min < 0:
		data -= data_min

	data_max = np.max(data)

	if data_max > 65355 :
		raise ValueError('Cancelling. Data needs to eb re-scaled first to avoid higher values truncation.')
	else:
		if data.dtype == np.float32 :
			data_out = data.astype(np.float16)
		elif data.dtype == np.int16 :
			data_out = data.astype(np.uint16)
	return data_out





