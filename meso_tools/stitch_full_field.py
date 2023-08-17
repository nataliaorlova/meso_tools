# This file has the code needed to process large FOV stack:
# 1. Asses all following:
#   a) stack is of correct type
#   b) only channel 1 saving is enabled
#   c) all rois are in non-discrete plane mode
#   d) all rois have only one scanfield
#   d) all rois are of the same pixel size and degree size (scaling would be too much work, 
#      plus we don't want to create a mess with resolution)
# 2. Get all above values for the stack (num of planes, etc)
# 3. Asses that tiff size is correct
# 4. If multiple repeats of the stack (volumes) - average them out before stitching
# 7. Stitching:
#       For nth z in z array:
#           Load nth page of tiff
#           For each roi in rois:
#               Get roi’s pixel size, and location
#               Get portion of the tiff to insert, inset to location in destination file
# 8. split and avergae surface images
# 9. insert surface averages into stitched tiff
#       downsample to match full field file resolution

#       figure out insert coordinates
#           normalization w regards to full field is problematic 

import numpy as np
from meso_tools.io_utils import read_scanimage_metadata as get_meta
from meso_tools.io_utils import read_tiff, write_tiff
from meso_tools.image_tools import image_negative_rescale, image_downsample
import sciris as sc


def read_full_field_stack_meta(metadata : dict) -> dict:
    """
    read_full_field_meta : reads metadata relevant to stitching mROI stack data

    Parameters
    ----------
    metadata : dict
        full scanimage metadata dictionary

    Returns
    -------
    dict
        dictionary with only relevant fields
    """
    
    md_general = metadata[0]  
    meta_dict = {}
    
    # quantifying properties:
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

def read_full_field_meta(metadata : dict) -> dict:
    """
    read_full_field_meta : reads metadata relevant to stitching mROI data

    Parameters
    ----------
    metadata : dict
        full scanimage metadata dictionary

    Returns
    -------
    dict
        dictionary with only relevant fields
    """
    md_general = metadata[0]  
    meta_dict = {}
    
    meta_dict['channel_save'] = md_general['SI.hChannels.channelSave']

    #metadata related to specific rois/scanfields
    meta_dict['rois'] = metadata[1]['RoiGroups']['imagingRoiGroup']['rois']
    
    return meta_dict

def check_meta(meta_dict):
    """
    assertions to check if the stack is of correct type and skimming off metadata
    1. Unifrom, non-centered
    2. only channel 1 is set to be saved
    3. all ROIs are in non-discrete mode 
    """
    assert meta_dict['channel_save'] == 1, f"More than 1 channel is set ot be saved when data acquired, unable to split"
    assert meta_dict['stack_type'] in ['uniform', 'bounded'], f"stack is of wrong type, unable to split"

    # check that all ROIs are in discrete plane mode
    for i,roi in enumerate(meta_dict['rois']):
        assert roi['discretePlaneMode'] == 0, f"ROI {i} is not in discrete plane mode - unable to split"
        assert isinstance(roi['scanfields'], dict), f"ROI {i} has more than one scnafield - unable to split"

    #checking that all rois are of the same size:
    pix_res = [roi['scanfields']['pixelResolutionXY'] for roi in  meta_dict['rois']] #XY
    assert all(elem == pix_res[0] for elem in pix_res), f'ROIs are not of the same shape, unable to stitch'

    degree_size = [roi['scanfields']['sizeXY'] for roi in  meta_dict['rois']] # XY
    assert all(elem == degree_size[0] for elem in degree_size), f'ROIs are not of the same size, unable to stitch'
    # take pixel resolution of hte first ROI since we checked that they all are of the same rezolution
    meta_dict['pixel_to_degree'] = np.array(pix_res[0])/np.array(degree_size[0])  # XY = XY /XY

    return meta_dict

