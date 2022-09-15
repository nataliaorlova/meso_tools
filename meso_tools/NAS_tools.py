#Tool currently returns list of session filepaths in storage that are candidates for deletion
#Currently only published/passed sessions.  Should update to include failed and incomplete sessions 
#that are associated with "published" mouse_ids

import typing
import requests
def credential_read(cred_path: str):
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

    with open(cred_path) as f:
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
    return(res)

def nas_query(credentials: dict, nas_name: str, release_list: str):
    """Uses requests to login to the NAS storage, query the list of folders being backed up, and return a list of
    folders that have been released by the AllenSDK

    Args:
        credentials (dict): output from credentials_read function containing Synology NAS credentials
        nas_name (str): name of the storage servers (currently either 'ophys_nas' or 'ophys_storage')
        release_list (str): Relative string filepath to a .csv file containing information about released ophys sessions. 
        This data is the result of an AllenSDK query and not currently included in this code
    """    

    user = credentials['SYNOLOGY_USERNAME']
    password = credentials['SYNOLOGY_PASSWORD']
    ip = credentials['SYNOLOGY_IP']

    # login
    response = requests.get("http://"+str(ip)+"/webapi/auth.cgi?api=SYNO.API.Auth&version=2&method=login&account="+str(user)+ 
        "&passwd="+str(password)+"&session=FileStation&format=sid")
    sid = (response.json()['data']['sid'])
    if nas_name == 'ophys_nas':
        #folder 1
        response = requests.get("http://"+str(ip)+"/webapi/entry.cgi?api=SYNO.FileStation.List&version=2&method=list&additional=%5B%22real_path%22%2C%22size%2Cperm%22%5D&folder_path=%22%2Fmeso2_backup/Data_Backup%22&_sid="+sid)        
        released_backups = release_check(release_list, response)
        
        #folder 2
        response = requests.get("http://"+str(ip)+"/webapi/entry.cgi?api=SYNO.FileStation.List&version=2&method=list&additional=%5B%22real_path%22%2C%22size%2Cperm%22%5D&folder_path=%22%2Fmeso1_backup/Data_Backup%22&_sid="+sid)
        released_backups2 = release_check(release_list, response)
    elif nas_name == 'ophys_backup':

        #folder 1
        response = requests.get("http://"+str(ip)+"/webapi/entry.cgi?api=SYNO.FileStation.List&version=2&method=list&additional=%5B%22real_path%22%2C%22size%2Cperm%22%5D&folder_path=%22%2Fmeso_backup_full/data_backup%22&_sid="+sid)
        released_backups = release_check(release_list, response)
        #folder 2
        response = requests.get("http://"+str(ip)+"/webapi/entry.cgi?api=SYNO.FileStation.List&version=2&method=list&additional=%5B%22real_path%22%2C%22size%2Cperm%22%5D&folder_path=%22%2Fmeso_backup/data_backup%22&_sid="+sid)
        released_backups2 = release_check(release_list, response)          
    else:
        print('NAS name not valid')
        released_backups = []
        released_backups2 = []
    # logout

    requests.get("http://"+str(ip)+"/webapi/auth.cgi?api=SYNO.API.Auth&version=6&method=logout&session=FileStation")
    return(released_backups, released_backups2)
            
def release_check(release_list: str, query_response: requests.models.Response):
    """Compares the output of a requests query against a list of released sessions, 
    and returns the filepath for each session in the NAS storage that matches the ID of a released session

    Args:
        release_list (str): Relative string filepath to a .csv file containing information about released ophys sessions. 
        This data is the result of an AllenSDK query and not currently included in this code
        query_response (requests.models.Response): Response from the NAS storage containing list of folders and filepaths.  
        This data is the output of the nas_query function
    """    
    import pandas as pd
    df = pd.read_csv(release_list)
    sessions = df['ophys_session_id'].astype(str).to_list()
    released_backups = []    
    for folder in query_response.json()['data']['files']:
        if folder['name'] in sessions:
            released_backups.append(folder['path'])
    return(released_backups)

