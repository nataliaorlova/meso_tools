#Tool currently returns list of session filepaths in storage that are candidates for deletion
#Currently only published/passed sessions.  Should update to include failed and incomplete sessions 
#that are associated with "published" mouse_ids

import typing
import requests
import pandas as pd

class NAStool():
    """NAStool interacts with the NAS storage device using http requests on the Synology API.  Use functions built into
    this class to login, query the database, and perform operations such as deleting a list of folder paths
    """    
    def __init__(self,
    nas_credentials: str):
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
        with open(nas_credentials) as f:
            credentials = f.readlines()
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
        "&passwd="+str(self.password)+"&session=FileStation&format=sid")

        self.sid = str(response.json()['data']['sid'])
        #get hostname
        response = requests.get("http://"+
        self.ip+
        "/webapi/entry.cgi?api=SYNO.FileStation.Info&version=2&method=get&_sid="+self.sid)
        self.hostname = response.json()['data']['hostname']


    def nas_folders(self) -> list:
        """Depending on which NAS host has been logged in, 
        will return the list of known folders which contain backup data

        Returns:
            list: filepaths to backup data which can be input to NAStool functions
        """  

        #get folders within host

        if self.hostname == 'ophys_nas':
            folders = ['meso1_backup/data_backup',
            'meso2_backup/data_backup']
            return folders
        if self.hostname == 'ophys_backup':
            folders = ['meso_backup/data_backup',
            'meso_backup_full/data_backup']
            return folders


    def nas_query(self, folder: str) -> dict:
        """Input the NAS folder to walk through, and return dictionary of all folders in that directory.

        Args:
            folder (str): NAS folder path that data is backed up in.
        Returns:
            dict: filepaths to backup data which can be input to NAStool functions
        """    


        response = requests.get("http://"+str(self.ip)+"/webapi/entry.cgi?api=SYNO.FileStation.List&version=2&method=list&additional=%5B%22real_path%22%2C%22size%2Cperm%22%5D&folder_path=%22%2F"+
        folder+
        "%22&_sid="+self.sid)
        return response.json()


    def release_check(self, release_list: str, query_response: dict) -> list:
        """Compares the output of a requests query against a list of released sessions, 
        and returns the filepath for each session in the NAS storage that matches the ID of a released session

        Args:
            release_list (str): Relative string filepath to a .csv file containing information about released ophys sessions. 
            This data is the result of an AllenSDK query and not currently included in this code
            query_response (dict): Response from the NAS storage containing list of folders and filepaths.  
            This data is the output of the nas_query function
        Returns:
            list: NAS filepaths to each folder with a name matching a session ID in the release list
        """    

        df = pd.read_csv(release_list)
        sessions = df['ophys_session_id'].astype(str).to_list()
        released_backups = []    
        for folder in query_response['data']['files']:
            if folder['name'] in sessions:
                released_backups.append(folder['path'])
        self.released_backups = released_backups
        return released_backups

    def nas_delete(self, delete_list = None):
        """Deletes NAS folders from a list of filepaths
        """   
        if delete_list == None:
            delete_list = self.released_backups  
        task_dict = {}
        for output in delete_list:
            print('deleting '+str(output))
            #start deletion
            response = requests.get("http://"+self.ip+"/webapi/entry.cgi?api=SYNO.FileStation.Delete&version=2&method=start&path=%22%2F"+str(output[1:])+"%22&_sid="+self.sid)
            #save task id for the current deletion jobs
            task_dict[output.split('/')[-1]]=response.json()['data']['taskid']
        #store task ID's for later in case we need to stop a job
        self.task_ids = task_dict

    def nas_stop(self):
        """Stop deleting jobs.  Only stops the most recent call to nas_delete.
        """       
        task_dict = self.task_ids
        for key in task_dict: 
            task_id = task_dict[key]
            response = requests.get("http://"+self.ip+"/webapi/entry.cgi?api=SYNO.FileStation.Delete&version=2&method=stop&taskid=%22"+str(task_id)+"%22&_sid="+self.sid)
    
    def nas_status(self) -> list:
        """Check status of current deletion job

        Returns:
            list: returns list of dictionaries containig the response of the deletion status query
        """        
        task_dict = self.task_ids
        response_list = []
        for key in task_dict: 
            task_id = task_dict[key]
            response = requests.get("http://"+self.ip+"/webapi/entry.cgi?api=SYNO.FileStation.Delete&version=2&method=status&taskid=%22"+str(task_id)+"%22&_sid="+self.sid)
            response_list.append(response.json())

        return response_list

    def nas_logout(self):
        """Log out of the connection to NAS server
        """        
        requests.get("http://"+str(self.ip)+"/webapi/auth.cgi?api=SYNO.API.Auth&version=6&method=logout&session=FileStation")
        print('session '+ self.sid+' logged out')

