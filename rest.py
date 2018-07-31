#!/usr/bin/python
import argparse
import json
import logging
import os
import requests
import sys
from configobj import ConfigObj
from os.path import expanduser


def config_parser():
    home = expanduser("~")
    if os.path.exists(home + '/aws_cvs_config'):
        with open(home + '/aws_cvs_config','r') as config_file:
            temp = json.load(config_file)
        headers = {}
        headers['api-key'] = temp['apikey']
        headers['secret-key'] = temp['secretkey']
        headers['content-type'] = 'application/json'
        url = temp['url']
        return headers, url
    else:
        print('\aws_cvs_config not found, please run cvs_keys.py before proceeding\n')
        exit()

def command_line():
    parser = argparse.ArgumentParser(prog='cloudvolumes.py',description='%(prog)s is used to issue api calls on your behalf')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--volCreate',action='store_const',const=True,)
    group.add_argument('--volDelete',action='store_const',const=True,)
    group.add_argument('--volList', action='store_const',const=True,)
    group.add_argument('--snapCreate',action='store_const',const=True,)
    group.add_argument('--snapDelete',action='store_const',const=True,)
    group.add_argument('--snapList', action='store_const',const=True,)
    parser.add_argument('--volume','-v', type=str,help='Enter a volume name to search for' )
    parser.add_argument('--pattern','-p',action='store_const',const=True,help='If --pattern, search for all volumes with the name as a substring.  Supports snap* and volList ')
    parser.add_argument('--region','-r',type=str,help='Specify the region when performing creation operations, Supports snapCreate and volCreate')
    parser.add_argument('--name','-n',type=str,help='Specify the object name to create.  Supports snapCreate and volCreate')
    parser.add_argument('--count','-c',type=str,help='Specify the number of volumes to create.  Supports volCreate')
    

    arg = vars(parser.parse_args())
    headers, url = config_parser()
    
    if arg['volList'] or arg['snapList'] or arg['snapCreate'] or arg['snapDelete'] or arg['volDelete']:
        #@# Create full fs hash containing all info
        volume_status, json_volume_object = submit_api_request(command = 'FileSystems',
                                                               direction = 'GET',
                                                               headers = headers,
                                                               url = url)
        
        #@# Check for errors in base rest call
        error_check(volume_status)

        #@# Map filesystem ids to names
        #fs_map_hash = create_export_to_fsid_hash(json_object = json_volume_object)
        if arg['volume'] and not arg['pattern']:
            fs_map_hash = create_export_to_fsid_hash(filesystems = [arg['volume']], json_object = json_volume_object)
        elif arg['volume'] and arg['pattern']:
            fs_map_hash = create_export_to_fsid_hash(json_object = json_volume_object)
            for element in fs_map_hash.keys():
                if arg['volume'] not in element:
                    fs_map_hash.pop(element)
        else: 
            fs_map_hash = create_export_to_fsid_hash(json_object = json_volume_object)

        if arg['volList']:
            #@# print and capture info for specific volumes
            vol_hash = extract_fs_info_for_vols_by_name(fs_map_hash = fs_map_hash,
                                                        json_object = json_volume_object)

        elif arg['volDelete']:
            if arg['volume'] and not arg['pattern']:
                #@# Delete specific volumes
                for volume in fs_map_hash.keys():
                    fileSystemId = fs_map_hash[volume]['fileSystemId']
                    command = 'FileSystems/' + fileSystemId
                    volume_status, json_volume_delete_object = submit_api_request(command = command,
                                                                                  direction = 'DELETE', 
                                                                                  headers = headers, 
                                                                                  url = url)
                    error_check(volume_status)
                    print('Volume Deletion submitted:\n\tvolume:%s:\n\tfileSystemId:%s\n' % (volume,fileSystemId))
            else:
                print('\nvolumeDelete requires use of --volume with a single volume name and fobids the use of --pattern\n')
                exit()
        

        elif arg['snapList']:
            #@# capture snapshot infor for volumes
            snapshot_status, json_snapshot_object = submit_api_request(command = 'Snapshots', 
                                                                       direction = 'GET',
                                                                       headers = headers, 
                                                                       url = url)

            #@# Check for errors in base rest call
            error_check(snapshot_status)

            #@# print snapshots for selected volumes
            snapshot_extract_info(fs_map_hash = fs_map_hash, prettify = True, snap_hash = json_snapshot_object)

        elif arg['snapCreate']:
            if arg['name'] and arg['region']:
                data = {'region':arg['region'],'name':arg['name']}
                for volume in fs_map_hash.keys():
                    command = 'FileSystems/' + fs_map_hash[volume]['fileSystemId'] + '/Snapshots'
                    snapshot_status, json_snapshot_object = submit_api_request(command = command,
                                                                               data = data, 
                                                                               direction = 'POST', 
                                                                               headers = headers, 
                                                                               url = url)
                #@# Check for errors in base rest call
                error_check(snapshot_status)
            else:
                print('\n--name and --region must both be specified along with --snapCreate.\n')
                exit()
                
        elif arg['snapDelete']:
            if arg['name']:
                #@# capture snapshot info for volumes
                snapshot_status, json_snapshot_object = submit_api_request(command = 'Snapshots',
                                                                           direction = 'GET',
                                                                           headers = headers,
                                                                           url = url)

                #@# Check for errors in base rest call
                error_check(snapshot_status)
    
                #@# print snapshots for selected volumes based on volume name
                fs_snap_hash = snapshot_extract_info(fs_map_hash = fs_map_hash,
                                                     prettify = False,
                                                     snap_hash = json_snapshot_object)
                

                for volume in fs_snap_hash.keys():
                    for index in range(0,len(fs_snap_hash[volume]['snapshots'])):
                        if fs_snap_hash[volume]['snapshots'][index]['name'] == arg['name']:
                            snapshotId = fs_snap_hash[volume]['snapshots'][index]['snapshotId']
                            fileSystemId = fs_map_hash[volume]['fileSystemId']
                            command = 'FileSystems/' + fileSystemId + '/Snapshots/' + snapshotId
                             
                            snapshot_status, json_snapshot_object = submit_api_request(command = command,
                                                                                       direction = 'DELETE',
                                                                                       headers = headers,
                                                                                       url = url)
                            
                            #@# Check for errors in base rest call
                            error_check(snapshot_status)
                            print('Deletion submitted for snapshot %s:\n\tvolume:%s\n\tsnapshot:%s' % (arg['name'],volume,snapshotId))
            else:
                print('\n--name must both be specified along with --snapDelete.\n')
                exit()
            
    exit()       

    
 

