#!/usr/bin/python
import requests
import json
import logging

url = 'https://cds-aws-bundles.netapp.com:8080/v1'
headers = {'content-type':'application/json',
           'api-key':'b2hpT0liU1Y1Y2hYZWVyWlJCcTh3UXpzRjI5M0pk',
           'secret-key':'NkVsb1lMS3lNZHc3VHhjeTNwNnVtRmJwZ1NjVmpE'}

#############
# Primary Code #
'''
Get the the json object for working with again and again
'''
def get_json_object( command = None, headers = None, mount = None, url = None):
    r = requests.get(url + '/' + command,headers=headers)
    return r.status_code,r.json()

'''
For now exit if error code != 200
'''
def error_check(status_code = None): 
    if status_code != 200:
        print('Something went wrong with API request, Error Code: %s' % (status_code))
        exit()

'''
get the hash of file system ids associated with creation tokens
key == export name
value == [filesystem id, index position inside base json object]
return == hash of export names : [filesystem id, index position]
'''
def create_export_to_fsid_hash(filesystems=None,json_object=None):
    fs_hash = {}
    if filesystems is not None:
        for mount in filesystems:
            for idx in range(0,len(json_object)):
                if mount == json_object[idx]['creationToken']:
                    fs_hash = add_volumes_to_fs_hash(json_object = json_object, index = idx, mount = mount, fs_hash = fs_hash)
    else:
        for idx in range(0,len(json_object)):
            mount = json_object[idx]['creationToken']
            fs_hash = add_volumes_to_fs_hash(json_object = json_object, index = idx, mount = mount, fs_hash = fs_hash)
    return fs_hash


'''
Add File system information to fs_hash, then pass hash back
FilesystemInfo == hash containing filesysteminfo from SDK for a specific volume
Index == the index within the higher level filesystem info dump, use this later on rather than having to crawl the json object
'''
def add_volumes_to_fs_hash(json_object = None, index = None, mount = None, fs_hash = None):
    fs_hash[mount] = {}
    fs_hash[mount]['FileSystemInfo'] = {'FileSystemId':json_object[index]['fileSystemId']}
    fs_hash[mount]['index'] = {'index':index}
    return fs_hash
    

'''
prettify the passed in hash for printing
'''
def pretty_hash(my_hash=None):
    print json.dumps(my_hash,
                     sort_keys = True,
                     indent = 4,
                     separators = (',', ': ')) 

#############
# Volume Code

# Get Volume Info
 
'''
if there is an fs_hash (which is a mapping of specific volumes to query,
extract full volume info for those volumes, otherwise get info for all
'''
def extract_fs_info_for_vols_by_name(fs_hash = None, json_object = None):
    if fs_hash == None:
        pretty_hash(json_object)
    else:
        for mount in fs_hash.keys():
            pretty_hash(json_object[fs_hash[mount]['index']['index']])


def extract_mount_target_info_for_vols_by_name(fs_hash = None, json_object = None, headers = None, url = None):
    if fs_hash == None:
        for index in range(0,len(json_object)):
            mount = json_object[index]['creationToken']
            fsid = json_object[index]['FileSystemId']
            add_mount_targets_to_fs_hash(fs_hash = fs_hash, fsid = fsid, headers = headers, mount = mount, url = url)
    else:
        for mount in fs_hash.keys():
            fsid = fs_hash[mount]['FileSystemInfo']['FileSystemId']
            add_mount_targets_to_fs_hash(fs_hash = fs_hash, fsid = fsid, headers = headers, mount = mount, url = url)
    pretty_hash(fs_hash)

'''
Add File system information to fs_hash, then pass hash back
FilesystemInfo == hash containing filesysteminfo from SDK for a specific volume
Index == the index within the higher level filesystem info dump, use this later on rather than having to crawl the json object
'''
def add_mount_targets_to_fs_hash(fs_hash = None, fsid = None, headers = None, mount = None, url = None):
    try: 
        status, fs_hash[mount]['MountTargets'].append( get_json_object(command = ('FileSystems/%s/MountTargets' % (fsid)), headers = headers, url = url))
    except:
        status, fs_hash[mount]['MountTargets'] = get_json_object(command = ('FileSystems/%s/MountTargets' % (fsid)), headers = headers, url = url)
    return fs_hash



#MAIN

'''
Required Commands
'''
#@# Create full fs hash containing all info
status, json_object = get_json_object(command = 'FileSystems', headers = headers, url = url)

