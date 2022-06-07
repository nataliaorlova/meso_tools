# This file has the code needed to process large FOV stack:
# 1. Asses all following:
#   a) stack is of correct type
#   b) only channel 1 saving is enabled
#   c) all rois are in non-discrete plane mode
#   d) all rois have only one scanfield
#   d) all rois are of the same pixel size and degree size (scaling would be too much work, plus we don't want to create a mess with resolution)
# 2. Get all above values for the stack (num of planes, etc)
# 3. Asses that tiff size is correct
# 4. If multiple repeats of the stack (volumes) - average them out before stitching

# 7. Stitching:
#       For nth z in z array:
#           Load nth page of tiff
#           For each roi in rois:
#               Get roi’s pixel size, and location
#               Get portion of the tiff to insert, inset to location in destination file

from matplotlib import path
from meso_tools.io_utils import read_si_metadata as get_meta
from meso_tools.io_utils import read_tiff
import numpy as np

GAP = 24

def read_full_field_meta(metadata):
    """
    reading of the relevant metadata fields
    return: dict
    """
    md_general = metadata[0]  
    meta_dict = {}
    meta_dict['num_slices'] = md_general['SI.hStackManager.actualNumSlices']
    meta_dict['num_volumes'] = md_general['SI.hStackManager.actualNumVolumes']
    meta_dict['z_step'] = md_general['SI.hStackManager.actualStackZStepSize']
    meta_dict['all_zs'] = np.asarray(md_general['SI.hStackManager.zsAllActuators'])[:,1]
    meta_dict['frames_per_slice'] = md_general['SI.hStackManager.framesPerSlice']
    
    #flag properties:
    meta_dict['channel_save'] = md_general['SI.hChannels.channelSave']
    meta_dict['stack_type'] = md_general['SI.hStackManager.stackDefinition']

    #metadata related to specific rois/scanfields
    meta_dict['rois'] = metadata[1]['RoiGroups']['imagingRoiGroup']['rois']
    return meta_dict

def check_meta(meta_dict):
    """
    assesions to check if the stakc is of correct type:
    1. Unifrom, non-centered
    2. only channel 1 is set to be saved
    3. all ROIs are in non-discrete mode 
    """
    assert meta_dict['channel_save'] == 1, f"More than 1 channel is set ot be saved when data acquired, unable to split"
    assert meta_dict['stack_type'] == 'uniform', f"stack is of wrong type, unable to split"

    # check that all ROIs are in discrete plane mode
    for i,roi in enumerate(meta_dict['rois']):
        assert roi['discretePlaneMode'] == 0, f"ROI {i} is not in discrete plane mode - unable to split"
        assert isinstance(roi['scanfields'], dict), f"ROI {i} has more than one scnafield - unable to split"

    #checking that all rois are of teh same size:
    pix_res = [roi['scanfields']['pixelResolutionXY'] for roi in  meta_dict['rois']]
    assert all(elem == pix_res[0] for elem in pix_res), f'ROIs are not of the same shape, unable to stitch'

    degree_size = [roi['scanfields']['sizeXY'] for roi in  meta_dict['rois']]
    assert all(elem == degree_size[0] for elem in degree_size), f'ROIs are not of the same size, unable to stitch'

    return

def check_tiff(tiff_array, rois):
    """
    calculate what tiff size should be, check if it's correct, calculate output tiff shape
    """
    # get tiff size
    tiff_shape = np.shape(tiff_array)
    # calculate what tiff shape should be:
    pix_res = rois[0]['scanfields']['pixelResolutionXY']
    output_tiff_shape =  [pix_res[0]*len(rois), pix_res[1]]
    expected_tiff_shape = [num_slices*num_repeats, pix_res[1]*len(rois)+(GAP*(len(rois)-1)), pix_res[0]]
    tiff_shape = np.shape(tiff_array)

    assert expected_tiff_shape == list(tiff_shape), f"Input tiff shape is unexpected"

    return output_tiff_shape

def average_tiff(tiff_array, meta):
    """
    average input tiff over all slices and number of stack repeats
    return : a single page tiff (2D np.array)
    """
    slices = meta['num_volumes'] # number of z slices
    # let's average eover repeats and slices
    # resahpe tp get array of [slices, repeats, y_pix_size, x_pix_size]
    x = tiff_array.reshape(tiff_array.shape[0] // slices, slices, tiff_array.shape[1], tiff_array.shape[2]) 
    # average over slices:
    y = x.mean(axis = 0) 
    # average over repeats:
    repeats = meta['num_volumes'] # this is number of repeats we want to average
    if repeats > 1 : 
        averaged_tiff = y.mean(axis=0)
    else:
        average_tiff = y
    return averaged_tiff

def deg_to_pix(meta_dict):
    """
    converts size and  center location of each ROI to pixel instead of degrees
    outputs meta_dict with pixel data added
    """
    
    return

def stitch_tiff(avg_tiff, output_tiff_shape):
    """
    actually stitch the file into a full FOV image
    returns: stitched image, 2D mumpy array
    """
    output_tiff = np.array(output_tiff_shape)

    return stitched_tiff

if __name__ == "__main__":
    path_to_tiff = "/Users/nataliaorlova/Code/data/incoming/1180346813_fullfield.tiff"

    metadata = get_meta(path_to_tiff)

    meta = read_full_field_meta(metadata)
    
    tiff_array = read_tiff(path_to_tiff)

    check_meta(meta)

    check_tiff(tiff_array, meta)

    output_tiff_shape = check_tiff(tiff_array, meta['rois'])

    averaged_tiff = average_tiff(tiff_array, meta)

    




# ToDo
# how to pass the filepath to this file without using argparser?