#############
# Primary Code #
'''
Get the the json object for working with again and again
'''
def submit_api_request( command = None, data = None, direction = None, headers = None, url = None):
    if direction == 'GET':
        r = requests.get(url + '/' + command, headers = headers)
    elif direction == 'POST':
        r = requests.post(url + '/' + command, data = json.dumps(data), headers = headers)
    elif direction == 'DELETE':
        r = requests.delete(url + '/' + command, headers = headers)
    return r.status_code,r.json()

'''
For now exit if error code != 200
'''
def error_check(status_code = None): 
    if status_code < 200 or status_code >= 300:
        print('Something went wrong with API request, Error Code: %s' % (status_code))
        exit()

'''
get the hash of file system ids associated with creation tokens
key == export name
value == [filesystem id, index position inside base json object]
return == hash of export names : [filesystem id, index position]
'''
def create_export_to_fsid_hash(filesystems = None, json_object = None):
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
    fs_map_hash[mount]['fileSystemId'] = json_object[index]['fileSystemId']
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
        fsid = fs_map_hash[mount]['fileSystemId']
        mount_hash[mount] = {}
        mount_hash[mount]['fileSystemId'] = fsid
        status, json_mountarget_object = submit_api_request(command = ('FileSystems/%s/MountTargets' % (fsid)), direction = 'GET', headers = headers, url = url)
        error_check(status)
        mount_hash[mount]['ipaddress'] = json_mountarget_object[0]['ipAddress']
    pretty_hash(mount_hash)
    return mount_hash


#############
# Snapshot Code

'''
Extract snapshots for the listed volumes,
pretty print the output if any,
return the output in form as follows
{
    "volume": {
        "fileSystemId": "75a59fcc-7254-2f32-ba7c-c790b469bc48",
        "snapshots": [
            {
                "name": "snappy",
                "snapshotId": "bdb723bf-5d72-5e95-b4ef-bb0d0e24ce72",
                "usedBytes": 136
            }
        ]
    }
}
'''
def snapshot_extract_info(fs_map_hash = None, prettify = None, snap_hash = None):
    fs_snap_hash = {}
    for mount in fs_map_hash.keys():
        for index in range(0,len(snap_hash)):
            if snap_hash[index]['fileSystemId'] == fs_map_hash[mount]['fileSystemId']:
                if mount not in fs_snap_hash:
                    fs_snap_hash[mount] = {}
                    fs_snap_hash[mount]['fileSystemId'] = fs_map_hash[mount]['fileSystemId']
                    fs_snap_hash[mount]['snapshots'] = []
                fs_snap_hash[mount]['snapshots'].append(snap_hash[index])

    if len(fs_snap_hash) > 0:
        if prettify: 
            pretty_hash(fs_snap_hash)
        return fs_snap_hash



#MAIN

'''
Required Commands
'''
#Extract url and headers
command_line()

#@# Create full fs hash containing all info
volume_status, json_volume_object = submit_api_request(command = 'FileSystems',
                                                       direction = 'GET',
                                                       headers = headers,
                                                       url = url)

#@# Check for errors in base rest call
error_check(volume_status)

#@# Map filesystem ids to names
#fs_map_hash = create_export_to_fsid_hash(json_object = json_volume_object)
fs_map_hash = create_export_to_fsid_hash(filesystems = ['goofy-clever-sfs2','smb-server-test-volume-three'], json_object = json_volume_object)

#@# print mount point to fsid map
pretty_hash(fs_map_hash)

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
snapshot_status, json_snapshot_object = submit_api_request(command = 'Snapshots', direction = 'GET', headers = headers, url = url)

#@# Check for errors in base rest call
error_check(snapshot_status)

#@# print snapshots for selected volumes
snapshot_extract_info(fs_map_hash = fs_map_hash, prettify = True, snap_hash = json_snapshot_object)

#@# create snapshots
data = {'region':'us-east','name':'us-east'}
for volume in fs_map_hash.keys():
    snapshot_status, json_snapshot_object = submit_api_request(command = 'FileSystems/' + fs_map_hash[volume]['fileSystemId'] + '/Snapshots',
                                                               data = data, 
                                                               direction = 'POST', 
                                                               headers = headers, 
                                                               url = url)
    #@# Check for errors in base rest call
    error_check(snapshot_status)

#'''
#data = {'name':'sn1', 'region':'us-east'}

'''
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

'''
