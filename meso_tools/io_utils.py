## this file has input/output related functions
### reading/writing tiff, hdf5s, reading metadata

from typing import Any, Union
import tifffile
import h5py
import pandas as pd
import numpy as np
import os
from allensdk.internal.api import PostgresQueryMixin
from typing import Tuple

def read_tiff(path_to_tiff : str, page_num : int = None) -> np.array:
    """
    Reads either entire tiff file, or if page_num is given, only those pages or pages range
    Parameters
    -------
    path_to_tiff : str
        local path to the tiff file
    page_num : int or [int, int]
        number of pages to read, if none provided will atempt to read entire tiff file.
        Will limlit to 5000 if tiff has more that 5000 pages.
        if list of 2 ints, a range, - will read pages from the range
    Returns
    -------
    tiff_array : np.array
        numpy array representing timeseries that was read
    """
    with tifffile.TiffFile(path_to_tiff, mode ='rb') as tiff:
        if page_num:
            if isinstance(page_num, list):
                #read pages from range
                tiff_array = tiff.asarray(range(page_num[0], page_num[1]))
            else:
                tiff_array = tiff.asarray(range(0, page_num))
        else: # number of pages is not provided:
            if len(tiff.pages) >=5000:
                print("This timeseries has more than 5000 frames to not overload RAM, we will only read 5000 first pages.")
                print("To read more pages, in case large amount of RAM is available, provide number of pages to read by calling read_tiff(path_to_tiff, page_num=value)")
                page_num = 5000
                tiff_array = tiff.asarray(range(0, page_num))
            else:
                tiff_array = tiff.asarray()
    return tiff_array


def write_tiff(path_to_tiff : str, data : np.array) -> None:
    """
    Writes tif file to disk
    Parameters
    -------
    path_to_tiff : str
        local path to the tiff file
    data : np.Array
        Numpy array representing a tiff file to be saved
    Returns
    -------
        None
    """
    tifffile.imsave(path_to_tiff, data)

def read_h5(path_to_h5 : str, field : str) -> Any:
    """
    Read a field from hdf5 file, wrapping h5py
    Parameters
    -------
    path_to_h5: str
        path to hdf5 file
    field : str
        datafield to read
    Returns
    -------
    data : any
        data contained in the given field of the h5 file
    """  
    with h5py.File(path_to_h5, "r") as h5_file:
        fields = h5_file.keys()
        if field not in fields:
            print("Specified field is not in h5 file")
            return None
        data = h5_file[field][()]
    return data

def write_h5(path : str, h5_data : Any) -> None:
    """
    Writes to disk file in hdf5 format, wrapper for h5py
    Parameters
    ----------
    path : str
        Absolute path to file to eb saved
    h5_data : Any
        Data to write to file
    """
    with h5py.File(path, 'w') as h5_file:
        h5_file.create_dataset('data', data=h5_data)


def read_scanimage_metadata(path_to_tiff : str) -> dict:
    """
    Read ScanImage metadata
    Parameters
    ----------
    path_to_tiff : str
        tiff file whose metadata needs to be read

    Returns
    -------
    meta_data : dict
        disctionary with metadata
    """
    meta_data = tifffile.read_scanimage_metadata(open(path_to_tiff, 'rb'))
    return meta_data

def get_roi_data(path_to_tiff : str) -> dict:
    """
    Read scanimage metadata's ROI structure part
    Parameters
    ----------
    path_to_tiff : str
        Path to tiff file
    Returns
    -------
    meta_data : dict
        dict w metadata
    """    
    meta_data = tifffile.read_scanimage_metadata(open(path_to_tiff, 'rb'))
    return meta_data[1]

def load_motion_corrected_movie(filepath : str, page_num : list = None) -> np.array:
    """
    Load motion corrected movie as numpy array as a whole or range of pages
    Parameters
    ----------
    filepath : str
        absolute path to teh hdf5 file with movie
    page_num : list, optional
        number of pages to load or tuple wiht range of images to load

    Returns
    -------
    motion_corrected_movie : np.Array
        loaded movie as a 3D numpy array
    """    
    with h5py.File(filepath, 'r') as motion_corrected_movie_file:
        if not page_num:        
            motion_corrected_movie = motion_corrected_movie_file['data']
        elif isinstance(page_num, list):
            motion_corrected_movie = motion_corrected_movie_file['data'][page_num[0]:page_num[1]]
        elif page_num > 0:
            motion_corrected_movie = motion_corrected_movie_file['data'][:page_num]
        else: 
            motion_corrected_movie = motion_corrected_movie_file['data'][page_num:]
    return motion_corrected_movie

