# Sam Seid | September 2022

# This script is used to clean up space on ophys backup drives
# it will read csv files containing data about releases, 
#  - get session IDs from there for the data that's been released 
#  - read folder structure in specified NASs
#  - compare what's on NAS to what's been released
#  - delete all backups of released data  

from ..NAS_tools import NASapi
import pandas as pd

# sessions to delete
# files with released data 
csv1 = r""
# additional released mice not in csv1 
csv2 = r""

# NAS login credentials
cred = r""
cred2 = r""

# pull session list
df1 = pd.read_csv(csv1)
df2 = pd.read_csv(csv2)
session_list = []
session_list.extend(df1.ophys_session_id.astype(str).to_list())
session_list.extend(df2.ophys_session_id.astype(str).to_list())

# code below will delete
api = NASapi(cred)
folders = api.nas_folders()

for folder in folders:
    check = api.nas_query(folder)
    check2 = api.release_check(session_list, check)
    for item in check2:
        api.nas_delete(item)

api = NASapi(cred2)
folders = api.nas_folders()
for folder in folders:
    check = api.nas_query(folder)
    check2 = api.release_check(session_list, check)
    for item in check2:
        api.nas_delete(item)