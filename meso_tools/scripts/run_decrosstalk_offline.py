from ophys_etl.types import OphysROI
from ophys_etl.modules.decrosstalk.ophys_plane import DecrosstalkingOphysPlane
from ophys_etl.modules.decrosstalk.decrosstalk import run_decrosstalk

from allensdk.brain_observatory.behavior.behavior_ophys_experiment import BehaviorOphysExperiment
import mindscope_qc.pipeline_dev.paired_plane_registration as ppr  # on paired-plane branch
import mindscope_qc.data_access.from_lims as from_lims
import glob

import tempfile
import time
import json
import pathlib
import numpy as np

from dask.distributed import Client

def find_actual_motion_corrected_movie(eid):
    """
    Takes eid (an int) and returns the path to the official
    motion corrected movie corresponding to that ophys_experiment_id
    """
    expt_path = from_lims.get_general_info_for_ophys_experiment_id(
        eid).experiment_storage_directory.iloc[0]
    raw_h5 = expt_path / ('processed/' + str(eid) + '_suite2p_motion_output.h5')
    if not raw_h5.is_file():
        raise RuntimeError(
            f"could not find motion corrected movie for {eid}\n"
            f"tried {raw_h5.resolve().absolute()}")
    return raw_h5


def serialize_mask(roi_mask):
    """
    Serialize a single ROI mask

    Parameters
    ----------
    roi_mask: np.nadarray
        The grid of booleans indicating where the ROI exists in the field
        of view

    Returns
    -------
    serialized_roi: dict
        The dict that needs to be read in by OphysRoi.from_schema_dict)
    """
    serialized_roi = dict()
    valid_pixels = np.where(roi_mask)

    y0 = valid_pixels[0].min()
    x0 = valid_pixels[1].min()

    y1 = valid_pixels[0].max()
    x1 = valid_pixels[1].max()

    valid_mask = roi_mask[y0:y1+1, x0:x1+1]

    serialized_roi['x'] = int(x0)
    serialized_roi['y'] = int(y0)
    serialized_roi['width'] = int(valid_mask.shape[1])
    serialized_roi['height'] = int(valid_mask.shape[0])

    serialized_roi['mask_matrix'] = [[int(v) for v in valid_mask[ii,:]]
                                     for ii in range(valid_mask.shape[0])]

    return serialized_roi


def serialize_rois(
        roi_df):
    """
    Convert a dataframe of ROIs into a dict that can be deserialized into
    an OphysROI by ophys_etl_pipelines.

    Parameters
    ----------
    roi_df: pandas.DataFrame
        The dataframe returned by BehaviorOphysExperiment.roi_masks

    Returns
    -------
    serialized_rois: list(OphysROI)
        a list of the ROIs in the form of OphysROI objects
    """
    serialized_rois = []
    for roi_id, roi_mask in zip(roi_df.cell_roi_id.values,
                                roi_df.roi_mask.values):
        this_roi = serialize_mask(roi_mask)
        this_roi['id'] = int(roi_id)
        this_roi['valid_roi'] = True
        serialized_rois.append(OphysROI.from_schema_dict(this_roi))

    return serialized_rois


def get_plane_objects(plane1_eid):
    """
    Take an ophys_experiment_id and return the BehaviorOphysExperiment
    object corresponding to that ID as well as the BehaviorOphysExperiment
    corresponding to its coupled plane.
    """
    plane1_experiment = BehaviorOphysExperiment.from_lims(plane1_eid)
    plane2_eid = ppr.get_paired_plane_id(plane1_eid)
    plane2_experiment = BehaviorOphysExperiment.from_lims(plane2_eid)
    return (plane1_experiment, plane2_experiment)


def find_matching_files(eid, save_path):
    if not isinstance(save_path, str):
       save_path = str(save_path.resolve().absolute())
    files = glob.glob(save_path + "/*")
    for file in files:
        if str(eid) in file:
            return file
    raise ValueError("No file found for eid: {}".format(eid))


def generate_shifted_movie(
        plane1_eid,
        output_dir):
    """
    Take two coupled BehaviorOphysExperiments. Generate
    the movies resulting from applying their partner's
    shifts (i.e. the frames in plane1_experiment with the shifts
    from plane2_experiment applied and vice versa)

    Parameters
    ----------
    plane1_eid:
       ophys_experiment_id of plane 1. Coupled plane will be automatically
       detected.

    output_dir:
        directory where the new movies will be written

    Return
    ------
    A dict mapping ophys_experiment_id to the paths to the generated movies
    """
    SHIFTED_H5_SAVE_PATH = pathlib.Path(output_dir)

    # generates the h5 files for BOTH plane1 and plane2 using each
    # others s2p rigid translations
    ppr.generate_all_pairings_shifted_frames(
            eid=plane1_eid,
            save_path=SHIFTED_H5_SAVE_PATH,
            shift_original=False,
            return_frames=False) 

    #above if you change shift original to True,
    # it will generate movies with their own offsets applied

    plane2_eid = ppr.get_paired_plane_id(plane1_eid)

    # find files in save_path that matches plane1_eid and plane2_eid
    plane1_paired_shift_h5file = find_matching_files(
                                    plane1_eid,
                                    SHIFTED_H5_SAVE_PATH)

    plane2_paired_shift_h5file = find_matching_files(
                                    plane2_eid,
                                    SHIFTED_H5_SAVE_PATH)

    return {int(plane1_eid): str(plane1_paired_shift_h5file),
            int(plane2_eid): str(plane2_paired_shift_h5file)}