def get_movie_shape(filepath : str) -> Tuple:
    """
    Get movie's shape
    Parameters
    ----------
    filepath : str
        absolute path to teh hdf5 file with movie
    Returns
    -------
    movie_shape : Tuple
        shape of the movie 
    """    
    assert isinstance(filepath, str), "Filepath should be string"
    assert os.path.isfile(filepath), "Filepath is incorrect"

    with h5py.File(filepath, 'r') as motion_corrected_movie_file:
        movie_shape = motion_corrected_movie_file['data'].shape
    return movie_shape

def read_scanimage_stack_metadata(metadata : dict) -> dict:
    """
    read_scanimage_stack_metadata reads of the relevant metadata fields

    Parameters
    ----------
    metadata : dict
        Dictionary that contains full ScanImage etadata dictionary 

    Returns
    -------
    dict
        stripped down dict wiht emetadata for stack only
    """
    md_general = metadata[0]
    stack_metadata = {}
    # stack params
    stack_metadata['num_slices'] = md_general['SI.hStackManager.actualNumSlices']
    stack_metadata['num_volumes'] = md_general['SI.hStackManager.actualNumVolumes']
    stack_metadata['z_step'] = md_general['SI.hStackManager.actualStackZStepSize']
    stack_metadata['all_zs'] = np.asarray(md_general['SI.hStackManager.zsAllActuators'])[:,1]
    stack_metadata['frames_per_slice'] = md_general['SI.hStackManager.framesPerSlice']
    #flag properties:
    stack_metadata['channel_save'] = md_general['SI.hChannels.channelSave']
    stack_metadata['stack_type'] = md_general['SI.hStackManager.stackDefinition']

    return stack_metadata

def read_scanimage_stack(tiff_path : str, stack_meta : dict, slices : int = None, volumes : int = None) -> np.array:
    """
    read_scanimage_stack reads ScanImage stack from file
    Parameters
    ----------
    tiff_path : str
        paht to tiff file w stack
    stack_meta : dict
        disctionary wiht stack parameters
    slices : int, optional
        slices(planes) to read, if None - read all, by default None
    volumes : int, optional
        volumes (repeats of the stack) to read, if None - read all, by default None

    Returns
    -------
    np.array
        stack read as numpy array
    """
    total_slices = stack_meta['num_slices']
    total_volumes = stack_meta['num_volumes']
    
    if not slices:
        slices = total_slices
        
    if not volumes:
        volumes = total_volumes
        
    frames_to_read = []
    for repeat in range(volumes):
        frames_to_read += list(np.linspace(repeat*total_slices,repeat*total_slices+slices,slices))

    with tifffile.TiffFile(tiff_path, mode ='rb') as tiff:
        stack = tiff.asarray(frames_to_read)
    
    return stack

def append_suffix_to_filename(filename : str, suffix : str) -> str :
    """
    append_suffix_to_filename 

    Parameters
    ----------
    filename : str
        filename to change by adding suffix before extension 
    suffix : str
        suffix to append

    Returns
    -------
    str
        filename wihta ppended suffix
    """
    basename = os.path.splitext(filename)[0]
    extension = os.path.splitext(filename)[1]
    return f"{basename}_{suffix}_{extension}"


def read_plane_in_stack(stack_path : str, plane_num : int, slices : int) -> np.array :
    """
    read_plane_in_stack returns a timeseries corresponding to one plane fomr a stack with multiple repeats

    Parameters
    ----------
    stack : str
        local path to stack
    repeats : int
        number of reepats of teh stak in np array
    slices:
        number of planes in stack
    Returns
    -------
    np.array
        output stack, aka timeseries
    """
    with tifffile.TiffFile(stack_path, mode ='rb') as tiff:
        tot_frames = len(tiff.pages)
        actual_repeats = np.divmod(tot_frames, slices)[0]
        pages_to_read = np.arange(plane_num, slices*actual_repeats+plane_num, slices)
        stack_plane = tiff.asarray(pages_to_read)

    new_filepath = append_suffix_to_filename(stack_path, f'plane{plane_num}')
    write_tiff(new_filepath, stack_plane)
    return stack_plane, actual_repeats

