#!/usr/bin/python
import argparse
import json
import math
import os
import requests
from os.path import expanduser


def config_parser(project = None):
    home = expanduser("~")
    if os.path.exists(home + '/aws_cvs_config'):
        with open(home + '/aws_cvs_config','r') as config_file:
            temp = json.load(config_file)
        if project not in temp.keys():
            print('\nSpecified project was not found in aws_cvs_config: %s\n\nPlease check your input and try again\n' % (project))
            exit()
        
        headers = {}
        headers['api-key'] = temp[project]['apikey']
        headers['secret-key'] = temp[project]['secretkey']
        headers['content-type'] = 'application/json'
        url = temp[project]['url']
        region = temp[project]['region']
    else:
        print('aws_cvs_config not found, please run cvs_keys.py before proceeding\n')
        exit()
    
    return headers, region, url

def quota_and_servicelevel_parser():
    if os.path.exists('servicelevel_and_quotas.json'):
        with open('servicelevel_and_quotas.json','r') as config_file:
            price_and_bw_hash = json.load(config_file)
        return price_and_bw_hash
    else:
        print('\Error, the servicelevel_and_quotas.json file could not be found\n')
        exit()

def command_line():
    parser = argparse.ArgumentParser(prog='cvs-aws.py',description='%(prog)s is used to issue commands to your NetApp Cloud Volumes Service on your behalf.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--volCreate',action='store_const',const=True,)
    group.add_argument('--volDelete',action='store_const',const=True,)
    group.add_argument('--volList', action='store_const',const=True,)
    group.add_argument('--snapCreate',action='store_const',const=True,)
    group.add_argument('--snapDelete',action='store_const',const=True,)
    group.add_argument('--snapList', action='store_const',const=True,)
    group.add_argument('--snapRevert', action='store_const',const=True,)
    parser.add_argument('--project','-p',type=str,help='Enter the project name to interact with, otherwise the default project is selected')
    parser.add_argument('--preview', action='store_const',const=True,help='If specfied, a try befor your buy simulation is run rather than\
                                                                         the actual command. Supports all delete and create commands.')
    parser.add_argument('--Force', action='store_const',const=True,help='If specfied, enables substring\'s to work *Delete and Revert\
                                                                         operations. Supports all *Delete operations as well as snapRevert.')
    parser.add_argument('--pattern','-P',action='store_const',const=True,help='Search for volumes using name as substring.\
                                                                               Supports snapList and volList nativley, snapDelete\
                                                                               and volDelete as well as snapRevert with --Force.\n\n')
    parser.add_argument('--volume','-v', type=str,help='Enter a volume name to search for, names must be between 16 and 33 characters in length' )
    parser.add_argument('--region','-r',type=str,help='Specify the region when performing creation operations, specify only if different than that\
                                                       listed already in the aws_cvs_config.json file. Supports snapCreate and volCreate')
    parser.add_argument('--name','-n',type=str,help='Specify the object name to create.  Supports snap* and volCreate. When used with volCreate,\
                                                     body must match [a-zA-Z][a-zA-Z0-9-] and be 16 - 33 character long')
    parser.add_argument('--gigabytes','-g',type=str,help='Volume gigabytes in Gigabytes, value accepted between 1 and 100,000. Supports volCreate')
    parser.add_argument('--bandwidth','-b',type=str,help='Volume bandwidth requirements in Megabytes per second. If unknown enter 0 and maximum\
                                                     bandwidth is assigned. Supports volCreate')
    parser.add_argument('--cidr','-c',type=str,help='IP Range used for export rules, the format needs to be similar to 0.0.0.0/0, supports volCreate')
    parser.add_argument('--label','-l',type=str,help='Volume label. Supports volCreate')
    parser.add_argument('--count','-C',type=str,help='Specify the number of volumes to create. Supports volCreate')
    arg = vars(parser.parse_args())

    #Use the specified project if given, if not given use the default project
    if arg['project']:
        project = arg['project']
    else:
        project = 'default'
    headers, region, url = config_parser(project = project)
    
    #Preview sets of the automation to simulate the command and return simulated results, if not entered assume False
    if arg['preview']:
        preview = True
    else:
        preview = False

    #Use the region specified in the command line if present, otherwise go with that returned in the config file
    if arg['region']:
        region = arg['region']
    
    
    if arg['volList'] or arg['snapList'] or arg['snapCreate'] or arg['snapDelete'] or arg['volDelete'] or arg['volCreate'] or arg['snapRevert']:
        #@# Create full fs hash containing all info
        volume_status, json_volume_object = submit_api_request(command = 'FileSystems',
                                                               direction = 'GET',
                                                               headers = headers,
                                                               region = region,
                                                               url = url)
        
        #@# Check for errors in base rest call
        error_check(body = json_volume_object,
                    status_code = volume_status,
                    url = url)

        #@# Map filesystem ids to names
        #fs_map_hash = create_export_to_fsid_hash(json_object = json_volume_object)
        if arg['volume'] and not arg['pattern']:
            fs_map_hash = create_export_to_fsid_hash(filesystems = [arg['volume']], json_object = json_volume_object, region = region)
        elif arg['volume'] and arg['pattern']:
            fs_map_hash = create_export_to_fsid_hash(json_object = json_volume_object, region = region)
            for element in fs_map_hash.keys():
                if arg['volume'] not in element:
                    fs_map_hash.pop(element)
        else: 
            fs_map_hash = create_export_to_fsid_hash(json_object = json_volume_object, region = region)


         
        ##########################################################
        #                      Volume Commands
        ##########################################################
        
        #Get a list of all volumes matching inputted -volume and --pattern if specified, or alternativley all volumes
        if arg['volList']:
            if arg['Force']:
                print('The volList command resulted in an error.\tThe --Force flag is not supported.')
                volList_error_message()
            elif arg['pattern'] and not arg['volume']:
                print('The volList command resulted in an error:\tThe --pattern flag requires --volume <volume>.')
                volList_error_message()
            elif len(fs_map_hash) > 0:
                #@# print and capture info for specific volumes
                vol_hash = extract_fs_info_for_vols_by_name(fs_map_hash = fs_map_hash,
                                                            json_object = json_volume_object,
                                                            headers = headers,
                                                            region = region, 
                                                            url = url)
            else:
                if arg['volume'] and arg['pattern']:
                    print('The volList command resulted in an error:\tNo volumes exist matching --volume substring %s in region %s.' % (arg['volume'],region))
                elif arg['volume']:
                    print('The volList command resulted in an error:\tNo volumes exist matching --volume %s in region %s.' % (arg['volume'],region))
                else: 
                    print('The volList command resulted in an error:\tNo volumes exist in region %s.' % (region))
                exit()

        elif arg['volCreate']:
            if arg['name']:
                if arg['gigabytes'] and arg['bandwidth'] and arg['cidr'] and arg['name'] and region:
                    error = False 
                    error_value = {}
    
                    if len(arg['name']) < 15:
                        error = True
                        error_value['name_length'] = ('Volume Name length is too short: %s, names must be => 15 and <= 33 characters' % (len(arg['name'])))
                    if len(arg['name']) > 33:
                        error = True
                        error_value['name_length'] = ('Volume Name length is too long: %s, names must be => 15 and <= 33 characters' % (len(arg['name'])))
                    for index in range(0,len(arg['name'])):
                        local_error = is_ord(my_string = arg['name'][index], position = index)
                        if local_error == True:
                            error = True
                            error_value['name_illegal_character'] = 'Illegal char type'
                    local_error = is_number(arg['gigabytes'])
                    if local_error == True:
                        error = True
                        error_value['gigabytes_integer'] = 'Capacity was not a numeric value'
                    elif int(arg['gigabytes']) < 1 or int(arg['gigabytes']) > 100000:
                        error = True
                        error_value['size'] = 'Capacity was either smaller than 1GB or greater than 100,000GB'
                    local_error = is_number(arg['bandwidth'])
                    if local_error == True:
                        error = True
                        error_value['bw_integer'] = 'Bandwidth was not a numeric value'
                    elif arg['bandwidth'] < 0:
                        error = True
                        error_value['bw'] = ('Negative value entered: %s, requested values must be => 0.  If value == 0 or value > 3800 then maximum bandwidth will be assigned' % (arg['bandwidth']))
                    servicelevel, quotainbytes, bandwidthMB = servicelevel_and_quota_lookup(bwmb = arg['bandwidth'], gigabytes = arg['gigabytes'])
                    local_error = cidr_rule_check(arg['cidr'])
                    if local_error == True:
                        error = True
                        error_value['cidr'] = ('Cidr rule is incorrect: %s, value must be in the form of X.X.X.X/X where all values for X are between 0 and 255' % (arg['cidr']))
                    if arg['count']: 
                        local_error = is_number(arg['count'])
                        if local_error == True:
                            error = True
                            error_value['count_int'] = 'count is a non integer'
                        elif int(arg['count']) < 1:
                            error = True
                            error_value['count'] = 'count is < 1'
                        else:
                            count = int(arg['count'])
                    else:
                        count = 1
                    if arg['label']:
                        label = arg['label']
                    else:
                        label = None
        
                    if error == False: 
                        if count == 1:
                            name = arg['name']
                            volume_creation(bandwidth = bandwidthMB,
                                            cidr = arg['cidr'],
                                            headers = headers,
                                            label = label,
                                            name = name,
                                            preview = preview,
                                            quota_in_bytes = quotainbytes,
                                            region = region,
                                            servicelevel = servicelevel,
                                            url = url)
                        else:
                            while count > 0:
                                name = arg['name'] + '-' + str(count)
                                volume_creation(bandwidth = bandwidthMB,
                                                cidr = arg['cidr'],
                                                headers = headers,
                                                label = label,
                                                name = name,
                                                preview = preview,
                                                quota_in_bytes = quotainbytes,
                                                region = region,
                                                servicelevel = servicelevel,
                                                url = url)
                                count -= 1
                    else:
                        print('The volCreate command failed, see the following json output for the cause:\n')
                        pretty_hash(error_value)
                        volCreate_error_message()
                else:
                    volCreate_error_message()
            else:   
                print('The volCreate command resulted in an error.\tThe required flag --name was not specified.')
                volCreate_error_message()

        #Volume delete does not support pattern matching or empty sets, a volume name must be entered
        elif arg['volDelete']:
            if arg['volume']:
                if arg['pattern']  and not arg['Force']:
                    print('The volDelete command resulted in an error:\tThe --pattern flag requires both --volume <volume> and --Force.')
                    volDelete_error_message()
                elif arg['volume'] and not arg['pattern'] or arg['volume'] and arg['pattern'] and arg['Force']:
                    #@# Delete specific volumes
                    if len(fs_map_hash) > 0:
                        for volume in fs_map_hash.keys():
                            fileSystemId = fs_map_hash[volume]['fileSystemId']
                            command = 'FileSystems/' + fileSystemId
                            if preview is False:
                                volume_status, json_volume_delete_object = submit_api_request(command = command,
                                                                                              direction = 'DELETE', 
                                                                                              headers = headers, 
                                                                                              region = region,
                                                                                              url = url)
                                error_check(body = json_volume_delete_object,
                                            status_code = volume_status,
                                            url = url)
                                print('Volume Deletion submitted:\n\tvolume:%s:\n\tfileSystemId:%s' % (volume,fileSystemId))
                            else:
                                print('Volume Deletion simulated:\n\tvolume:%s:\n\tfileSystemId:%s' % (volume,fileSystemId))
                    else:
                        if arg['pattern']:
                            print('The volDelete command resulted in an error:\tNo volumes exist matching --volume substring %s in region %s.' % (arg['volume'],region))
                        else:
                            print('The volDelete command resulted in an error:\tNo volumes exist matching --volume %s in region %s.' % (arg['volume'],region))
                        exit()
                else:
                    volDelete_error_message()
            else:
                print('The volDelete command resulted in an error.\tThe required flag --volume was not specified.')
                volDelete_error_message()

        
        ##########################################################
        #                     Snapshot Commands
        ##########################################################
        

        elif arg['snapList']:
            #@# capture snapshot infor for volumes
            if arg['pattern'] and not arg['volume']:
                print('The snapList command resulted in an error:\tCommand line parameter --patterns requires --volumes <volume>')
                snapList_error_message()
            elif arg['Force']:
                print('The snapList command resulted in an error:\tCommand line parameter --Force is not supported')
                snapList_error_message()
            else:
                if len(fs_map_hash) == 0: 
                    if arg['volume'] and arg['pattern']:
                        print('The snapList command resulted in an error:\tNo volumes exist matching --volume substring %s region %s.' % (arg['volume'],region))
                    elif arg['volume']:
                        print('The snapList command resulted in an error:\tNo volumes exist matching --volume %s in region %s.' % (arg['volume'],region))
                    else: 
                        print('The snapList command resulted in an error:\tNo volumes exist in region %s.' % (region))
                    exit()
                else:
                    #@# capture snapshot info for volumes
                    snapshot_status, json_snapshot_object = submit_api_request(command = 'Snapshots', 
                                                                               direction = 'GET',
                                                                               headers = headers, 
                                                                               region = region,
                                                                               url = url)

                    #@# Check for errors in base rest call
                    error_check(body = json_snapshot_object,
                                       status_code = snapshot_status,
                                       url = url)

                    #@# print snapshots for selected volumes
                    snapshot_extract_info(fs_map_hash = fs_map_hash, prettify = True, snap_hash = json_snapshot_object)

        elif arg['snapCreate']:
            if arg['name']:
                if arg['Force']:
                    print('The snapCreate command resulted in an error.\tThe --Force flag is not supported.')
                    snapCreate_error_message()
                elif arg['volume'] and not arg['pattern'] or arg['volume'] and arg['pattern'] or not arg['volume'] and not arg['pattern']:
                    data = {'region':region,'name':arg['name']}
                    
                    if len(fs_map_hash) > 0:
                        for volume in fs_map_hash.keys():
                            command = 'FileSystems/' + fs_map_hash[volume]['fileSystemId'] + '/Snapshots'
                            if preview is False:
                                snapshot_status, json_snapshot_object = submit_api_request(command = command,
                                                                                           data = data, 
                                                                                           direction = 'POST', 
                                                                                           headers = headers, 
                                                                                           region = region,
                                                                                           url = url)
                                #@# Check for errors in base rest call
                                error_check(body = json_snapshot_object,
                                            status_code = snapshot_status,
                                            url = url)
                                print('Snapshot Creation submitted:\n\tvolume:%s:\n\tname:%s' % (volume,arg['name']))
                            else:
                                print('Snapshot Creation simulated:\n\tvolume:%s:\n\tname:%s' % (volume,arg['name']))
                        exit()
                    else:
                        if arg['volume'] and arg['pattern']:
                            print('The snapCreate command resulted in an error:\tNo volumes exist matching --volume substring %s in region %s.' % (arg['volume'],region))
                        elif arg['volume']:
                            print('The snapCreate command resulted in an error:\tNo volumes exist matching --volume %s in region %s.' % (arg['volume'],region))
                        else: 
                            print('The snapCreate command resulted in an error:\tNo volumes exist in region %s.' % (region))
                        exit()
            else:
                print('The snapCreate command resulted in an error.\tThe required flag --name name was not specified.')
                snapCreate_error_message()
                
        #snapDelete Code
        elif arg['snapDelete']:
            if arg['name']:
                if arg['pattern'] and arg['Force'] and not arg['volume']:
                    print('The snapDelete command resulted in an error:\tCommand line options missings')
                    snapDelete_error_message()
                elif arg['Force'] and arg['volume'] and not arg['pattern']:
                    print('The snapDelete command resulted in an error:\tIncorrect Command line')
                    snapDelete_error_message()
                elif arg['name'] and arg['pattern'] and not arg['Force']: 
                    print('The snapDelete command resulted in an error:\tCommand line options missings')
                    snapDelete_error_message()
                elif arg['volume'] and not arg['pattern'] or arg['volume'] and arg['pattern'] and arg['Force'] or arg['Force'] :
                    if len(fs_map_hash) == 0: 
                        if arg['volume'] and arg['pattern']:
                            print('The snapDelete command resulted in an error:\tNo volumes exist matching --volume substring %s in region %s.' % (arg['volume'],region))
                        elif arg['volume']:
                            print('The snapDelete command resulted in an error:\tNo volumes exist matching --volume %s in region %s.' % (arg['volume'],region))
                        else: 
                            print('The snapDelete command resulted in an error:\tNo volumes exist in region %s.' % (region))
                        exit()
                    else:
                        #@# capture snapshot info for volumes
                        snapshot_status, json_snapshot_object = submit_api_request(command = 'Snapshots',
                                                                                   direction = 'GET',
                                                                                   headers = headers,
                                                                                   region = region,
                                                                                   url = url)
        
                        #@# Check for errors in base rest call
                        error_check(body = json_snapshot_object,
                                    status_code = snapshot_status,
                                    url = url)
            
                        #@# print snapshots for selected volumes based on volume name
                        fs_snap_hash = snapshot_extract_info(fs_map_hash = fs_map_hash,
                                                             prettify = False,
                                                             snap_hash = json_snapshot_object)
                        tracking_deletions = 0
                        if fs_snap_hash is not None: 
                            for volume in fs_snap_hash.keys():
                                #Use this to record if we actually deleted any snapshots
                                for index in range(0,len(fs_snap_hash[volume]['snapshots'])):
                                    if fs_snap_hash[volume]['snapshots'][index]['name'] == arg['name']:
                                        snapshotId = fs_snap_hash[volume]['snapshots'][index]['snapshotId']
                                        fileSystemId = fs_map_hash[volume]['fileSystemId']
                                        command = 'FileSystems/' + fileSystemId + '/Snapshots/' + snapshotId
                                        if preview is False:
                                            snapshot_status, json_snapshot_object = submit_api_request(command = command,
                                                                                                       direction = 'DELETE',
                                                                                                       headers = headers,
                                                                                                       region = region,
                                                                                                       url = url)
                                        
                                            #@# Check for errors in base rest call
                                            error_check(body = json_snapshot_object,
                                                        status_code = snapshot_status,
                                                        url = url)
                                            print('Snapshot Deletion submitted for snapshot %s:\n\tvolume:%s\n\tsnapshot:%s' % (arg['name'],volume,snapshotId))
                                        else:
                                            print('Snapshot Deletion simulated for snapshot %s:\n\tvolume:%s\n\tsnapshot:%s' % (arg['name'],volume,snapshotId))
                                        tracking_deletions += 1 
                                exit()
                        if tracking_deletions == 0:
                            print('The snapDelete command resulted in zero deletions: :\tNo volumes contained snapshot %s' % (arg['name']))
                        exit()
            else:
                print('The snapDelete command resulted in an error:\tThe required flag --name name was not specified.')
                snapDelete_error_message()



        #Revert filesystem(s) to a specific snapshot
        elif arg['snapRevert']:
            if arg['name']:
                if arg['pattern']  and  arg['Force'] and not arg['volume']:
                    print('The snapRevert command resulted in an error:\tThe --pattern flag requires both --volume <substring> and --Force.')
                    snapRevert_error_message()
                elif arg['pattern']  and  not arg['Force']:
                    print('The snapRevert command resulted in an error:\tThe flag --pattern was specified without --Force.')
                    snapRevert_error_message()
                elif arg['volume'] and not arg['pattern'] or arg['volume'] and arg['pattern'] and arg['Force'] or arg['Force']:
                    if len(fs_map_hash) == 0: 
                        if arg['volume'] and arg['pattern']:
                            print('The snapRevert command resulted in an error:\tNo volumes exist matching --volume substring %s in region %s.' % (arg['volume'],region))
                        elif arg['volume']:
                            print('The snapRevert command resulted in an error:\tNo volumes exist matching --volume %s in region %s.' % (arg['volume'],region))
                        else: 
                            print('The snapRevert command resulted in an error:\tNo volumes exist in region %s.' % (region))
                        exit()
                    else:
                        #@# capture snapshot info for volumes
                        snapshot_status, json_snapshot_object = submit_api_request(command = 'Snapshots',
                                                                                   direction = 'GET',
                                                                                   headers = headers,
                                                                                   region = region,
                                                                                   url = url)
                        #@# Check for errors in base rest call
                        error_check(body = json_snapshot_object,
                                    status_code = snapshot_status,
                                    url = url)
            
                        #@# print snapshots for selected volumes based on volume name
                        fs_snap_hash = snapshot_extract_info(fs_map_hash = fs_map_hash,
                                                             prettify = False,
                                                             snap_hash = json_snapshot_object)
    
                        tracking_reversions = 0
                        if fs_snap_hash is not None: 
                            for volume in fs_snap_hash.keys():
                                for index in range(0,len(fs_snap_hash[volume]['snapshots'])):
                                    if fs_snap_hash[volume]['snapshots'][index]['name'] == arg['name']:
                                        snapshotId = fs_snap_hash[volume]['snapshots'][index]['snapshotId']
                                        fileSystemId = fs_map_hash[volume]['fileSystemId']
                                        command = 'FileSystems/' + fileSystemId + '/Revert'
                                        data = {'region':region,'snapshotId':snapshotId, 'fileSystemId':fileSystemId}
                                        if preview is False:
                                            snapshot_status, json_snapshot_object = submit_api_request(command = command,
                                                                                                       data = data,
                                                                                                       direction = 'POST',
                                                                                                       headers = headers,
                                                                                                       region = region,
                                                                                                       url = url)
                                    
                                            #@# Check for errors in base rest call
                                            error_check(body = json_snapshot_object,
                                                        status_code = snapshot_status,
                                                        url = url)
                                            print('Snapshot Revert submitted for snapshot %s:\n\tvolume:%s\n\tsnapshot:%s' % (arg['name'],volume,snapshotId))
                                        else:
                                            print('Snapshot Revert simulated for snapshot %s:\n\tvolume:%s\n\tsnapshot:%s' % (arg['name'],volume,snapshotId))
                                        tracking_reversions += 1 
                            exit()
                        if tracking_reversions == 0:
                            print('The snapRevert command resulted in zero volume reversions: :\tNo volumes contained snapshot %s' % (arg['name']))
                        exit()
                else:
                    print('The snapRevert command resulted in an error:\tThe required flag --name requires additional options.')
                    snapRevert_error_message()
            else:
                print('The snapRevert command resulted in an error:\tThe required flag --name name was not specified.')
                snapRevert_error_message()
           
            
    exit()       

 


