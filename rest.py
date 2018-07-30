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
def get_json_object( command = None, direction = None, headers = None, url = None):
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
    fs_map_hash = {}
    if filesystems is not None:
        for mount in filesystems:
            for idx in range(0,len(json_object)):
                if mount == json_object[idx]['creationToken']:
                    add_volumes_to_fs_hash(json_object = json_object, index = idx, mount = mount, fs_map_hash = fs_map_hash)
    else:
        for idx in range(0,len(json_object)):
            mount = json_object[idx]['creationToken']
            add_volumes_to_fs_hash(json_object = json_object, index = idx, mount = mount, fs_map_hash = fs_map_hash)
    return fs_map_hash


'''
Add File system information to fs_hash, then pass hash back
FilesystemInfo == hash containing filesysteminfo from SDK for a specific volume
Index == the index within the higher level filesystem info dump, use this later on rather than having to crawl the json object
'''
def add_volumes_to_fs_hash(json_object = None, index = None, mount = None, fs_map_hash = None):
    fs_map_hash[mount] = {}
    fs_map_hash[mount]['FileSystemId'] = json_object[index]['fileSystemId']
    fs_map_hash[mount]['index'] = index
    

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
# Get
 
'''
if there is an fs_hash (which is a mapping of specific volumes to query,
extract full volume info for those volumes, otherwise get info for all
'''
def extract_fs_info_for_vols_by_name(fs_map_hash = None, json_object = None):
    fs_hash = {}
    for mount in fs_map_hash.keys():
        fs_hash[mount] = {}
        add_fs_info_for_vols_by_name(fs_hash = fs_hash, fs_map_hash = fs_map_hash, json_object = json_object, mount = mount)
    pretty_hash(fs_hash)

def add_fs_info_for_vols_by_name(fs_hash = None, fs_map_hash = None, json_object = None, mount = None):
    for attribute in json_object[fs_map_hash[mount]['index']].keys():
       fs_hash[mount][attribute] = json_object[fs_map_hash[mount]['index']][attribute]
    

#############
# Mount Code


'''
Add File system information to fs_hash, then pass hash back
FilesystemInfo == hash containing filesysteminfo from SDK for a specific volume
Index == the index within the higher level filesystem info dump, use this later on rather than having to crawl the json object
'''
def extract_mount_target_info_for_vols_by_name(fs_map_hash = None, json_object = None, headers = None, url = None):
    mount_hash = {}
    for mount in fs_map_hash.keys():
        fsid = fs_map_hash[mount]['FileSystemId']
        mount_hash[mount] = {}
        mount_hash[mount]['fileSystemId'] = fsid
        status, json_mountarget_object = get_json_object(command = ('FileSystems/%s/MountTargets' % (fsid)), direction = 'GET', headers = headers, url = url)
        error_check(status)
        mount_hash[mount]['ipaddress'] = json_mountarget_object[0]['ipAddress']
    pretty_hash(mount_hash)
    return mount_hash


#############
# Snapshot Code

def extract_snapshot_info(fs_map_hash = None, snap_hash = None):
    fs_snap_hash = {}
    for mount in fs_map_hash.keys():
        fs_snap_hash[mount] = {'snapshots':{}}
        fs_snap_hash[mount]['fileSystemId'] = fs_map_hash[mount]['FileSystemId']
        for index in range(0,len(snap_hash)):
            print snap_hash[index]['fileSystemId']
            if snap_hash[index]['fileSystemId'] == fs_map_hash[mount]['fileSystemId']:
                fs_snap_hash[mount]['snapshots'][snap_hash[index]['snapshotId']] = {'name':snap_hash[index]['name'],'usedBytes':snap_hash[index]['usedBytes']}
    pretty_hash(fs_snap_hash)
    return fs_snap_hash


#MAIN

'''
Required Commands
'''
#@# Create full fs hash containing all info
volume_status, json_volume_object = get_json_object(command = 'FileSystems', direction = 'GET', headers = headers, url = url)

#@# Check for errors in base rest call
error_check(volume_status)

#@# Map filesystem ids to names
fs_map_hash = create_export_to_fsid_hash(json_object = json_volume_object)
#fs_map_hash = create_export_to_fsid_hash(filesystems = ['goofy-clever-sfs2','smb-server-test-volume-three'], json_object = json_object)

#@# print mount point to fsid map
#pretty_hash(fs_map_hash)

''' 
Main Volumes
'''
#@# print and capture info for specific volumes
#vol_hash = extract_fs_info_for_vols_by_name(fs_map_hash = fs_map_hash, json_object = json_volume_object)

'''
Main Mount Targets
'''
#@# print anc capture ip addresses for volumes
#mount_hash = extract_mount_target_info_for_vols_by_name(fs_map_hash = fs_map_hash, json_object = json_volume_object, headers = headers, url = url)

'''
MAIN Snapshots
'''
#@# capture snapshot infor for volumes
snapshot_status, json_snapshot_object = get_json_object(command = 'Snapshots', direction = 'GET', headers = headers, url = url)

#@# Check for errors in base rest call
error_check(snapshot_status)

#@# print mount point to fsid map
extract_snapshot_info(fs_map_hash = fs_map_hash, snap_hash = json_snapshot_object)



                             


           


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
