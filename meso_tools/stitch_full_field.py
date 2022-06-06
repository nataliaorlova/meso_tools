# This file has the code needed to process large FOV stack:
# 1. Asses that stack is of correct type, only channel 1 saving is enabled, all rois are in non-discrete plane mode
# 2. Get all above values for the stack (num of planes, etc)
# 3. Asses that tiff size is correct
# 4. If multiple repeats of the stack (volumes) - average them out before stitching
# 5. Preallocated destination tiff:
# 6. Keep track of what output size should be:
# 7. Stitching:
#       For nth z in z array:
#           Load nth page of tiff
#           For each roi in rois:
#               Get roi’s pixel size, and location
#               Get portion of the tiff to insert, inset to location in destination file

from meso_tools.io_utils import read_si_metadata as get_meta
import numpy as np

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

def check_stack(meta_dict):
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
        assert roi['discretePlaneMode'] == 0, f"ROI {i} is not in discrete plane mode, unable to split"
    
    return




if __name__ == "__main__":
    path_to_tiff = "/Users/nataliaorlova/Code/data/incoming/1180346813_fullfield.tiff"

    metadata = get_meta(path_to_tiff)

    meta = read_full_field_meta(metadata)

    check_stack(meta)






# how to pass the filepath to this file?
# wihtout using argparser?