#@# Check for errors in base rest call
error_check(status)

#@# Map filesystem ids to names
#fs_hash = create_export_to_fsid_hash(json_object = json_object)
fs_hash = create_export_to_fsid_hash(filesystems = ['goofy-clever-sfs2','smb-server-test-volume-three'], json_object = json_object)

#@# print mount point to fsid map
#pretty_hash(fs_hash)

''' 
Custom commands
'''
#@# print info for all volumes, this is what happens if the fs_hash is empty
#extract_fs_info_for_vols_by_name(json_object = json_object)

#@# print info for specific volumes
extract_fs_info_for_vols_by_name(fs_hash = fs_hash, json_object = json_object)
                             
#extract_mount_target_info_for_vols_by_name(fs_hash = fs_hash, json_object = json_object, headers = headers, url = url)
                             


           


'''
#Capture all File Systems
if [[ $1 == "allfs" ]]; then
#    curl -s -H accept:application/json -H "Content-type: application/json" -H api-key:b2hpT0liU1Y1Y2hYZWVyWlJCcTh3UXpzRjI5M0pk -H secret-key:NkVsb1lMS3lNZHc3VHhjeTNwNnVtRmJwZ1NjVmpE -X GET https://cds-aws-bundles.netapp.com:8080/v1/FileSystems  | jq '.'
    curl -s -H accept:application/json 
            -H "Content-type: application/json" 
            -H api-key:b2hpT0liU1Y1Y2hYZWVyWlJCcTh3UXpzRjI5M0pk 
            -H secret-key:NkVsb1lMS3lNZHc3VHhjeTNwNnVtRmJwZ1NjVmpE 
            -X GET https://cds-aws-bundles.netapp.com:8080/v1/FileSystems  | jq '.'

    curl -s -H accept:application/json 
            -H \"Content-type: application/json\" 
            -H api-key:b2hpT0liU1Y1Y2hYZWVyWlJCcTh3UXpzRjI5M0pk 
            -H secret-key:NkVsb1lMS3lNZHc3VHhjeTNwNnVtRmJwZ1NjVmpE 
            -X POST https://cds-aws-bundles.netapp.com:8080/v1/FileSystems 
            -d \'{\"name\": \"$2\",
                  \"creationToken\":\"$3\",
                  \"region\":\"us-east\",
                  \"serviceLevel\":\"$4\",
                  \"quotaInBytes\":$5,
                  \"exportPolicy\":{\"rules\":[
                                               {\"ruleIndex\": 1,
                                                \"allowedClients\":\"0.0.0.0/0\",
                                                \"unixReadOnly\":false,
                                                \"unixReadWrite\": true,
                                                \"cifs\": false, 
                                                \"nfsv3\":true,
                                                \"nfsv4\":false}]},
                  \"labels\":[\"$6\"]}\' > /tmp/$$.ksh

#Capture mount Target
elif [[ $1 == "mt" ]]; then
    curl -s -H accept:application/json -H "Content-type: application/json" -H api-key:b2hpT0liU1Y1Y2hYZWVyWlJCcTh3UXpzRjI5M0pk -H secret-key:NkVsb1lMS3lNZHc3VHhjeTNwNnVtRmJwZ1NjVmpE -X GET https://cds-aws-bundles.netapp.com:8080/v1/FileSystems/$2/MountTargets/$3 | jq '.'

#Create Volumes
elif [[ $1 == "cv" ]]; then
    echo curl -s -H accept:application/json -H \"Content-type: application/json\" -H api-key:b2hpT0liU1Y1Y2hYZWVyWlJCcTh3UXpzRjI5M0pk -H secret-key:NkVsb1lMS3lNZHc3VHhjeTNwNnVtRmJwZ1NjVmpE -X POST https://cds-aws-bundles.netapp.com:8080/v1/FileSystems -d \'{\"name\": \"$2\",\"creationToken\":\"$3\",\"region\":\"us-east\",\"serviceLevel\":\"$4\",\"quotaInBytes\":$5,\"exportPolicy\":{\"rules\":[{\"ruleIndex\": 1,\"allowedClients\":\"0.0.0.0/0\",\"unixReadOnly\":false,\"unixReadWrite\": true,\"cifs\": false, \"nfsv3\":true,\"nfsv4\":false}]},\"labels\":[\"$6\"]}\' > /tmp/$$.ksh
    chmod 777 /tmp/$$.ksh
    /tmp/$$.ksh

#Delete Volumes
elif [[ $1 == "delete" ]]; then
    curl -s -H accept:application/json -H "Content-type: application/json" -H api-key:b2hpT0liU1Y1Y2hYZWVyWlJCcTh3UXpzRjI5M0pk -H secret-key:NkVsb1lMS3lNZHc3VHhjeTNwNnVtRmJwZ1NjVmpE -X DELETE https://cds-aws-bundles.netapp.com:8080/v1/FileSystems/$2

#Inspect AD
elif [[ $1 == "ad" ]]; then
    curl -s -H accept:application/json -H "Content-type: application/json" -H api-key:b2hpT0liU1Y1Y2hYZWVyWlJCcTh3UXpzRjI5M0pk -H secret-key:NkVsb1lMS3lNZHc3VHhjeTNwNnVtRmJwZ1NjVmpE -X GET https://cds-aws-bundles.netapp.com:8080/v1/Storage/ActiveDirectory | jq '.'

#View CVS Regions
elif [[ $1 == "regions" ]]; then
    curl -s -H accept:application/json -H "Content-type: application/json" -H api-key:b2hpT0liU1Y1Y2hYZWVyWlJCcTh3UXpzRjI5M0pk -H secret-key:NkVsb1lMS3lNZHc3VHhjeTNwNnVtRmJwZ1NjVmpE -X GET https://cds-aws-bundles.netapp.com:8080/v1/Storage/Regions | jq '.'

#View Zones
elif [[ $1 == "zones" ]]; then
    curl -s -H accept:application/json -H "Content-type: application/json" -H api-key:b2hpT0liU1Y1Y2hYZWVyWlJCcTh3UXpzRjI5M0pk -H secret-key:NkVsb1lMS3lNZHc3VHhjeTNwNnVtRmJwZ1NjVmpE -X GET https://cds-aws-bundles.netapp.com:8080/v1/Storage/Zones | jq '.'

#View IPRanges
elif [[ $1 == "iprange" ]]; then
    curl -s -H accept:application/json -H "Content-type: application/json" -H api-key:b2hpT0liU1Y1Y2hYZWVyWlJCcTh3UXpzRjI5M0pk -H secret-key:NkVsb1lMS3lNZHc3VHhjeTNwNnVtRmJwZ1NjVmpE -X GET https://cds-aws-bundles.netapp.com:8080/v1/Storage/IPRanges | jq '.'

#View Jobs
elif [[ $1 == "jobs" ]]; then
    curl -s -H accept:application/json -H "Content-type: application/json" -H api-key:b2hpT0liU1Y1Y2hYZWVyWlJCcTh3UXpzRjI5M0pk -H secret-key:NkVsb1lMS3lNZHc3VHhjeTNwNnVtRmJwZ1NjVmpE -X GET https://cds-aws-bundles.netapp.com:8080/v1/Jobs | jq '.'

#View Backups
elif [[ $1 == "backups" ]]; then
    curl -s -H accept:application/json -H "Content-type: application/json" -H api-key:b2hpT0liU1Y1Y2hYZWVyWlJCcTh3UXpzRjI5M0pk -H secret-key:NkVsb1lMS3lNZHc3VHhjeTNwNnVtRmJwZ1NjVmpE -X GET https://cds-aws-bundles.netapp.com:8080/v1/Backups | jq '.'

#View Snapshots
elif [[ $1 == "all-snapshots" ]]; then
    curl -s -H accept:application/json -H "Content-type: application/json" -H api-key:b2hpT0liU1Y1Y2hYZWVyWlJCcTh3UXpzRjI5M0pk -H secret-key:NkVsb1lMS3lNZHc3VHhjeTNwNnVtRmJwZ1NjVmpE -X GET https://cds-aws-bundles.netapp.com:8080/v1/Snapshots | jq '.'

#create Snapshots
elif [[ $1 == "create-snapshot" ]]; then
    echo curl -s -H accept:application/json -H \"Content-type: application/json\" -H api-key:b2hpT0liU1Y1Y2hYZWVyWlJCcTh3UXpzRjI5M0pk -H secret-key:NkVsb1lMS3lNZHc3VHhjeTNwNnVtRmJwZ1NjVmpE -X POST https://cds-aws-bundles.netapp.com:8080/v1/FileSystems/$2/Snapshots -d \'{\"name\": \"$3\",\"region\":\"us-east\"}\' > /tmp/$$.ksh
    chmod 777 /tmp/$$.ksh
    /tmp/$$.ksh
fi
'''