##########################################################
#                     Primary Functions
##########################################################

def is_number(number = None):
    try:
        int(number)
        local_error = False
    except: 
        local_error = True
    return local_error 

'''
verify characters are allowable, only letters, numbers, and - are allowed
'''
def is_ord(my_string = None, position = None):
    if position == 0:
        if ord(my_string) >= 65 and  ord(my_string) <= 90 or ord(my_string) >= 97 and ord(my_string) <= 122:
           value = False
        else:
           value = True
    else:
        if ord(my_string) >= 65 and ord(my_string) <= 90 or ord(my_string) >= 97 and ord(my_string) <= 122\
                                or ord(my_string) >= 48 and ord(my_string) <= 57 or ord(my_string) == 45:
           value = False
        else:
           value = True
    return value
         

'''
Get the the json object for working with again and again
'''
def submit_api_request( command = None, data = None, direction = None, headers = None, region = None, url = None):
    if direction == 'GET':
        r = requests.get(url + '/' + command, headers = headers)
        api_error_print(region = region, request = r)
    elif direction == 'POST':
        r = requests.post(url + '/' + command, data = json.dumps(data), headers = headers)
        api_error_print(region = region, request = r)
    elif direction == 'PUT':
        r = requests.put(url + '/' + command, data = json.dumps(data), headers = headers)
        api_error_print(region = region, request = r)
    elif direction == 'DELETE':
        r = requests.delete(url + '/' + command, headers = headers)
        api_error_print(region = region, request = r)
    return r.status_code,r.json()