def run_decrosstalk_offline(
        signal_movie_path,
        signal_roi_list,
        signal_motion_border,
        coupled_movie_path,
        coupled_motion_border):
    """
    Run decrosstalk on a single signal/coupled plane pair
    (does not permute the roles of "signal" and "coupled";
    do that by calling this method twice with reversed parameters)

    Parameters
    ----------
    signal_movie_path: str or pathlib.Path
        path to motion corrected signal plane movie

    signal_roi_list: list of OphysROI objects

    signal_motion_border: dict
        of the form {'x0': int, 'x1': int, 'y0': int, 'y1': int}
        denoting how many pixels to trim from each edge of the field
        of view in the signal plane (if None, defaults all trim
        values to zero)

    coupled_movie_path: str or pathlib.Path
        path to motion corrected coupled plane movie

    coupled_motion_border: dict
        same as signal_motion_border, but for coupled plane

    Returns
    -------
    (These structures are all defined in
     ophys_etl.modules.decrosstalk.decrosstalk_types.py)

    roi_flags -- a dict listing the ROI IDs of ROIs that were
                 ruled invalid for different reasons, namely:

        'decrosstalk_ghost' -- ROIs that are ghosts
        'decrosstalk_invalid_raw' -- ROIs with invalid
                                     raw traces
        'decrosstalk_invalid_raw_active' -- ROIs with invalid
                                            raw active traces
        'decrosstalk_invalid_unmixed' -- ROIs with invalid
                                         unmixed traces
        'decrosstalk_invalid_unmixed_active' -- ROIs with invalid
                                                unmixed active traces
    (raw_traces,
     invalid_raw_traces) -- two decrosstalk_types.ROISetDicts containing
                            the raw trace data for the ROIs and the
                            invalid raw traces
    (unmixed_traces,
     invalid_unmixed_traces) -- two decrosstalk_types.ROISetDicts containing
                                the unmixed trace data for the ROIs and then
                                invalid unmixed traces
    (raw_trace_events,
     invalid_raw_trace_events) -- two decrosstalk_types.ROIEventSets
                                  characterizing the active timestamps
                                  from the raw traces and the invalid
                                  active timestamps
    (unmixed_trace_events,
     invalid_unmixed_trace_events) -- two decrosstalk_types.ROIEventSets
                                      characterizing the active timestamps
                                      from the unmixed traces and the invalid
                                      unmixed trace events

    Notes
    -----
    Return signature is the same as
    ophys_etl.modules.decrosstalk.decrosstalk.run_decrosstalk
    """

    if signal_motion_border is None:
        signal_motion_border = {'x0': 0, 'x1': 0,
                                'y0': 0, 'y1': 0}

    if coupled_motion_border is None:
        coupled_motion_border = {'x0': 0, 'x1': 0,
                                 'y0': 0, 'y1': 0}

    signal_plane = DecrosstalkingOphysPlane(
                experiment_id=0,
                movie_path=signal_movie_path,
                motion_border=signal_motion_border,
                roi_list=signal_roi_list,
                max_projection_path=None,
                qc_file_path=None)

    coupled_plane = DecrosstalkingOphysPlane(
                experiment_id=1,
                movie_path=coupled_movie_path,
                motion_border=coupled_motion_border,
                roi_list = [],
                max_projection_path=None,
                qc_file_path=None)

    result = run_decrosstalk(
                signal_plane=signal_plane,
                ct_plane=coupled_plane)

    return result 


def run(plane1_eid = 1198901240):

    # directory where newly shifted movies will be written
    output_dir = pathlib.Path(
        tempfile.mkdtemp(
            dir='/allen/aibs/informatics/danielsf/scratch/offline_decrosstalk'))

    (plane1_experiment,
     plane2_experiment) = get_plane_objects(plane1_eid=plane1_eid)

    plane2_eid = plane2_experiment.ophys_experiment_id


    # create the movies that have been motion corrected according to
    # their complement shifts; return a lookup table mapping
    # ophys_experiment_id to movie_path
    shifted_path_lookup = generate_shifted_movie(
                            plane1_eid,
                            output_dir=output_dir)


    plane1_rois = serialize_rois(plane1_experiment.roi_masks)
    plane2_rois = serialize_rois(plane2_experiment.roi_masks)

    plane1_path = find_actual_motion_corrected_movie(plane1_eid)
    plane1_path = str(plane1_path.resolve().absolute())

    # NOTE: I did not do the work to figure out where to get the
    # proper motion borders for these experiments.
    # run_decrosstalk_offline is just assigning a placeholder
    # at this point

    result = run_decrosstalk_offline(
                signal_movie_path=plane1_path,
                signal_roi_list=plane1_rois,
                signal_motion_border=None,
                coupled_movie_path=shifted_path_lookup[plane2_eid],
                coupled_motion_border=None)

    return result

if __name__ == "__main__":

    run()
