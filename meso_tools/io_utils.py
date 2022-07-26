## this file has input/output related functions
### reading/writing tiff, hdf5s, reading metadata

import tifffile
import h5py
import pandas as pd
from allensdk.internal.api import PostgresQueryMixin

def read_tiff(path_to_tiff, page_num=None):
    """ reads either entire tiff file, or if n is given, N pages of it
        path_to_tiff: str: local path to the tifffile
        page_num : int or list of 2 ints: number of pages to read, 
        if none provided will atempt to read entire tiff file. 
        Will limlit to 5000 if tiff has more that 5000 pages.
        if list of 2 ints - will read pages fomr int 1 to int 2
    Return:
        tiff_array: 3D numpy array representing timeseries that was read
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
                print(f"This timeseries has more than 5000 frames to not overload RAM, we will only read 5000 first pages.")
                print(f"To read more pages,in case large amount of RAM is available, provide number of pages to read by calling read_tiff(path_to_tiff, page_num=value)")
                page_num = 5000
                tiff_array = tiff.asarray(range(0, page_num))
            else:
                tiff_array = tiff.asarray()
    return tiff_array

def write_tiff(path, data):
    tifffile.imsave(path, data)
    return

def read_h5(path, field):
    """
    function to read a field form hdf5 file, wrapping h5py
    :param path: path to hdf5 file
    :param field: datafield to read
    :return: raed data
    """
    with h5py.File(path, "r") as f:
        data = f[field][()]
    return data

def write_h5(path, h5_data):
    with h5py.File(path, 'w') as f:
        f.create_dataset('data', data=h5_data)
    return

def read_si_metadata(path_to_tiff):
    """
    function to read scnaimage metadata in full
    path: path to tiff file
    returns: dict w metadata
    """
    meta_data = tifffile.read_scanimage_metadata(open(path_to_tiff, 'rb'))
    return meta_data

def get_roi_data(path_to_tiff):
    """
    function to read scnaimage metadata's ROI structure part
    path: path to tiff file
    returns: dict w metadata
    """
    meta_data = tifffile.read_scanimage_metadata(open(path_to_tiff, 'rb'))
    return meta_data[1]

def load_motion_corrected_movie(filepath, pages=None):
    """load motion correctionmovie : whole or some pages
    filepath :  str : absolute path to teh hdf5 file with movie
    pages :  int : number of pages to load, if given
    return : loaded movie as a 3D numpy array
    """
    with h5py.File(filepath, 'r') as motion_corrected_movie_file:
        if not pages:        
            motion_corrected_movie = motion_corrected_movie_file['data']
        elif pages > 0:
            motion_corrected_movie = motion_corrected_movie_file['data'][:pages]
        else: 
            motion_corrected_movie = motion_corrected_movie_file['data'][pages:]
    return motion_corrected_movie

class LimsApi():
    def __init__(self, lims_credentials):
        self.lims_db = PostgresQueryMixin(
            dbname=lims_credentials['dbname'], user=lims_credentials['user'],
            host=lims_credentials['host'], password=lims_credentials['password'],
            port=lims_credentials['port'])
        
    def get_exp_folder(self, exp_id):
        """get path to the storage directory for given experiment id
        """
        query = f"""SELECT
                    oe.storage_directory as experiment_folder
                    FROM ophys_experiments oe
                    WHERE oe.id={exp_id}"""
        exp_folder_pd = pd.read_sql(query, self.lims_db.get_connection())
        if len(exp_folder_pd) != 0:
            return exp_folder_pd.experiment_folder[0]
        else: print(f"can't find folder for experiment {exp_id}")
            
    def get_motion_corrected_stack(self, exp_id):
        """get path to the motion corrected stack for given experiment id
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
    
    def get_all_table_columns(self, table_name):
        """get all columns in given LIMS table
        """
        query = (f"""SELECT * FROM {table_name} WHERE 1=0""")
        table_columns = pd.read_sql(query, self.lims_db.get_connection())
        return table_columns.columns.values

    def get_all_distinct_values_in_column(self, table, column):
        """get all distinct values in column/table
        """
        query = (f"""SELECT {column} FROM {table} GROUP BY {column} """)
        return pd.read_sql(query, self.lims_db.get_connection())

    def get_experiments_in_project(self, project):
        """get alal epxeriments, their deths and specimen name for given project code
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
        return pd.read_sql(query, self.lims_db.get_connection())

    def get_all_lims_tables(self):
        query = """SELECT table_name
                FROM information_schema.tables
                WHERE table_schema='public'
                AND table_type='BASE TABLE';"""
        tables = pd.read_sql(query, self.lims_db.get_connection()).table_name.values
        return tables        