#Error Printing If API Call Triggered Error
def api_error_print(region = None, request = None):
    if 'message' in request.json():
        print('SDE returned error code %s for command in region %s' % (request.json()['code'],region)) 

'''
For now exit if error code != 200
'''
def error_check(status_code = None, body = None, url = None): 
    if status_code < 200 or status_code >= 300:
        if status_code == 404:
            print('\tThe specified url could not be found (404):\tcheck validity of the url.\nurl: %s\nmessage: %s' % (url,body['message']))
        elif status_code == 403:
            print('\tAccess to the specified url is forbidden (403):\tcheck validity of apikey and secretkey')
        else:
            print('\t%s' % (body['message']))
        exit()

'''
get the hash of file system ids associated with creation tokens
key == export name
value == [filesystem id, index position inside base json object]
return == hash of export names : [filesystem id, index position]
'''
def create_export_to_fsid_hash(filesystems = None, json_object = None, region = None):
    fs_map_hash = {}
    if filesystems is not None:
        for mount in filesystems:
            for idx in range(0,len(json_object)):
                if mount == json_object[idx]['creationToken'] and region == json_object[idx]['region']:
                    add_volumes_to_fs_hash(json_object = json_object, index = idx, mount = mount, fs_map_hash = fs_map_hash)
    else:
        for idx in range(0,len(json_object)):
            if json_object[idx]['region'] == region:
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
    print (json.dumps(my_hash,
                     sort_keys = True,
                     indent = 4,
                     separators = (',', ': ')))