class LimsApi():
    """
    Class with simple queries to LIMS database, must have access to the credentials and read it prior to instantiating the class
    """
    def __init__(self, lims_credentials : dict):
        """
        Parameters
        ----------
        lims_credentials : dict
            disctionary with database access credentials
        """
        self.lims_db = PostgresQueryMixin(
            dbname=lims_credentials['dbname'], user=lims_credentials['user'],
            host=lims_credentials['host'], password=lims_credentials['password'],
            port=lims_credentials['port'])
        
    def get_exp_folder(self, exp_id : int) -> Union[str, None]:      
        """
        Get path to the storage directory for given experiment id, via a direct query to LIMS
        Parameters
        ----------
        exp_id : int
            Experiment ID assigned in LIMS
        Returns
        -------
        Union[str, None]
            path to experimental folder, if exists, or None
        """        
        query = f"""SELECT
                    oe.storage_directory as experiment_folder
                    FROM ophys_experiments oe
                    WHERE oe.id={exp_id}"""
        exp_folder_pd = pd.read_sql(query, self.lims_db.get_connection())
        if len(exp_folder_pd) != 0:
            path = exp_folder_pd.experiment_folder[0]
            return path
        else: print(f"Can't find folder for experiment {exp_id}")
            
    def get_motion_corrected_stack(self, exp_id : int) -> Union[str, None]:
        """
        Get path to the motion corrected stack for given experiment ID via a direct query to LIMS

        Parameters
        ----------
        exp_id : int
            Experiment ID assigned in LIMS

        Returns
        -------
        Union[str, None]
            path to motion corrected stack, if exists, or None
        """
        query = f"""SELECT wkf.storage_directory || wkf.filename AS mc_stack_file
                    FROM ophys_experiments oe
                    JOIN well_known_files wkf ON wkf.attachable_id = oe.id
                    JOIN well_known_file_types wkft
                    ON wkft.id = wkf.well_known_file_type_id
                    WHERE wkf.attachable_type = 'OphysExperiment'
                    AND wkft.name = 'MotionCorrectedImageStack'
                    AND oe.id = {exp_id};
                    """
        mc_file = pd.read_sql(query, self.lims_db.get_connection())
        if len(mc_file) != 0:
            return mc_file.mc_stack_file[0]
        else: print(f"can't find motion corrected stack for experiment {exp_id}")
    
    def get_all_table_columns(self, table_name : str) -> Union[list, None]:
        """
        Get all columns in given LIMS table via a direct query to LIMS
        Parameters
        ----------
        table_name : str
            Name of the LIMS table
        Returns
        -------
        Union[str, None]
            list of strings with names of all columns, or None
        """        
        query = (f"""SELECT * FROM {table_name} WHERE 1=0""")
        table_columns = list(pd.read_sql(query, self.lims_db.get_connection()).keys())
        if len(table_columns) == 0:
            print(f"table {table_name} has no columns")
            return None
        return table_columns
        
    def get_all_distinct_values_in_column(self, table, column):
        """
        Get all distinct values in column/table via a direct query to LIMS
        Parameters
        table : string
            name of lims table
        column :  string
            name of column in table
        -------
        Returns
        columns: : list [string, string, string]
            list of column names
        -------
        """
        query = (f"""SELECT {column} FROM {table} GROUP BY {column} """)
        df = pd.read_sql(query, self.lims_db.get_connection())

        columns= list(df.values)
        return columns

    def get_experiments_in_project(self, project : str) -> pd.DataFrame:
        """
        Get all experiments, their deths and specimen name for given project code via a direct query to LIMS
        Parameters
        ----------
        project : str
            Project code from LIMS
        Returns
        -------
        pd.DataFrame
            dataframe with following columns : exp_id, session_id, container_id, depth, specimen
        """
        query = f"""SELECT 
                    oe.id AS exp_id,
                    os.id AS session_id,
                    oevbec.visual_behavior_experiment_container_id AS container_id,
                    imaging_depths.depth AS depth,
                    specimens.name AS specimen
                    FROM ophys_experiments oe  
                    JOIN imaging_depths ON imaging_depths.id = oe.imaging_depth_id
                    JOIN ophys_sessions os ON oe.ophys_session_id = os.id
                    JOIN specimens ON os.specimen_id = specimens.id
                    JOIN projects p ON p.id = os.project_id
                    JOIN ophys_experiments_visual_behavior_experiment_containers oevbec ON oevbec.ophys_experiment_id = oe.id
                    WHERE p.code = '{project}' AND oe.workflow_state = 'passed' ;"""
        df = pd.read_sql(query, self.lims_db.get_connection())
        return df

    def get_all_lims_tables(self) -> list:
        """
        Get all tables of LIMS
        Returns
        -------
        list:
            List of tables
        """
        query = """SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema='public'
                    AND table_type='BASE TABLE';"""
        tables = list(pd.read_sql(query, self.lims_db.get_connection()).table_name.values)
        return tables   

    def get_sessions_per_mouse_id(self, mouse_id : int) -> pd.DataFrame:
        """
        Get all sessions and experiments per given mouse_id via a direct query to LIMS
        Parameters
        ----------
        mouse_id : int
            LabTracks mouse ID from specimens table, specimens.external_specimen_id
        Returns
        -------
        dataframe : pd.dataframe
            pandas dataframe woth columns [mouse_id, session_id, experiment_id, container_id]
        """
        query = f"""SELECT
                    sp.external_specimen_name as mouse_id,
                    os.id AS session_id,
                    oe.id AS exp_id,
                    oevbec.visual_behavior_experiment_container_id AS container_id
                    FROM specimens sp 
                    JOIN ophys_sessions os ON os.specimen_id = sp.id
                    JOIN ophys_experiments oe ON oe.ophys_session_id = os.id
                    JOIN ophys_experiments_visual_behavior_experiment_containers oevbec ON oevbec.ophys_experiment_id = oe.id
                    WHERE sp.external_specimen_name = '{mouse_id}'"""
        return pd.read_sql(query, self.lims_db.get_connection())  

    def get_roi_number_per_experiment(self, exp_id : int) -> int:
        """
        Get number of segmenter ROIs given experiment ID via a direct query to LIMS
        Parameters
        ----------
        exp_id  : str
            Experiment ID assigned in LIMS
        Returns
        -------
        num_rois : int
            Number of Segmented ROIs
        """
        query = f"""SELECT
                    cr.id as roi_id
                    FROM cell_rois cr 
                    JOIN ophys_experiments oe ON oe.id = cr.ophys_experiment_id
                    WHERE oe.id = '{exp_id}'"""
        rois = pd.read_sql(query, self.lims_db.get_connection()).values
        num_rois = len(rois)
        return num_rois

    def get_experiment_depth(self, exp_id : str) -> int:
        """
        Get imaging depth for given exeriment ID via a direct query to LIMS
        Parameters
        ----------
        exp_id  : str
            Experiment ID assigned in LIMS
        Returns
        -------
        depth : int
            Imaging depth
        """
        query = f"""SELECT
                    oe.calculated_depth as depth
                    FROM ophys_experiments oe 
                    WHERE oe.id = '{exp_id}'"""
        depth = pd.read_sql(query, self.lims_db.get_connection()).values[0][0]
        return depth

    def get_experiment_line(self, exp_id : int) -> tuple:
        """
        Get Cre line for given experiment ID via a direct query to LIMS
        Parameters
        ----------
        exp_id : int
            experiment ID assigned in LIMS
        Returns
        -------
        tuple(str, str):
            cre : str
                Cre line
            mouse_id : int
                Mouse ID assigned in LIMS 
        """
        query = f"""SELECT
                    sp.name as name
                    FROM ophys_experiments oe 
                    JOIN ophys_sessions os ON oe.ophys_session_id = os.id
                    JOIN specimens sp ON sp.id = os.specimen_id
                    WHERE oe.id = '{exp_id}'"""
        line = pd.read_sql(query, self.lims_db.get_connection()).values[0][0]
        cre = line.split('-')[0]
        mouse_id = line.split('-')[-1]
        return (cre, mouse_id)
    
    def get_fullfile_raw_path(self, sessions_id: int) -> str or None:
    """
    get_fullfile_raw_path returns filepath in windwos format to the raw tiff file containing unstitched fullfield stack

    Parameters
    ----------
    sessions_id : int
        LIMS sessions ID

    Returns
    -------
    str
        path to file
    """
    
    query = f"""SELECT 
            os.id, 
            os.storage_directory
            FROM ophys_sessions os
            WHERE os.id = '{session_id}'"""
    #get sessions directory in lims
    session_directory = pd.read_sql(query, lapi.lims_db.get_connection())['storage_directory'].values[0]
    #reformat filepath for windwos:
    session_directory = session_directory.replace('/', '\\')
    session_directory = session_directory.replace('\\allen', '\\\\allen')
    #get all files in sessions dir
    files = os.listdir(session_directory)
    #find file for fullfield stack
    for index, file in enumerate(files):
            if 'fullfield.tiff' in file:
                file_index = index
    #return paht if it exists, or None if not
    try:
        path = os.path.join(session_directory, files[file_index])
    except:
        path = None
        print('No fullfield for '+str(session_id))
    return path

