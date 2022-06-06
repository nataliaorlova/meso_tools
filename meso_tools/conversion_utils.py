## this file has finctions to convert data

import numpy as np

def to_16bit(data):
	data_min = np.min(data)
	if data_min < 0:
		data -= data_min
	data_max = np.max(data)
	if data_max > 65355 :
		raise ValueError('Cancelling. Data needs to eb re-scaled first to avoid higher values truncation.')
	else:
		if data.dtype == np.int16 :
			data_out = data.astype(np.uint16)
		else:
			data_out = data.astype(np.float16) #assuming float in all other cases
	return data_out