##########################################################
#                     Volume Functions
##########################################################
 
'''
if there is an fs_hash (which is a mapping of specific volumes to query,
extract full volume info for those volumes, otherwise get info for all
'''
def extract_fs_info_for_vols_by_name(fs_map_hash = None,
                                     json_object = None,
                                     headers = None,
                                     region = None,
                                     url = None):
    fs_hash = {}
    for mount in fs_map_hash.keys():
        fs_hash[mount] = {}
        add_fs_info_for_vols_by_name(fs_hash = fs_hash,
                                     fs_map_hash = fs_map_hash,
                                     json_object = json_object,
                                     headers = headers,
                                     mount = mount,
                                     region = region,
                                     url = url)
    pretty_hash(fs_hash)

'''
Helper function to extract attributes about each volume,
this function call extract_mount_target_info to get the ip address associated
'''
def add_fs_info_for_vols_by_name(fs_hash = None,
                                 fs_map_hash = None,
                                 json_object = None,
                                 headers = None,
                                 mount = None,
                                 region = None,
                                 url = None):
    for attribute in json_object[fs_map_hash[mount]['index']].keys():
       fs_hash[mount][attribute] = json_object[fs_map_hash[mount]['index']][attribute]
       if attribute == 'fileSystemId':
           extract_mount_target_info_for_vols_by_name(fs_hash = fs_hash,
                                                      fileSystemId = fs_hash[mount][attribute],
                                                      headers = headers,
                                                      mount = mount,
                                                      region = region,
                                                      url = url)
    bandwidthMB, capacityGB = bandwidth_calculator(servicelevel = fs_hash[mount]['serviceLevel'],
                                                   quotaInBytes = int(fs_hash[mount]['quotaInBytes']))
    if bandwidthMB is not None:
        fs_hash[mount]['allocatedCapacityGB'] = capacityGB
        fs_hash[mount]['availableBandwidthMB'] = bandwidthMB
        fs_hash[mount].pop('quotaInBytes')
        
    
    