def check_tiff(tiff_array, meta_dict):
    """
    calculate what tiff size should be, check if it's correct, calculate output tiff shape
    """
    # get tiff size
    tiff_shape = np.shape(tiff_array)
    rois = meta_dict['rois']
    num_slices = meta_dict['num_slices']
    num_repeats = meta_dict['num_volumes']
    frames_per_plane = meta_dict['frames_per_slice']

    # calculate what tiff shape should be:
    
    pix_res_x = rois[0]['scanfields']['pixelResolutionXY'][0]
    pix_res_y = rois[0]['scanfields']['pixelResolutionXY'][1]

    output_tiff_shape =  [pix_res_x*len(rois), pix_res_y]
    
    if frames_per_plane != 1:
        raw_len = tiff_array.shape[2]
        tiff_array_avg = tiff_array.mean(axis=1)
        tiff_shape = np.shape(tiff_array_avg)
    else:
        raw_len = tiff_array.shape[1]
        tiff_shape = np.shape(tiff_array)

    rois_num = len(meta_dict['rois'])
    gap = (raw_len - pix_res_y*rois_num)/(rois_num-1)
    expected_tiff_shape = [num_slices*num_repeats, pix_res_y*len(rois)+(gap*(len(rois)-1)), pix_res_x]

    assert expected_tiff_shape == list(tiff_shape), f"Input tiff shape is unexpected"

    return output_tiff_shape, int(gap)

def get_output_shape(stack : np.array, meta_dict : dict) -> int:
    """
    get_output_shape : calculate output shape and gap between images inserted vertically in one page of a tiff

    Parameters
    ----------
    stack : np.array
        input stack of images
    meta_dict : dict
        dictionary with metadata

    Returns
    -------
    int
        gap in number of pixels
    """
    raw_len = stack.shape[1]
    rois = meta_dict['rois']
    pix_res_x = rois[0]['scanfields']['pixelResolutionXY'][0]
    pix_res_y = rois[0]['scanfields']['pixelResolutionXY'][1]
    rois_num = len(meta_dict['rois'])
    gap = int((raw_len - pix_res_y*rois_num)/(rois_num-1))

    output_shape =  [pix_res_x*len(rois), pix_res_y]

    return gap, output_shape

