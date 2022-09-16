#Tool currently returns list of session filepaths in storage that are candidates for deletion
#Currently only published/passed sessions.  Should update to include failed and incomplete sessions 
#that are associated with "published" mouse_ids

import typing
import requests
import pandas as pd

class NAStool():
    def __init__(self,
    nas_credentials: str):
        """Takes txt doc containing NAS credentials and outputs a dictionary containing the relevent info.  
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
        """_summary_

        Returns:
            list: _description_
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


    def nas_query(self, folder) -> dict:
        """Uses requests to login to the NAS storage, query the list of folders being backed up, and return a list of
        folders that have been released by the AllenSDK

        Args:
            credentials (dict): output from credentials_read function containing Synology NAS credentials
            nas_name (str): name of the storage servers (currently either 'ophys_nas' or 'ophys_storage')
            release_list (str): Relative string filepath to a .csv file containing information about released ophys sessions. 
            This data is the result of an AllenSDK query and not currently included in this code
        """    


        response = requests.get("http://"+str(self.ip)+"/webapi/entry.cgi?api=SYNO.FileStation.List&version=2&method=list&additional=%5B%22real_path%22%2C%22size%2Cperm%22%5D&folder_path=%22%2F"+
        folder+
        "%22&_sid="+self.sid)
        return response.json()


    def release_check(self, release_list: str, query_response: dict):
        """Compares the output of a requests query against a list of released sessions, 
        and returns the filepath for each session in the NAS storage that matches the ID of a released session

        Args:
            release_list (str): Relative string filepath to a .csv file containing information about released ophys sessions. 
            This data is the result of an AllenSDK query and not currently included in this code
            query_response (dict): Response from the NAS storage containing list of folders and filepaths.  
            This data is the output of the nas_query function
        """    

        df = pd.read_csv(release_list)
        sessions = df['ophys_session_id'].astype(str).to_list()
        released_backups = []    
        for folder in query_response['data']['files']:
            if folder['name'] in sessions:
                released_backups.append(folder['path'])
        return released_backups


    def nas_logout(self):
        requests.get("http://"+str(self.ip)+"/webapi/auth.cgi?api=SYNO.API.Auth&version=6&method=logout&session=FileStation")
        print('session '+ self.sid+' logged out')