'''
Issue call to create volume
'''
def volume_creation(bandwidth = None,
                    cidr = None, 
                    headers = None,
                    label = None,
                    name = None,
                    preview = None,
                    quota_in_bytes = None,
                    region = None,
                    servicelevel = None,
                    url = None):
    command =  'FileSystems'
    data = {'name':name,
        'creationToken':name,
        'region':region,
        'serviceLevel':servicelevel,
        'quotaInBytes':quota_in_bytes,
        'exportPolicy':{'rules': [ { 'ruleIndex':1, 'allowedClients':cidr, 'unixReadOnly':False, 'unixReadWrite':True, 'cifs':False,'nfsv3':True, 'nfsv4':False } ] } }
    if label:
        data['labels'] = [label]

    if preview is False:
        volume_status, json_volume_object = submit_api_request(command = command,
                                                               data = data, 
                                                               direction = 'POST', 
                                                               headers = headers,
                                                               region = region,
                                                               url = url )
        error_check(body = json_volume_object,
                    status_code = volume_status,
                    url = url)
    
    if servicelevel == 'basic':
        servicelevel_alt = 'standard'
    elif servicelevel == 'standard':
        servicelevel_alt = 'premium'
    elif servicelevel == 'extreme':
        servicelevel_alt = 'extreme'
    if preview is True:
        print('Volume Creation simlated:')
    else:
        print('Volume Creation submitted:')
    print('\tname:%s\
          \n\tcreationToken:/%s\
          \n\tregion:%s\
          \n\tserviceLevel:%s\
          \n\tallocatedCapacityGB:%s\
          \n\tavailableBandwidthMB:%s'\
          % (name,name,region,servicelevel_alt,int(quota_in_bytes) / 1000000000,bandwidth))