def average_tiff(tiff_array, meta):
    """
    average input tiff over all slices and number of stack repeats (volumes) and frames per plane 
    return : a single page tiff (2D np.array)
    """
    slices = meta['num_volumes'] # number of z slices
    # let's average over repeats and slices
    # resahpe tp get array of [slices, repeats, y_pix_size, x_pix_size]
    x = tiff_array.reshape(tiff_array.shape[0] // slices, slices, tiff_array.shape[1], tiff_array.shape[2]) 
    # average over slices:
    y = x.mean(axis = 0) 
    # average over repeats:
    repeats = meta['num_volumes'] # this is number of repeats we want to average
    if repeats > 1 : 
        averaged_tiff = y.mean(axis=0)
    else:
        averaged_tiff = y
    return averaged_tiff

def average_stack(stack: np.array, meta: dict, avg_slices : bool = True, avg_repeats : bool = True, avg_frames : bool = True) -> np.array:
    """
    average_stack average stack over repeats of stack, planes or frames per plane
    Scanimage tiff files are ordered the following way : [number of z slices * number of stack repeats, frames per plane, rows, columns]
    Parameters
    ----------
    stack : np.array
        numpy array containing teh stack
    meta : dict
        dictionary wiht metadata
    avg_slices : bool, optional
        whether to average over slices, by default False
    avg_repeats : bool, optional
        whether to average over repeats, by default True
    avg_frames : bool, optional
        whether to average over frames acquired at teh same plane, by default True

    Returns
    -------
    np.array
        averaged stack
    """
    repeats = meta['num_volumes'] # number of repeats of one stack
    frames = meta['frames_per_slice'] # number of frames aquired at one z

    # let's first average by frames
    if avg_frames & (frames !=1):
        stack = stack.mean(axis=1)

    # reshape to average repeats and slices
    stack_reshape = stack.reshape(stack.shape[0] // repeats, repeats, stack.shape[1], stack.shape[2])
    # avergae repeats
    if avg_repeats:
        stack_averaged = stack_reshape.mean(axis = 1)
    # avergae slices
    if avg_slices:
        stack_averaged = stack_reshape.mean(axis = 0)
    # average both  
    if avg_slices & avg_repeats:
        stack_temp = stack_reshape.mean(axis = 1)
        stack_averaged = stack_temp.mean(axis = 0)

    return stack_averaged


def stitch_tiff(averaged_tiff, meta_dict, gap, output_tiff_shape):
    """
    actually stitch the file into a full FOV image
    returns: stitched image, 2D mumpy array
    """

    rois = meta_dict['rois']

    output_tiff_shape = [output_tiff_shape[1],output_tiff_shape[0]]

    stitched_tiff = np.empty(output_tiff_shape)

    pix_to_deg_x = rois[0]['scanfields']['pixelResolutionXY'][0]/rois[0]['scanfields']['sizeXY'][0]
    pix_to_deg_y = rois[0]['scanfields']['pixelResolutionXY'][1]/rois[0]['scanfields']['sizeXY'][1]

    roi_centers = np.array([roi['scanfields']['centerXY'] for roi in  rois]) # [x,y] array of ROI centers in degrees
    roi_sizes = np.array([roi['scanfields']['sizeXY'] for roi in  rois]) # [x, y] array of ROI sizes in degrees

    # calculate top right corner, degrees
    insert_top_right = roi_centers - roi_sizes/2
    insert_bottom_left = roi_centers + roi_sizes/2

    #normalize top right corner coords, degrees
    roi_x_min = np.min([i[0] for i in insert_top_right])
    roi_y_min = np.min([i[1] for i in insert_top_right])
    insert_top_right -= [roi_x_min, roi_y_min]
    meta_dict['min_x'] = roi_x_min
    meta_dict['min_y'] = roi_y_min
    
    #normalize bottom left corner coords, degrees
    insert_bottom_left -= [roi_x_min, roi_y_min]

    # convert insert coordinates to pixels
    insert_top_right *= [pix_to_deg_x, pix_to_deg_y]
    insert_top_right = insert_top_right.round(0)
    insert_top_right = insert_top_right.astype(np.int16)
    insert_top_right[:, [1, 0]] = insert_top_right[:, [0, 1]]

    insert_bottom_left *= [pix_to_deg_x, pix_to_deg_y]
    insert_bottom_left = insert_bottom_left.round(0)
    insert_bottom_left = insert_bottom_left.astype(np.int16)
    insert_bottom_left[:, [1, 0]] = insert_bottom_left[:, [0, 1]]

    # convert sizes to pixels:
    roi_sizes *= np.array([pix_to_deg_x, pix_to_deg_y])
    roi_sizes= roi_sizes.round(0)
    roi_sizes = roi_sizes.astype(int)

    cut_top_right = np.array([[i*(roi_sizes[i][1] + gap), 0] for i, roi in enumerate(rois)])
    cut_bottom_left = np.array([[(i+1)*(roi_sizes[i][1]) + i*gap, roi_sizes[i][0]] for i, roi in enumerate(rois)])

    for i, _ in enumerate(rois):
        # averaged_tiff = image_negative_rescale(averaged_tiff)
        image_to_insert = averaged_tiff[cut_top_right[i][0]:cut_bottom_left[i][0], cut_top_right[i][1]:cut_bottom_left[i][1]]
        stitched_tiff[insert_top_right[i][0]:insert_bottom_left[i][0], insert_top_right[i][1]:insert_bottom_left[i][1]] = image_to_insert

    return stitched_tiff, meta_dict

def split_surface(path_to_surface):

    surface_array = read_tiff(path_to_surface)
    surface_meta = get_meta(path_to_surface)

    surface_meta_dict = {}
    surface_meta_dict['rois'] = surface_meta[1]['RoiGroups']['imagingRoiGroup']['rois']
    surface_meta_dict['num_repeats'] = surface_meta[0]['SI.hStackManager.actualNumVolumes']

    # handling 1 or more than 1 ROIs in tiff metadata 
    if isinstance(surface_meta[1]['RoiGroups']['imagingRoiGroup']['rois'], list):
        surface_meta_dict['num_rois'] = len(surface_meta_dict['rois'])
    elif isinstance(surface_meta[1]['RoiGroups']['imagingRoiGroup']['rois'], dict):
        surface_meta_dict['num_rois'] = 1
        
    # averaging over number of repeats: 
    surface_averaged = np.average(surface_array.reshape(surface_meta_dict['num_repeats'], -1, surface_array.shape[1], surface_array.shape[2]), axis=0)
    
    assert surface_averaged.shape[0] == surface_meta_dict['num_rois'], f"Metadata of the surface file reports {surface_meta_dict['num_rois']} rois, while tiff file has data for {surface_averaged.shape[0]}"

    if surface_averaged.shape[0] != 1:
        for i in range(len(surface_meta_dict['rois'])):
            surface_meta_dict['rois'][i]['array'] = surface_averaged[i, :,:]
    else:
        surface_meta_dict['rois']['array'] = surface_averaged[0,:,:]

    return surface_meta_dict, surface_averaged


def insert_surface_to_ff(ff_stitched_tiff, ff_meta_dict, split_surface_meta):

    # get pixel to degrees for full field data
    pixel_resolution_ff = ff_meta_dict['pixel_to_degree'] #XY
    right_corner_ff = np.array([ff_meta_dict['min_x'], ff_meta_dict['min_y']]) #XY 
    
    sesion_type_1x6 = True
    if isinstance(split_surface_meta['rois'], list):
        sesion_type_1x6 = False
    
    if not sesion_type_1x6: 
        # get pixel resolution and check that resolution of all rois in surface is the same
        pix_res = [roi['scanfields']['pixelResolutionXY'] for roi in  split_surface_meta['rois']]
        assert all(elem == pix_res[0] for elem in pix_res), f'ROIs are not of the same shape, unable to stitch'
        pix_res_surface = np.array(pix_res[0]) #XY
        
        # get degree size and check that resolution of all rois in surface is the same
        degree_size = [roi['scanfields']['sizeXY'] for roi in  split_surface_meta['rois']]
        assert all(elem == degree_size[0] for elem in degree_size), f'ROIs are not of the same shape, unable to stitch'
        degree_size_surface = np.array(degree_size[0]) #XY
        
        # finally, pixel to degree for surface data
        pixel_resolution_surf = pix_res_surface / degree_size_surface # XY = XY / XY

        # bring two piece of data to the same pix/degree (usually this means downsampling surafce tiff arrays)
        # calculate scaling factor
        convert_factor = pixel_resolution_surf / pixel_resolution_ff # XY = XY * XY
        ff_stitched_mapped = np.copy(ff_stitched_tiff)

        # downsampling 
        for i, roi in enumerate(split_surface_meta["rois"]):
            a = roi['array']
            b = image_negative_rescale(a)
            c = image_downsample(b, convert_factor)
            roi['downsampled_array'] = c

        for roi in split_surface_meta["rois"]:
            scanfield = roi['scanfields']
            roi_center = np.array(scanfield['centerXY']) # get center, XY
            roi_size = np.array(scanfield['sizeXY']) # get size, XY
            # convert to pixels
            roi_center *= pixel_resolution_ff # XY = XY * XY
            roi_size *= pixel_resolution_ff # XY = XY * XY
            # round down
            roi_size = np.floor(roi_size)
            roi_center = np.floor(roi_center)
            # caculate paste coordinates
            top_right = roi_center - roi_size/2 #XY
            bottom_left = roi_center + roi_size/2 #XY

            # normalize to right top corner    
            a = right_corner_ff * pixel_resolution_ff #XY * XY
            top_right = top_right - a #XY - XY
            b = right_corner_ff * pixel_resolution_ff #(XY * XY)
            bottom_left = bottom_left - b #XY - XY

            # cast as int
            top_right = top_right.astype(np.int16)
            bottom_left = bottom_left.astype(np.int16)

            #insert into full field image:
            ff_stitched_mapped[top_right[1]:bottom_left[1], top_right[0]:bottom_left[0]] = roi['downsampled_array']
    else:
        # get pixel number
        pix_res = split_surface_meta['rois']['scanfields']['pixelResolutionXY']
        pix_res_surface = np.array(pix_res[0]) #XY

        # get degree size 
        degree_size = split_surface_meta['rois']['scanfields']['sizeXY']
        degree_size_surface = np.array(degree_size[0]) #XY

        # finally, pixel to degree for surface data
        pixel_resolution_surf = pix_res_surface / degree_size_surface # XY = XY / XY
        
        # bring two piece of data to the same pix/degree (usually this means downsampling surface tiff arrays)
        # calculate scaling factor
        convert_factor = pixel_resolution_surf / pixel_resolution_ff # XY = XY / XY
        ff_stitched_mapped = np.copy(ff_stitched_tiff)

        # downsampling 
        a = split_surface_meta["rois"]['array']
        b = image_negative_rescale(a)
        c = image_downsample(b, convert_factor)
        split_surface_meta["rois"]['downsampled_array'] = c

        roi = split_surface_meta["rois"]
        scanfield = roi['scanfields']
        roi_center = np.array(scanfield['centerXY']) # get center, XY
        roi_size = np.array(scanfield['sizeXY']) # get size, XY
        # convert to pixels
        roi_center *= pixel_resolution_ff # XY = XY * XY
        roi_size *= pixel_resolution_ff # XY = XY * XY
        # round down
        roi_size = np.floor(roi_size)
        roi_center = np.floor(roi_center)
        # caculate paste coordinates
        top_right = roi_center - roi_size/2 #XY
        bottom_left = roi_center + roi_size/2 #XY

        # normalize to right top corner    
        a = right_corner_ff * pixel_resolution_ff #XY * XY
        top_right = top_right - a #XY - XY
        b = right_corner_ff * pixel_resolution_ff #(XY * XY)
        bottom_left = bottom_left - b #XY - XY

        # cast as int
        top_right = top_right.astype(np.int16)
        bottom_left = bottom_left.astype(np.int16)

        #insert into full field image:
        ff_stitched_mapped[top_right[1]:bottom_left[1], top_right[0]:bottom_left[0]] = roi['downsampled_array']
        

    return ff_stitched_mapped

if __name__ == "__main__":

    #Inputs:
    path_to_tiff = "/Users/nataliaorlova/Code/data/incoming/1180346813_fullfield.tiff"
    surface_path = "/Users/nataliaorlova/Code/data/incoming/1180346813_averaged_surface.tiff"


    #Outputs: 
    meta_path = "/Users/nataliaorlova/Code/data/incoming/1180346813_fullfield_metadata.dict"
    path_to_tiff_stitched = "/Users/nataliaorlova/Code/data/incoming/1180346813_fullfield_stitched.tiff"
    path_to_tiff_mapped = "/Users/nataliaorlova/Code/data/incoming/1180346813_fullfield_stitched_mapped.tiff"

    #reading tiff and it's metadata, saving metadata to a dict object to disk
    tiff_array = read_tiff(path_to_tiff)
    meta = get_meta(path_to_tiff)
    ff_meta_dict = read_full_field_meta(meta)
    ff_meta_dict = check_meta(ff_meta_dict)
    check_tiff(tiff_array, ff_meta_dict)
    output_tiff_shape, gap = check_tiff(tiff_array, ff_meta_dict)
    sc.saveobj(meta_path, ff_meta_dict)

    #averaging and stitching stack, writing stitched stack in a tiff file to disk
    ff_averaged_tiff = average_tiff(tiff_array, ff_meta_dict)
    ff_stitched_tiff, ff_meta_dict = stitch_tiff(ff_averaged_tiff, ff_meta_dict, gap, output_tiff_shape)
    write_tiff(path_to_tiff_stitched, ff_stitched_tiff)

    #splitting surface file, mapping surface images to full field, saving into a tiff
    split_surface_meta, surface_averaged = split_surface(surface_path)
    ff_stitched_mapped = insert_surface_to_ff(ff_stitched_tiff, ff_meta_dict, split_surface_meta)
    write_tiff(path_to_tiff_mapped, ff_stitched_mapped)