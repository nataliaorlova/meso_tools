## this file has finctions to convert data

import numpy as np

def to_16bit(data, keep_dtype=True):
	"""
	this function will convert data to 16 bit
	if keep_dtype is True, input data type will be preserved: 
		float64 -> float16
		int64 -> int16
	if keep_dtype is False, output data is always int16
		float64 -> int16
		int64 -> int16
	Return: converted numpy array
	"""

	# let's first take care of the negative values 
	data_min = np.min(data)
	if data_min < 0:
		data -= data_min
	data_max = np.max(data)

	#let's check is teh 16bit dynamic range can be saturated 
	if data_max > 65355 :
		raise ValueError('Cancelling. Data needs to eb re-scaled first to avoid higher values truncation.')
	else:
		if keep_dtype:
			if data.dtype == np.int16 :
				data_out = data.astype(np.uint16)
			else:
				data_out = data.astype(np.float16) #assuming float in all other cases
		else: 
			data_out = data.astype(np.uint16)
	return data_out

def to_8bit(data, keep_dtype=True):
	"""
	this function will convert data to 8 bit
	if keep_dtype is True, input data type will be preserved: 
		floatN -> float8
		intN -> int8
	if keep_dtype is False, output data is always int16
		floatN -> int8
		intN -> int8
	Return: converted numpy array
	"""
	if keep_dtype:
		if data.dtype == np.int16 :
			data_out = data.astype(np.uint16)
		else:
			data_out = data.astype(np.float16) #assuming float in all other cases
	else: 
		data_out = data.astype(np.uint16)

	return data_out