'''
Determine the best gigabytes and service level based upon input
input == bandwidth in MB, gigabytes in GB
output == service level and gigabytes in GB
'''

def servicelevel_and_quota_lookup(bwmb = None, gigabytes = None):
    servicelevel_and_quota_hash = quota_and_servicelevel_parser()

    bwmb = float(bwmb)
    gigabytes = float(gigabytes)
    basic_cost_per_gb = float(servicelevel_and_quota_hash['prices']['basic'])
    standard_cost_per_gb = float(servicelevel_and_quota_hash['prices']['standard'])
    extreme_cost_per_gb = float(servicelevel_and_quota_hash['prices']['extreme'])

    basic_bw_per_gb = float(servicelevel_and_quota_hash['bandwidth']['basic'])
    standard_bw_per_gb = float(servicelevel_and_quota_hash['bandwidth']['standard'])
    extreme_bw_per_gb = float(servicelevel_and_quota_hash['bandwidth']['extreme'])

    '''
    if bwmb == 0, then the user didn't know the bandwidth, so set to maximum which we've seen is 3800MB/s. 
    '''
    if bwmb == 0 or bwmb > 3800:
        bwmb = 3800
    '''
    convert mb to kb
    '''
    bwkb = bwmb * 1000.0
    
    '''
    gigabytes needed based upon bandwidth needs
    '''
    basic_gigabytes_by_bw = bwkb / basic_bw_per_gb
    if basic_gigabytes_by_bw < gigabytes:
        basic_cost = gigabytes * basic_cost_per_gb
    else:
        basic_cost = basic_gigabytes_by_bw * basic_cost_per_gb

    standard_gigabytes_by_bw = bwkb / standard_bw_per_gb
    if standard_gigabytes_by_bw  < gigabytes:
        standard_cost = gigabytes * standard_cost_per_gb
    else:
        standard_cost = standard_gigabytes_by_bw * standard_cost_per_gb

    extreme_gigabytes_by_bw = bwkb / extreme_bw_per_gb
    if extreme_gigabytes_by_bw < gigabytes:
        extreme_cost = gigabytes * extreme_cost_per_gb
    else:
        extreme_cost = extreme_gigabytes_by_bw * extreme_cost_per_gb

    '''
    calculate right service level and gigabytes based upon cost
    '''
    cost_hash = {'basic':basic_cost,'standard':standard_cost,'extreme':extreme_cost}
    capacity_hash = {'basic':basic_gigabytes_by_bw,'standard':standard_gigabytes_by_bw,'extreme':extreme_gigabytes_by_bw}
    bw_hash = {'basic':basic_bw_per_gb,'standard':standard_bw_per_gb,'extreme':extreme_bw_per_gb}
    lowest_price = min(cost_hash.values())
    for key in cost_hash.keys():
        if cost_hash[key] == lowest_price:
            servicelevel = key
            if capacity_hash[key] < gigabytes:
                gigabytes = int(math.ceil(gigabytes))
                bandwidthKB = int(math.ceil(gigabytes)) * bw_hash[servicelevel] 
            else:
                gigabytes =  int(math.ceil(capacity_hash[key]))
                bandwidthKB =  int(math.ceil(capacity_hash[key])) * bw_hash[servicelevel]
   
            '''
            convert from Bytes to GB 
            '''
            gigabytes *= 1000000000
            bandwidthMB = int(bandwidthKB / 1000)
            break

    return servicelevel, gigabytes, bandwidthMB

