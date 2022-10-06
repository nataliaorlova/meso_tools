# Sam Seid | September 2022

# Tool currently returns list of session filepaths in storage that are 
# candidates for deletion. 
# Currently only published/passed sessions.  
# Should update to include failed and incomplete sessions
# that are associated with "published" mouse_ids"""

import requests

class NASapi():
    """NAStool interacts with the NAS storage device using http requests on the Synology API.
    Use functions built into this class to login, query the database, and perform operations
    such as deleting data folders
    """
    def __init__(self, nas_credentials: str):
        """Takes txt doc containing NAS credentials, saves them, and logs into the NAS.
        Expected format for txt doc:
        # Device access credentials
        SYNOLOGY_IP=xx.xxx.xx.xx:xxxx
        SYNOLOGY_PORT=xxxx
        SYNOLOGY_USERNAME=x
        SYNOLOGY_PASSWORD=x

        Args:
            cred_path (str): relative string path of txt document containing NAS credentials
        """
        with open(nas_credentials, encoding='UTF-8') as txt_line:
            credentials = txt_line.readlines()
        lines =[]
        for line in credentials[1:]:
            line_split = line.split('=')
            for items in line_split:
                item = items.split('\n')[0]
                lines.append(item)
        keys = lines[::2]
        values = lines[1::2]
        res = {keys[i]: values[i] for i in range(len(keys))}
        self.credentials = res
        self.user = res['SYNOLOGY_USERNAME']
        self.password = res['SYNOLOGY_PASSWORD']
        self.ip = res['SYNOLOGY_IP']

        # login
        response = requests.get("http://"+
        str(self.ip)+
        "/webapi/auth.cgi?api=SYNO.API.Auth&version=2&method=login&account="+str(self.user)+
        "&passwd="+str(self.password)+"&session=FileStation&format=sid", timeout = 5)

        self.sid = str(response.json()['data']['sid'])
        #get hostname
        response = requests.get("http://"+
        self.ip+
        "/webapi/entry.cgi?api=SYNO.FileStation.Info&version=2&method=get&_sid="+
        self.sid, timeout = 5)
        self.hostname = response.json()['data']['hostname']
        self.task_id = None
        self.folders = None

    def nas_folders(self, all_folders: bool = False) -> list:
        """Depending on which NAS host has been logged in,
        will return the list of known folders which contain backup data

        Parameters
        ----------
        all_folders : bool
            False by default, will return only the known folders based on hostname.
            If true, will return all top level folders on NAS

        Returns
        -------
        list
            filepaths to backup data which can be input to NAStool functions
        """

        #get folders within host
        if all_folders is True:
            response = requests.get("http://"+str(self.ip)+
            "/webapi/entry.cgi?api=SYNO.FileStation.Info&version=2&method=get&_sid="+
            self.sid, timeout = 5)
            all_paths = []
            for path in response.json()['data']['shares']:
                all_paths.append(path['additional']['real_path'])
            return all_paths
        else:
            if self.hostname == 'ophys_nas':
                folders = ['meso1_backup/data_backup',
                'meso2_backup/data_backup']
                self.folders = folders
                return folders
            if self.hostname == 'ophys_backup':
                folders = ['meso_backup/data_backup',
                'meso_backup_full/data_backup']
                self.folders = folders
                return folders


    def nas_query(self,
     folder: str) -> dict:
        """Input the NAS folder to walk through, and return dictionary of all
        folders in that directory.

        Parameters
        ----------
        folder : str
            NAS folder path that data is backed up in

        Returns
        -------
        dict
            Filepaths to backup data which can be input to NAStool functions
        """
        response = requests.get("http://"+str(self.ip)+
        "/webapi/entry.cgi?api=SYNO.FileStation.List&version=2&method=list"+
        "&additional=%5B%22real_path%22%2C%22size%2Cperm%22%5D&folder_path=%22%2F"+
        folder+
        "%22&_sid="+self.sid, timeout = 5)
        return response.json()


    def release_check(self, sessions: list, query_response: dict) -> list:
        """
        Compares the output of a requests query against a list of released sessions,
        and returns the filepath for each session in the NAS storage that matches
        the ID of a released session

        Parameters
        ----------
        sessions : list
             List of ophys session IDs to compare against NAS folders
        query_response : dict
            Response from the NAS storage containing list of folders and filepaths.
            This data is the output of the nas_query function

        Returns
        -------
        list
            NAS filepaths to each folder with a name matching a session ID in the release list
        """
        released_backups = []
        for folder in query_response['data']['files']:
            if folder['name'] in sessions:
                released_backups.append(folder['path'])
        return released_backups

    def nas_delete(self, delete_item: str, delete: bool = True):
        """Deletes NAS folders from a list of filepaths

        Parameters
        ----------
        delete_item : list
            List of NAS filepaths to delete, by default will use the released_backups
            calculated in the release check function
        delete: bool, True by default
            Determines wether the call to this function will actually delete
        """
        print('deleting '+str(delete_item))
        if delete is True:
            #start deletion
            response = requests.get("http://"+self.ip+
            "/webapi/entry.cgi?api=SYNO.FileStation.Delete&version=2&method=start&path=%22%2F"+
            str(delete_item[1:])+"%22&_sid="+self.sid, timeout = 5)
            #save task id for the current deletion job
            task_id = response.json()['data']['taskid']
            #store task ID's for later in case we need to stop a job
            self.task_id = task_id

    def nas_stop(self):
        """Stop deleting jobs.  Only stops the most recent call to nas_delete.
        """
        task_id = self.task_id
        requests.get("http://"+self.ip+
        "/webapi/entry.cgi?api=SYNO.FileStation.Delete&version=2&method=stop&taskid=%22"+
        str(task_id)+"%22&_sid="+self.sid, timeout = 5)

    def nas_status(self) -> dict:
        """Check status of current deletion job

        Returns
        -------
        list
            returns dictionary containig the response of the deletion status query
        """

        task_id = self.task_id
        response = requests.get("http://"+self.ip+
        "/webapi/entry.cgi?api=SYNO.FileStation.Delete&version=2&method=status&taskid=%22"+
        str(task_id)+"%22&_sid="+self.sid, timeout = 5)

        return response


    def recycle_empty(self, folder: str, delete: bool = True):
        """Empty the recycle bin for a selected folder

        Parameters
        ----------
        folder : str
            filepath to the top level directory from which you deleted files from
        delete: bool, default to True
            Determine wether call to this function will actually delete files
        """

        path = folder.split('/')
        path.insert(1, '#recycle')
        path = '/'.join(path)
        print(f'Emptying {path} from NAS recycle bin')
        if delete is True:
            #start deletion
            response = requests.get("http://"+self.ip+
            "/webapi/entry.cgi?api=SYNO.FileStation.Delete&version=2&method=start&path=%22%2F"+
            str(path)+"%22&_sid="+self.sid, timeout = 5)
            #save task id for the current deletion job
            task_id = response.json()['data']['taskid']
            #store task ID's for later in case we need to stop a job
            self.task_id = task_id


    def nas_logout(self):
        """Log out of the connection to NAS server
        """
        requests.get("http://"+str(self.ip)+
        "/webapi/auth.cgi?api=SYNO.API.Auth&version=6&method=logout&session=FileStation",
         timeout = 5)
        print('session '+ self.sid+' logged out')