'''
Calculate the bandwidth based upon passed in service level and quota
'''
def bandwidth_calculator(servicelevel = None, quotaInBytes = None):
    servicelevel_and_quota_hash = quota_and_servicelevel_parser()
    '''
    gigabytes converted from Bytes to KB
    '''
    #quotaInBytes *= 1000000000
    if servicelevel in servicelevel_and_quota_hash['bandwidth'].keys():
        capacityGB = quotaInBytes / 1000000000
        bandwidthMB = (capacityGB * servicelevel_and_quota_hash['bandwidth'][servicelevel]) / 1000
    else:
        bandwidthMB = None
        capacityGB = None
    return bandwidthMB, capacityGB

'''
check health of cidr
'''
def cidr_rule_check(cidr=None):
    error = False
    if '/' in cidr and len(cidr.split('.')) == 4:
        head = cidr.split('.')
        tail = head[3].split('/')
        for octet in head[0:3]:
             error = is_number(octet)
             if error == False:
                octet = int(octet)
                if octet < 0 or octet  > 255:
                    error = True
                    break
             else:
                error = True
                break
        if error == False:
            if len(tail) == 2:
                for octet in tail:
                    error = is_number(octet)
                    if error == False:
                        octet = int(octet)
                        if octet < 0 or octet > 255:
                            error = True
                            break
                    else:
                        error = True
                        break
    else:
        error = True
    return error
    
def volList_error_message():
    print('\nThe following vol list command line options are supported:\
           \n\tvolList --volume <volume>\t\t\t#Return information about volume X\
           \n\tvolList --name X --volume <volume> --pattern\t#Return information about volumes with names containing substring X\
           \n\tvolList\t\t\t\t\t\t#Return information about volumes with names containing substring X')
    exit()

def volCreate_error_message():
    print('\nThe following volCreate flags are required:\
           \n\t--name | -n X\t\t\t\t#Name used for volume and export path\
           \n\t--gigabytes | -g [0 < X <= 100,000]\t#Allocated volume capacity in Gigabyte\
           \n\t--bandwidth | -b [0 <= X <= 3500]\t#Requested maximum volume bandwidth in Megabytes\
           \n\t--cidr | -c 0.0.0.0/0\t\t\t#Network with acess to exported volume')
    print('\nThe following flags are optional:\
           \n\t--count | -C [ 1 <= X]\t\t\t#If specified, X volumes will be created,\
           \n\t\t\t\t\t\t#Curent count will be appended to each volume name\
           \n\t\t\t\t\t\t#The artifacts of the required flags will be applied to each volume')
    print('\t--label | -l X\t\t\t\t#Additional metadata for the volume(s)')
    print('\t--preview | -l X\t\t\t\t#results is a simulated rather than actual volume creation')
    exit()

def volDelete_error_message():
    print('\nThe following vol deletion command line options are supported:\
           \n\tvolDelete --name X --volume <volume> [--preview]\t\t\t#Delete volume X\
           \n\tvolDelete --name X --volume <volume> --pattern --Force [--preview]\t#Delete volumes with names containing substring X')
    exit()

##########################################################
#                     Mount Target Functions
##########################################################

'''
Add mount target information for each volume fsid passed in
'''
def extract_mount_target_info_for_vols_by_name(fs_hash = None,
                                               fileSystemId = None,
                                               headers = None,
                                               mount = None,
                                               region = None,
                                               url = None):

    status, json_mountarget_object = submit_api_request(command = ('FileSystems/%s/MountTargets' % (fileSystemId)),
                                                                   direction = 'GET',
                                                                   headers = headers,
                                                                   region = region,
                                                                   url = url)
    error_check(body = json_mountarget_object,
                status_code = status,
                url = url)
    
    if len(json_mountarget_object) > 0:
        for attribute in json_mountarget_object[0]: 
            fs_hash[mount][attribute] = json_mountarget_object[0][attribute]
    else:
        if fs_hash[mount]['lifeCycleStateDetails'] == 'Creation in progress':
            fs_hash[mount]['MountTarget'] = 'Creating: No Mount Target Exists'
        else:
            fs_hash[mount]['MountTarget'] = 'Error: No Mount Target Exists'



##########################################################
#                     Snapshot Functions
##########################################################



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
                '''
                Only work with snapshots in 'available' state
                '''
                if snap_hash[index]['lifeCycleState'] == 'available':
                    if mount not in fs_snap_hash:
                        fs_snap_hash[mount] = {}
                        fs_snap_hash[mount]['fileSystemId'] = fs_map_hash[mount]['fileSystemId']
                        fs_snap_hash[mount]['snapshots'] = []
                    fs_snap_hash[mount]['snapshots'].append(snap_hash[index])

    if len(fs_snap_hash) > 0:
        if prettify: 
            pretty_hash(fs_snap_hash)
        return fs_snap_hash

def snapList_error_message():
    print('\nThe following snapshot list command line options are supported:\
           \n\tsnapList --volume <volume>\t\t\t#List all snapshots for specified volume.\
           \n\tsnapList --volume <volume> --pattern\t#List all snapshot from volumes with names containing Y.\
           \n\tsnapList\t\t\t\t#List all snapshot accross all volumes.')
    exit()

def snapCreate_error_message():
    print('\nThe following snapshot creation command line options are supported:\
           \n\tsnapCreate --name X --volume <volume> [--preview]\t\t#Create snapshot X on volume Y.\
           \n\tsnapCreate --name X --volume <volume> --pattern [--preview]\t#Create snapshot X on volumes with names containing substring Y.\
           \n\tsnapCreate --name X [--preview]\t\t\t\t#Create snapshot X on all volumes.')
    exit()
    
def snapRevert_error_message():
    print('\nThe following snapshot reversion command line options are supported:\
           \n\tsnapRevert --name X --volume <volume> [--preview]\t\t\t#Revert to Snapshot X for volume Y.\
           \n\tsnapRevert --name X --volume <volume> --pattern --Force [--preview]\t#Revert to snapshot X for volumes with names containing Y.\
           \n\tsnapRevert --name X --Force  [--preview]\t\t\t\t#Revert to snapshot X wherever it is found.')
    exit()

def snapDelete_error_message():
    print('\nThe following snapshot deletion command line options are supported:\
           \n\tsnapDelete --name X --volume <volume> [--preview]\t\t\t#Delete Snapshot X from volume Y.\
           \n\tsnapDelete --name X --volume <volume> --pattern --Force [--preview]\t#Delete Snapshot X from volumes with names containing Y.\
           \n\tsnapDelete --name X --Force  [--preview]\t\t\t\t#Delete Snapshot X wherever it is found.')
    exit()


'''MAIN'''
command_line()
