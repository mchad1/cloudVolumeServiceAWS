###!/usr/bin/python
import sys
sys.path.append(sys.path[0] + "/lib")
import argparse
import json
import math
import os
import requests
import userio
import orautils
from time import sleep
from  datetime import datetime
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

#Return epoch
def date_to_epoch(created = None, now = None):
    #Split the created string for now becuase I don't know how to use Z
    if now:
        #Convert creation time string to datetime
        created = str(datetime.now()).split('.')[0]
        #Convert creation time string to datetime
        created = datetime.strptime(str(created), '%Y-%m-%d %H:%M:%S')
    else:
        created = created.split('.')[0]
        #Convert creation time string to datetime
        created = datetime.strptime(created, '%Y-%m-%dT%H:%M:%S')
    #Return creation time in epoch
    return datetime.timestamp(created)


def command_line():
    parser = argparse.ArgumentParser(prog='cvs-aws.py',description='%(prog)s is used to issue commands to your NetApp Cloud Volumes Service on your behalf.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--oracleBackup',action='store_const',const=True,)
    group.add_argument('--oracleRevert',action='store_const',const=True,)
    group.add_argument('--snapCreate',action='store_const',const=True,)
    group.add_argument('--snapDelete',action='store_const',const=True,)
    group.add_argument('--snapKeepByCount', action='store_const',const=True,help='Keep only the newest N snapshots, delete the rest for given volumes')
    group.add_argument('--snapKeepByDays', action='store_const',const=True,help='Keep only the snapshots for X days, delete the rest for given volumes')
    group.add_argument('--snapList', action='store_const',const=True,)
    group.add_argument('--snapRevert', action='store_const',const=True,)
    group.add_argument('--volCreate',action='store_const',const=True,)
    group.add_argument('--volDelete',action='store_const',const=True,)
    group.add_argument('--volList', action='store_const',const=True,)
    parser.add_argument('--project','-p',type=str,help='Enter the project name to interact with, otherwise the default project is selected')
    parser.add_argument('--preview', action='store_const',const=True,help='If specfied, a try befor your buy simulation is run rather than\
                                                                         the actual command. Supports all delete and create and Oracle commands.')
    parser.add_argument('--Force', action='store_const',const=True,help='If specfied, enables substring\'s to work *Delete and Revert\
                                                                         operations. Supports all *Delete operations as well as snapRevert.')
    parser.add_argument('--volPattern','-P',action='store_const',const=True,help='Search for volumes using name as substring.\
                                                                               Supports snapList and volList nativley, snapDelete\
                                                                               and volDelete as well as snapRevert with --Force.\n\n')
    parser.add_argument('--snapPattern','-S',action='store_const',const=True,help='Search for snapshots using name as substring.\
                                                                               Supports snap*.\n\n')
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
    parser.add_argument('--count','-C',type=str,help='Specify the number of volumes to create, or the number of snapshots to keep. Supports volCreate, snapKeepBy*')
    parser.add_argument('--configFile','-f',type=str,help='Enter the json config file to extract volume lists from, used with oracleBackup')
    parser.add_argument('--oracleSid','-s',type=str,help='Enter the Oracle SID to backup')
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

    if arg['bandwidth']:
        bandwidth = arg['bandwidth']    
    else:
        bandwidth = None

    if arg['cidr']:
        cidr = arg['cidr']    
    else:
        cidr = None

    if arg['count']:
        count = arg['count']    
    else:
        count = None

    if arg['gigabytes']:
        gigabytes = arg['gigabytes']    
    else:
        gigabytes = None

    if arg['label']:
        label = arg['label']    
    else:
        label = None

    if arg['configFile']:
        configFile = arg['configFile']
    else:
        configFile = None

    if arg['oracleSid']:
        oracleSid = arg['oracleSid']
    else:
        oracleSid = None





    #Oracle recover commands
    if arg['oracleRevert'] and not arg['configFile'] and not arg['oracleSid'] and not arg['name']:
        print('oracleRevert as well as configlFile, oracleSid and name <snapshot name> must be entered together, exiting') 
        exit()

    #Oracle hot Backup Mode
    if arg['oracleBackup'] and not arg['configFile'] and not arg['oracleSid']:
        print('oracleBackup as well as configlFile and oracleSid muct be entered together, exiting') 
        exit()

      

    if arg['snapPattern'] and not arg['name']:
        print('snapPattern has been entered without specifiying --name, exiting') 
        exit()
    elif arg['snapPattern'] and arg['name']:
        snapPattern = arg['snapPattern']
        name = arg['name']
    else:
        snapPattern = None

    if arg['name']:
        name = arg['name']
    else:
        name = None

    #Use the region specified in the command line if present, otherwise go with that returned in the config file
    if arg['region']:
        region = arg['region']
    
    if arg['count']: 
        local_error = is_number(arg['count'])
        if local_error == True:
            error_value['count_int'] = 'count is a non integer'
        elif int(arg['count']) < 1:
            count = 1
        else:
            count = int(arg['count'])
        if local_error == True:
            quit()

    if arg['Force']:
        force = arg['Force']
    else:
        force = None
        
    if arg['volume']:
        volume = arg['volume']
    else:
        volume = None
    
        
    if arg['volPattern']:
        volPattern = arg['volPattern']
    else:
        volPattern = None
        
    if arg['snapKeepByDays']:
        snapKeepByDays = arg['snapKeepByDays']
    else:
        snapKeepByDays = None
        
    if arg['snapKeepByCount']:
        snapKeepByCount = arg['snapKeepByCount']
    else:
        snapKeepByCount = None


 
    
    if arg['oracleRevert'] or arg['oracleBackup'] or arg['volList'] or arg['snapList'] or arg['snapCreate'] or arg['snapDelete'] or arg['volDelete'] or arg['volCreate'] or arg['snapRevert'] or arg['snapKeepByCount'] or arg['snapKeepByDays']:
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
        if arg['volume'] and not arg['volPattern']:
            fs_map_hash = create_export_to_fsid_hash(filesystems = [arg['volume']], json_object = json_volume_object, region = region)
        elif arg['volume'] and arg['volPattern']:
            fs_map_hash = create_export_to_fsid_hash(json_object = json_volume_object, region = region)
            for element in list(fs_map_hash):
                #for element in fs_map_hash.keys():
                if arg['volume'] not in element:
                    fs_map_hash.pop(element)
        else: 
            fs_map_hash = create_export_to_fsid_hash(json_object = json_volume_object, region = region)

    if arg['volList']:
        volList( force = force, fs_map_hash = fs_map_hash, headers = headers, json_volume_object = json_volume_object, region = region, url = url, volPattern = volPattern, volume = volume)
    elif arg['volCreate']:
        volCreate( bandwidth = bandwidth, cidr = cidr, count = count, force = force, fs_map_hash = fs_map_hash, gigabytes = gigabytes, json_volume_object = json_volume_object, headers = headers, label = label, name = name, preview = preview, region = region, url = url, volPattern = volPattern, volume = volume)
    elif arg['volDelete']:
        volDelete( force = force,fs_map_hash = fs_map_hash,headers = headers, preview = preview, region = region, url = url, volPattern = volPattern, volume = volume)
    elif arg['snapList']:     
        snapList( force = force, fs_map_hash = fs_map_hash, headers = headers, json_volume_object = json_volume_object, name = name, region = region, url = url, volPattern = volPattern, snapPattern = snapPattern, volume = volume)
    elif arg['snapCreate']:
        snapCreate( force = force, fs_map_hash = fs_map_hash, headers = headers, name = name, preview = preview, region = region, url = url, volPattern = volPattern, volume = volume)
    elif arg['snapDelete']:
        snapDelete( force = force, fs_map_hash = fs_map_hash, headers = headers, name = name, preview = preview, region = region, snapPattern = snapPattern, url = url, volPattern = volPattern, volume = volume)
    elif arg['snapKeepByCount'] or arg['snapKeepByDays']:
        snapKeepByStar(count = count, force = force, fs_map_hash = fs_map_hash, headers = headers, name = name, preview = preview, region = region, snapPattern = snapPattern, snapKeepByDays = snapKeepByDays, snapKeepByCount = snapKeepByCount, url = url, volPattern = volPattern, volume = volume)
    elif arg['snapRevert']:
        snapRevert(force = force, fs_map_hash = fs_map_hash, headers = headers, name = name, preview = preview, region = region, url = url, volPattern = volPattern, volume = volume)
    elif arg['oracleBackup']:
        oracle_hot_backup(configFile = configFile, fs_map_hash = fs_map_hash, headers = headers, oracleSid = oracleSid, preview = preview, project = project, region = region, url = url)
    elif arg['oracleRevert']:
        oracle_recover_database(configFile = configFile, fs_map_hash = fs_map_hash, headers = headers, name = name, oracleSid = oracleSid, preview = preview, project = project, region = region, url = url)
        
        ##########################################################
        #                      Volume Commands
        ##########################################################
        
def volList(
            force = None,
            fs_map_hash = None,
            headers = None,
            json_volume_object = None,
            region = None,
            url = None,
            volPattern = None,
            volume = None
           ):

    #Get a list of all volumes matching inputted -volume and --volPattern if specified, or alternativley all volumes
    if force:
        print('The volList command resulted in an error.\tThe --Force flag is not supported.')
        volList_error_message()
    elif volPattern and not volume:
        print('The volList command resulted in an error:\tThe --volPattern flag requires --volume <volume>.')
        volList_error_message()
    elif len(fs_map_hash) > 0:
        #@# print and capture info for specific volumes
        vol_hash = extract_fs_info_for_vols_by_name(fs_map_hash = fs_map_hash,
                                                    json_object = json_volume_object,
                                                    headers = headers,
                                                    region = region, 
                                                    url = url)
    else:
        if volume and volPattern:
            print('The volList command resulted in an error:\tNo volumes exist matching --volume substring %s in region %s.' % (volume,region))
        elif volume:
            print('The volList command resulted in an error:\tNo volumes exist matching --volume %s in region %s.' % (volume,region))
        else: 
            print('The volList command resulted in an error:\tNo volumes exist in region %s.' % (region))
        exit()



def volCreate(
            bandwidth = None,
            cidr = None,
            count = None,
            force = None,
            fs_map_hash = None,
            gigabytes = None,
            json_volume_object = None,
            headers = None,
            label = None,
            name = None,
            preview = None,
            region = None,
            url = None,
            volPattern = None,
            volume = None
           ):

    if name:
        if gigabytes and bandwidth and cidr and name and region:
            error = False 
            error_value = {}
   
            if len(name) < 1:
                error = True
                error_value['name_length'] = ('Volume Name length is too short: %s, names must be => 1 and <= 33 characters' % (len(name)))
            if len(name) > 33:
                error = True
                error_value['name_length'] = ('Volume Name length is too long: %s, names must be => 1 and <= 33 characters' % (len(name)))
            for index in range(0,len(name)):
                local_error = is_ord(my_string = name[index], position = index)
                if local_error == True:
                    error = True
                    error_value['name_illegal_character'] = 'Illegal char type'
            local_error = is_number(gigabytes)
            if local_error == True:
                error = True
                error_value['gigabytes_integer'] = 'Capacity was not a numeric value'
            elif int(gigabytes) < 100 or int(gigabytes) > 100000:
                error = True
                error_value['size'] = 'Capacity was either smaller than 100GB or greater than 100,000GB'
            local_error = is_number(bandwidth)
            if local_error == True:
                error = True
                error_value['bw_integer'] = 'Bandwidth was not a numeric value'
            elif int(bandwidth) < 0:
                error = True
                error_value['bw'] = ('Negative value entered: %s, requested values must be => 0.  If value == 0 or value > 3800 then maximum bandwidth will be assigned' % (bandwidth))
            servicelevel, quotainbytes, bandwidthMB = servicelevel_and_quota_lookup(bwmb = bandwidth, gigabytes = gigabytes)
            local_error = cidr_rule_check(cidr)
            if local_error == True:
                error = True
                error_value['cidr'] = ('Cidr rule is incorrect: %s, value must be in the form of X.X.X.X/X where all values for X are between 0 and 255' % (cidr))
            if not count:
                count = 1
            if label:
                label = label
            else:
                label = None
  
            if error == False: 
                if count == 1:
                    name = name
                    volume_creation(bandwidth = bandwidthMB,
                                    cidr = cidr,
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
                        newname = ('%s-%s' % (name,count))
                        volume_creation(bandwidth = bandwidthMB,
                                        cidr = cidr,
                                        headers = headers,
                                        label = label,
                                        name = newname,
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

def volProtect(fs_map_hash = None):
    mounted_volumes = []
    with open('/etc/mtab','r') as mt:
        content = mt.readlines() 
    for volume in fs_map_hash.keys():
       for export in content:
           if volume in export:
               mounted_volumes.append(volume)
    if len(mounted_volumes) > 0:
        print('\nThe Volume Delete command cannot be safely run as (%s) requested volumes are mounted locally' % (len(mounted_volumes)))
        print('The mounted volumes are listed below:\n')
        for volume in mounted_volumes:
            print('Volume:\t%s' % (volume))
        print('\n')
        exit()

#Volume delete does not support volPattern matching or empty sets, a volume name must be entered
def volDelete(
            force = None,	
            fs_map_hash = None,	
            headers = None,
            preview = None,
            region = None,
            url = None,
            volPattern = None,
            volume = None
           ):
    volProtect(fs_map_hash = fs_map_hash)
    if volume:
        if volPattern  and not force:
            print('The volDelete command resulted in an error:\tThe --volPattern flag requires both --volume <volume> and --Force.')
            volDelete_error_message()
        elif volume and not volPattern or volume and volPattern and force:
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
                if volPattern:
                    print('The volDelete command resulted in an error:\tNo volumes exist matching --volume substring %s in region %s.' % (volume,region))
                else:
                    print('The volDelete command resulted in an error:\tNo volumes exist matching --volume %s in region %s.' % (volume,region))
                exit()
        else:
            volDelete_error_message()
    else:
        print('The volDelete command resulted in an error.\tThe required flag --volume was not specified.')
        volDelete_error_message()


        ##########################################################
        #                     Snapshot Commands
        ##########################################################
        
def snapList(
            force = None,
            fs_map_hash = None,
            headers = None,
            json_volume_object = None,
            name = None,
            region = None,
            url = None,
            volPattern = None,
            snapPattern = None,
            volume = None
           ):

    #Get a list of all volumes matching inputted -volume and --volPattern if specified, or alternativley all volumes

    #@# capture snapshot infor for volumes
    if snapPattern and not name:
        print('The snapList command resulted in an error:\tCommand line parameter --snapPattern requires --volume <volume>')
        snapList_error_message()
    if volPattern and not volume:
        print('The snapList command resulted in an error:\tCommand line parameter --volPattern requires --volume <volume>')
        snapList_error_message()
    elif force:
        print('The snapList command resulted in an error:\tCommand line parameter --Force is not supported')
        snapList_error_message()
    else:
        if len(fs_map_hash) == 0: 
            if volume and volPattern:
                print('The snapList command resulted in an error:\tNo volumes exist matching --volume substring %s region %s.' % (volume,region))
            elif volume:
                print('The snapList command resulted in an error:\tNo volumes exist matching --volume %s in region %s.' % (volume,region))
            elif name and not snapPattern:
                print('The snapList command resulted in an error:\tNo snapshots exist matching --name %s in region %s.' % (name,region))
            elif name and snapPattern:
                print('The snapList command resulted in an error:\tNo snapshots exist matching the pattern --name %s in region %s.' % (name,region))
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
            snapshot_extract_info(fs_map_hash = fs_map_hash, name = name, prettify = True, snap_hash = json_snapshot_object, snapPattern = snapPattern)

def snapCreate(
               force = None,
               fs_map_hash = None,
               headers = None,
               name = None,
               preview = None,
               region = None,
               url = None,
               volPattern = None,
               volume = None,
               volume_list = None
               ):
    if name:
        if force:
            print('The snapCreate command resulted in an error.\tThe --Force flag is not supported.')
            snapCreate_error_message()
        elif volume and not volPattern or volume and volPattern or not volume and not volPattern:
            data = {'region':region,'name':name}
            if len(fs_map_hash) > 0:
                for volume in fs_map_hash.keys():
                    if volume_list and volume in volume_list or not volume_list:
                        command = 'FileSystems/' + fs_map_hash[volume]['fileSystemId'] + '/Snapshots'
                        if not preview:
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
                            print('Snapshot Creation submitted:\n\tvolume:%s:\n\tname:%s' % (volume,name))
                        else:
                            print('Snapshot Creation simulated:\n\tvolume:%s:\n\tname:%s' % (volume,name))
                #exit()
                 
            else:
                if volume and volPattern:
                    print('The snapCreate command resulted in an error:\tNo volumes exist matching --volume substring %s in region %s.' % (volume,region))
                elif volume:
                    print('The snapCreate command resulted in an error:\tNo volumes exist matching --volume %s in region %s.' % (volume,region))
                else: 
                    print('The snapCreate command resulted in an error:\tNo volumes exist in region %s.' % (region))
                #exit()

    else:
        print('The snapCreate command resulted in an error.\tThe required flag --name name was not specified.')
        snapCreate_error_message()
        


def snapDelete(
               force = None,
               fs_map_hash = None,
               headers = None,
               name = None,
               preview = None,
               region = None,
               snapPattern = None,
               url = None,
               volPattern = None,
               volume = None
              ):

    #snapDelete Code
    if name and snapPattern and volume and volPattern and force:
        fs_snap_hash = snapshot_delete_shared_function(fs_map_hash = fs_map_hash, 
                                                       headers = headers, 
                                                       prettify = False,
                                                       region = region,
                                                       url = url,
                                                       volume = volume)

        submit_snap_deletions(force = force,
                              fs_map_hash = fs_map_hash,
                              fs_snap_hash = fs_snap_hash,
                              headers = headers,
                              name = name,
                              preview = preview,
                              region = region,
                              snapPattern = snapPattern,
                              volPattern = volPattern,
                              url = url) 

    if name and snapPattern and volume and force:
        fs_snap_hash = snapshot_delete_shared_function(fs_map_hash = fs_map_hash, 
                                                       headers = headers, 
                                                       prettify = False,
                                                       region = region,
                                                       url = url,
                                                       volume = volume)

        submit_snap_deletions(force = force,
                              fs_map_hash = fs_map_hash,
                              fs_snap_hash = fs_snap_hash,
                              headers = headers,
                              name = name,
                              preview = preview,
                              region = region,
                              snapPattern = snapPattern,
                              url = url) 

    elif name and volPattern and volume and force:
        print(1)
        fs_snap_hash = snapshot_delete_shared_function(fs_map_hash = fs_map_hash, 
                                                       headers = headers, 
                                                       prettify = False,
                                                       region = region,
                                                       url = url,
                                                       volume = volume)
        submit_snap_deletions(force = force,
                              fs_map_hash = fs_map_hash,
                              fs_snap_hash = fs_snap_hash,
                              headers = headers,
                              name = name,
                              preview = preview,
                              region = region,
                              volPattern = volPattern,
                              url = url) 

    elif name and volume and not snapPattern:
        fs_snap_hash = snapshot_delete_shared_function(fs_map_hash = fs_map_hash, 
                                                       headers = headers, 
                                                       prettify = False,
                                                       region = region,
                                                       volume = volume,
                                                       url = url)
        submit_snap_deletions(fs_map_hash = fs_map_hash,
                              fs_snap_hash = fs_snap_hash,
                              headers = headers,
                              name = name,
                              preview = preview,
                              region = region,
                              url = url) 

    elif name and force:
        fs_snap_hash = snapshot_delete_shared_function(fs_map_hash = fs_map_hash, 
                                                       headers = headers, 
                                                       prettify = False,
                                                       region = region,
                                                       url = url)
        submit_snap_deletions(force = force,
                              fs_map_hash = fs_map_hash,
                              fs_snap_hash = fs_snap_hash,
                              headers = headers,
                              name = name,
                              preview = preview,
                              region = region,
                              url = url) 

    elif volPattern and force and not volume:
        print('Error The snapDelete command resulted in an error:\t--volume flag missing')
        snapDelete_error_message()

    elif force and volume and not volPattern:
        print('The snapDelete command resulted in an error:\tIncorrect Command line')
        snapDelete_error_message()

    elif name and volPattern and volume and not force: 
        print('Error The snapDelete command resulted in an error:\t--Force flag missing')
        snapDelete_error_message()
    elif name and volPattern and not volume and force: 
        print('Error The snapDelete command resulted in an error:\t--Force flag missing and --volume missing')
        snapDelete_error_message()
    elif name and snapPattern and not force: 
        print('Error The snapDelete command resulted in an error:\t--Force flag missing')
        snapDelete_error_message()
    elif name and not volume and not force: 
        print('Error The snapDelete command resulted in an error:\t--Force flag missing')
        snapDelete_error_message()
    else:
        print('The snapDelete command resulted in an error:\tThe required flag --name name was not specified.')
        snapDelete_error_message()


def snapKeepByStar(
               count = None,
               force = None,
               fs_map_hash = None,
               headers = None,
               name = None,
               preview = None,
               region = None,
               snapPattern = None,
               snapKeepByDays = None,
               snapKeepByCount = None,
               url = None,
               volPattern = None,
               volume = None
               ):
    #snapKeepByCount Code used to ensure that a volume only has the desired number of snapshots - all others get purged
    #snapKeepByDays Code used to ensure that a volume only keep snapshots for X days - all others get purged
    #Added at the request of Jeff Steiner for Oracle support
    if not count and not volume and not force :
        if snapKeepByDays:
            print('The snapKeepByDays command resulted in an error:\tThe --snapKeepByDays flag requires --count <int>, --volume <substring> and --force.')
            snapKeepByDays_error_message()
        else:
            print('The snapKeepByCount command resulted in an error:\tThe --snapKeepByCount flag requires --count <int>, --volume <substring> and --force.')
            snapKeepByCount_error_message()
    if not count or not volume:
        if snapKeepByDays:
            print('The snapKeepByDays command resulted in an error:\tThe --snapKeepByDays flag requires --count <int> and --volume <substring> in conjunction with --force.')
            snapKeepByDays_error_message()
        else:
            print('The snapKeepByCount command resulted in an error:\tThe --snapKeepByCount flag requires --count <int> and --volume <substring> in conjunction with --force.')
            snapKeepByCount_error_message()
    if not force or not volume:
        if snapKeepByDays:
            print('The snapKeepByDays command resulted in an error:\tThe --snapKeepByDays flag requires --force and --volume <substring> in conjunction with --count.')
            snapKeepByDays_error_message()
        else:
            print('The snapKeepByCount command resulted in an error:\tThe --snapKeepByCount flag requires --force and --volume <substring> in conjunction with --count.')
            snapKeepByCount_error_message()
    if not force or not count:
        if snapKeepByDays:
            print('The snapKeepByDays command resulted in an error:\tThe --snapKeepByDays flag requires --force and --count <int> in conjunction with --volume.')
            snapKeepByDays_error_message()
        else:
            print('The snapKeepByCount command resulted in an error:\tThe --snapKeepByCount flag requires --force and --count <int> in conjunction with --volume.')
            snapKeepByCount_error_message()
    if snapKeepByDays and name and not snapPattern:
        if snapKeepByDays:
            print('The snapKeepByDays command resulted in an error:\tCommand line parameter --name <name> requires --snapPattern')
            snapKeepByDays_error_message()
        else:
            print('The snapKeepByCount command resulted in an error:\tCommand line parameter --name <name> requires --snapPattern')
            snapKeepByCount_error_message()
    elif volume and not volPattern or volume and volPattern and force or force :
        fs_snap_hash = snapshot_delete_shared_function(fs_map_hash = fs_map_hash, 
                                                       headers = headers, 
                                                       prettify = False,
                                                       region = region,
                                                       url = url,
                                                       volume = volume)
        tracking_deletions = 0
        if fs_snap_hash is not None: 
            for volume in fs_snap_hash.keys():
                fileSystemId = fs_map_hash[volume]['fileSystemId']
                epoch_and_snap_id_hash = {}
                epoch_and_snap_name_hash = {}
                epoch_list = []
                #Record the number of snapshots in the volume
                for index in range(0,len(fs_snap_hash[volume]['snapshots'])):
                    #If snapPattern is specified and name is in the snapshot, load the snapshot into the hashes, don't track the rest
                    if snapPattern and name in fs_snap_hash[volume]['snapshots'][index]['name']:
                        #key = epoch, value = snapid
                        epoch_and_snap_id_hash[fs_snap_hash[volume]['snapshots'][index]['epochTime']] = fs_snap_hash[volume]['snapshots'][index]['snapshotId']
                        #key = epoch, value = name
                        epoch_and_snap_name_hash[fs_snap_hash[volume]['snapshots'][index]['epochTime']] = fs_snap_hash[volume]['snapshots'][index]['name']
                        #list of epoch
                        epoch_list.append(fs_snap_hash[volume]['snapshots'][index]['epochTime'])
                    #If snapPattern is not specified, load all snapshots into the two hashes
                    elif not snapPattern:
                        #key = epoch, value = snapid
                        epoch_and_snap_id_hash[fs_snap_hash[volume]['snapshots'][index]['epochTime']] = fs_snap_hash[volume]['snapshots'][index]['snapshotId']
                        #key = epoch, value = name
                        epoch_and_snap_name_hash[fs_snap_hash[volume]['snapshots'][index]['epochTime']] = fs_snap_hash[volume]['snapshots'][index]['name']
                        #list of epoch
                        epoch_list.append(fs_snap_hash[volume]['snapshots'][index]['epochTime'])
                #Sort the epoch list in place
                epoch_list.sort(reverse = True)           


                #Keep the specified number of snapshots, delete the rest 
                #Always keep at least one around
                if snapKeepByCount:
                    for index in range(0,len(epoch_list)):
                        if index >= count:
                            volume
                            snapshotName = epoch_and_snap_name_hash[epoch_list[index]]
                            snapshotId = epoch_and_snap_id_hash[epoch_list[index]]
                            timeEpoch = epoch_list[index]
                            print('Deleteing: Volume: %s  VolId: %s SnapName: %s SnapID: %s Time: %s' % (volume,
   											                 fileSystemId,
									                                 snapshotName,
                									                 snapshotId,
									                                 timeEpoch))
                            command = ('FileSystems/%s/Snapshots/%s' % (fileSystemId,snapshotId))
                            if preview is False:
                                snapshot_status, json_snapshot_object = submit_api_request(command = command,
                                                                                           direction = 'DELETE',
                                                                                           headers = headers,
                                                                                           region = region,
                                                                                           url = url)

                #Keep the specified number of days to keep snapshots 
                #Always keep at least one around
                if snapKeepByDays:
                    now = date_to_epoch(now=True) #Time since epoch in seconds
                    day = 86400 #Seconds in a day
                    secondsToKeep = count * day
                    epochSafeToDelete = now - secondsToKeep
                    for index in range(0,len(epoch_list)):
                        if epoch_list[index] < epochSafeToDelete:
                            volume
                            snapshotName = epoch_and_snap_name_hash[epoch_list[index]]
                            snapshotId = epoch_and_snap_id_hash[epoch_list[index]]
                            timeEpoch = epoch_list[index]
                            print('Deleteing: Volume: %s  VolId: %s SnapName: %s SnapID: %s Time: %s' % (volume,
  				   					                                 fileSystemId,
        		    							                         snapshotName,
         	    										         snapshotId,
        												 timeEpoch))
                            command = ('FileSystems/%s/Snapshots/%s' % (fileSystemId,snapshotId))
                            if preview is False:
                                snapshot_status, json_snapshot_object = submit_api_request(command = command,
                                                                                           direction = 'DELETE',
                                                                                           headers = headers,
                                                                                           region = region,
                                                                                           url = url)
    

#Revert filesystem(s) to a specific snapshot
def snapRevert(
               force = None,
               fs_map_hash = None,
               headers = None,
               name = None,
               preview = None,
               region = None,
               url = None,
               volPattern = None,
               volume = None,
               volume_list = None 
               ):
    if name:
        if volPattern  and  force and not volume:
            print('The snapRevert command resulted in an error:\tThe --volPattern flag requires both --volume <substring> and --Force.')
            snapRevert_error_message()
        elif volPattern  and  not force:
            print('The snapRevert command resulted in an error:\tThe flag --volPattern was specified without --Force.')
            snapRevert_error_message()
        elif volume_list or volume and not volPattern or volume and volPattern and force or force:
            if len(fs_map_hash) == 0: 
                if volume and volPattern:
                    print('The snapRevert command resulted in an error:\tNo volumes exist matching --volume substring %s in region %s.' % (volume,region))
                elif volume:
                    print('The snapRevert command resulted in an error:\tNo volumes exist matching --volume %s in region %s.' % (volume,region))
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
                                                     name = name,
                                                     prettify = False,
                                                     snap_hash = json_snapshot_object)
                tracking_reversions = 0
                if fs_snap_hash is not None: 
                    for volume in fs_snap_hash.keys():
                        if volume_list and volume in volume_list or not volume_list:
                            for index in range(0,len(fs_snap_hash[volume]['snapshots'])):
                                if fs_snap_hash[volume]['snapshots'][index]['name'] == name:
                                    snapshotId = fs_snap_hash[volume]['snapshots'][index]['snapshotId']
                                    fileSystemId = fs_map_hash[volume]['fileSystemId']
                                    command = 'FileSystems/' + fileSystemId + '/Revert'
                                    data = {'region':region,'snapshotId':snapshotId, 'fileSystemId':fileSystemId}
                                    if preview == False: 
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
                                        print('Snapshot Revert submitted for snapshot %s:\n\tvolume:%s\n\tsnapshot:%s' % (name,volume,snapshotId))
                                    else:
                                        print('Snapshot Revert simulated for snapshot %s:\n\tvolume:%s\n\tsnapshot:%s' % (name,volume,snapshotId))
                                    tracking_reversions += 1 
                    if tracking_reversions == 0 and preview == False:
                        print('The snapRevert command resulted in zero volume reversions: :\tNo volumes contained snapshot %s' % (name))
        else:
            print('The snapRevert command resulted in an error:\tThe required flag --name requires additional options.')
            snapRevert_error_message()
    else:
        print('The snapRevert command resulted in an error:\tThe required flag --name name was not specified.')
        snapRevert_error_message()
   


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
    sleep(1)
    if direction == 'GET':
        r = requests.get(url + '/' + command, headers = headers)
        #print(r)
        api_error_print(region = region, request = r)
    elif direction == 'POST':
        r = requests.post(url + '/' + command, data = json.dumps(data), headers = headers)
        #print(r)
        api_error_print(region = region, request = r)
    elif direction == 'PUT':
        #print(r)
        r = requests.put(url + '/' + command, data = json.dumps(data), headers = headers)
        api_error_print(region = region, request = r)
    elif direction == 'DELETE':
        r = requests.delete(url + '/' + command, headers = headers)
        #print(r)
        api_error_print(region = region, request = r)
    return r.status_code,r.json()

#Error Printing If API Call Triggered Error
def api_error_print(region = None, request = None):
    if 'message' in request.json():
        print(request.json())

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
       if attribute == 'created':
           fs_hash[mount]['epochTime'] = date_to_epoch(created = fs_hash[mount][attribute])

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
        print('Volume Creation simulated:')
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
    if bwmb == 0 or bwmb > 4500:
        bwmb = 4500 
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
           \n\tvolList --volume <volume> --volPattern\t#Return information about volumes with names containing substring X\
           \n\tvolList\t\t\t\t\t\t#Return information about volumes with names containing substring X')
    exit()

def volCreate_error_message():
    print('\nThe following volCreate flags are required:\
           \n\t--name | -n X\t\t\t\t#Name used for volume and export path\
           \n\t--gigabytes | -g [0 < X <= 100,000]\t#Allocated volume capacity in Gigabyte\
           \n\t--bandwidth | -b [0 <= X <= 4500]\t#Requested maximum volume bandwidth in Megabytes\
           \n\t--cidr | -c 0.0.0.0/0\t\t\t#Network with acess to exported volume')
    print('\nThe following flags are optional:\
           \n\t--count | -C [ 1 <= X]\t\t\t#If specified, X volumes will be created,\
           \n\t\t\t\t\t\t#Curent count will be appended to each volume name\
           \n\t\t\t\t\t\t#The artifacts of the required flags will be applied to each volume')
    print('\t--label | -l\t\t\t\t#Additional metadata for the volume(s)')
    print('\t--preview\t\t\t\t#results is a simulated rather than actual volume creation')
    exit()

def volDelete_error_message():
    print('\nThe following vol deletion command line options are supported:\
           \n\tvolDelete --name X --volume <volume> [--preview]\t\t\t#Delete volume X\
           \n\tvolDelete --name X --volume <volume> --volPattern --Force [--preview]\t#Delete volumes with names containing substring X')
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
def snapshot_extract_info(fs_map_hash = None, name = None, prettify = None, snap_hash = None, snapPattern = None):
    fs_snap_hash = {}
    for mount in fs_map_hash.keys():
        for index in range(0,len(snap_hash)):
            if snap_hash[index]['fileSystemId'] == fs_map_hash[mount]['fileSystemId']:
                if snapPattern and name:
                    if snapPattern and name in snap_hash[index]['name']:
                        '''
                        Only work with snapshots in 'available' state
                        '''
                        if snap_hash[index]['lifeCycleState'] == 'available':
                            snap_hash[index]['epochTime'] = date_to_epoch( created = snap_hash[index]['created'])
                            if mount not in fs_snap_hash: 
                                fs_snap_hash[mount] = {}
                                fs_snap_hash[mount]['fileSystemId'] = fs_map_hash[mount]['fileSystemId']
                                fs_snap_hash[mount]['snapshots'] = []
                            fs_snap_hash[mount]['snapshots'].append(snap_hash[index])
                elif not snapPattern and not name:
                    '''
                    Only work with snapshots in 'available' state
                    '''
                    if snap_hash[index]['lifeCycleState'] == 'available':
                        snap_hash[index]['epochTime'] = date_to_epoch( created = snap_hash[index]['created'])
                        if mount not in fs_snap_hash: 
                            fs_snap_hash[mount] = {}
                            fs_snap_hash[mount]['fileSystemId'] = fs_map_hash[mount]['fileSystemId']
                            fs_snap_hash[mount]['snapshots'] = []
                        fs_snap_hash[mount]['snapshots'].append(snap_hash[index])
                elif name and name == snap_hash[index]['name']:
                    '''
                    Only work with snapshots in 'available' state
                    '''
                    if snap_hash[index]['lifeCycleState'] == 'available':
                        snap_hash[index]['epochTime'] = date_to_epoch( created = snap_hash[index]['created'])
                        if mount not in fs_snap_hash: 
                            fs_snap_hash[mount] = {}
                            fs_snap_hash[mount]['fileSystemId'] = fs_map_hash[mount]['fileSystemId']
                            fs_snap_hash[mount]['snapshots'] = []
                        fs_snap_hash[mount]['snapshots'].append(snap_hash[index])


    if len(fs_snap_hash) > 0:
        if prettify: 
            pretty_hash(fs_snap_hash)
        return fs_snap_hash


#Submit deletions here
def submit_snap_deletions(force = None,
                          fs_map_hash = None,
                          fs_snap_hash = None,
                          headers = None,
                          name = None,
                          preview = None,
                          region = None,
                          snapPattern = None,
                          volPattern = None,
                          url = None): 
    tracking_deletions = 0
    if fs_snap_hash is not None: 
        for volume in fs_snap_hash.keys():
            #Use this to record if we actually deleted any snapshots
            for index in range(0,len(fs_snap_hash[volume]['snapshots'])):
                if name == fs_snap_hash[volume]['snapshots'][index]['name'] or snapPattern and name in  fs_snap_hash[volume]['snapshots'][index]['name']:
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
                        print('Snapshot Deleton Submitted: Volume: %s  VolId: %s SnapName: %s SnapID: %s' % (volume, fileSystemId, fs_snap_hash[volume]['snapshots'][index]['name'], snapshotId))
                    else:
                        print('Snapshot Deleton Simulated: Volume: %s  VolId: %s SnapName: %s SnapID: %s' % (volume, fileSystemId, fs_snap_hash[volume]['snapshots'][index]['name'], snapshotId))
                    tracking_deletions += 1 
        exit()
    if tracking_deletions == 0:
        print('The snapDelete command resulted in zero deletions: :\tNo volumes contained snapshot %s' % (name))
    exit()

def snapshot_delete_shared_function(fs_map_hash = None,
                                    headers = None,
                                    name = None,
                                    prettify = None,
                                    region = None,
                                    snapPattern = None,
                                    url = None,
                                    volPattern = None,
                                    volume = None):
    if len(fs_map_hash) == 0: 
        if volume and volPattern:
            print('The snapDelete command resulted in an error:\tNo volumes exist matching --volume substring %s in region %s.' % (volume,region))
        elif volume:
            print('The snapDelete command resulted in an error:\tNo volumes exist matching --volume %s in region %s.' % (volume,region))
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
                                             name = name,
                                             prettify = False,
                                             snap_hash = json_snapshot_object,
                                             snapPattern = snapPattern)
        return fs_snap_hash

def snapList_error_message():
    print('\nThe following snapshot list command line options are supported:\
           \n\tsnapList --volume <volume>\t\t\t#List all snapshots for specified volume.\
           \n\tsnapList --volume <volume> --volPattern\t#List all snapshot from volumes with names containing Y.\
           \n\tsnapList\t\t\t\t#List all snapshot accross all volumes.')
    exit()

def snapCreate_error_message():
    print('\nThe following snapshot creation command line options are supported:\
           \n\tsnapCreate --name X --volume <volume> [--preview]\t\t#Create snapshot X on volume Y.\
           \n\tsnapCreate --name X --volume <volume> --volPattern [--preview]\t#Create snapshot X on volumes with names containing substring Y.\
           \n\tsnapCreate --name X [--preview]\t\t\t\t#Create snapshot X on all volumes.')
    exit()
    
def snapRevert_error_message():
    print('\nThe following snapshot reversion command line options are supported:\
           \n\tsnapRevert --name X --volume <volume> [--preview]\t\t\t#Revert to Snapshot X for volume Y.\
           \n\tsnapRevert --name X --volume <volume> --volPattern --Force [--preview]\t#Revert to snapshot X for volumes with names containing Y.\
           \n\tsnapRevert --name X --Force  [--preview]\t\t\t\t#Revert to snapshot X wherever it is found.')
    exit()

def snapKeepByDays_error_message():
    print('\nThe following snapKeepByDays command line options are supported:\
           \n\tsnapKeepByDays --volume <volume> --count --Force[--preview]\t\t\t\t\t#Keep the newest --count Snapshots, Delete the remaining snapshots Y for volume --volume.\
           \n\tsnapKeepByDays --volume <volume> --count --volPattern --Force[--preview]\t\t\t#Keep the newest --count Snapshots, Delete the remaining snapshot for pattern matched volumes.\
           \n\tsnapKeepByDays --volume <volume> --count --volPattern --snapPattern --name --Force[--preview]\t#Keep the newest --count Snapshots pattern matched based on --name.\
           \n\t\t\t\t\t\t\t\t\t\t\t\t\t#Delete the remaining snapshots also pattern matched based on --name.\
           \n\t\t\t\t\t\t\t\t\t\t\t\t\t#These operations occur against volumes pattern matched based on --volume')
    exit()

def snapKeepByCount_error_message():
    print('\nThe following snapKeepByCount command line options are supported:\
           \n\tsnapKeepByCount --volume <volume> --count --Force[--preview]\t\t\t\t\t#Keep the newest --count Snapshots, Delete the remaining snapshots Y for volume --volume.\
           \n\tsnapKeepByCount --volume <volume> --count --volPattern --Force[--preview]\t\t\t#Keep the newest --count Snapshots, Delete the remaining snapshot for pattern matched volumes.\
           \n\tsnapKeepByCount --volume <volume> --count --volPattern --snapPattern --name --Force[--preview]\t#Keep the newest --count Snapshots pattern matched based on --name.\
           \n\t\t\t\t\t\t\t\t\t\t\t\t\t#Delete the remaining snapshots also pattern matched based on --name.\
           \n\t\t\t\t\t\t\t\t\t\t\t\t\t#These operations occur against volumes pattern matched based on --volume')
    exit()

def snapDelete_error_message():
    print('\nThe following snapshot deletion command line options are supported:\
           \n\tsnapDelete --name X --volume <volume> [--preview]\t\t\t#Delete Snapshot X from volume Y.\
           \n\tsnapDelete --name X --volume <volume> --volPattern --Force [--preview]\t#Delete Snapshot X from volumes with names containing Y.\
           \n\tsnapDelete --name X --Force  [--preview]\t\t\t\t#Delete Snapshot X wherever it is found.')
    exit()


####################
## Oracle Functions
###################

#Oracle Config Capture
def oracle_config_capture(configFile = None, fs_map_hash = None, oracleSid = None, project = None):
    datavols, logvols = extract_oracle_json(configfile = configFile, project = project, oraclesid = oracleSid)
    #Check for SID, datavols and logvols in configfile
    if not datavols or not logvols:
        if not datavols:
           print('datavols not present in configfile %s for sid %s' % (sys.argv[1],sys.argv[2]))
        if not logvols:
           print('dogvols not present in configfile %s for sid %s' % (sys.argv[1],sys.argv[2]))
        exit()
    elif len(datavols) == 0 or len(logvols) == 0:
        if len(datavols) == 0:
            print('datavols key present in configfile %s but no values therein for sid %s' % (sys.argv[1],sys.argv[2]))
        if len(logvols) == 0:
            print('logvols key present in configfile %s but no values therein for sid %s' % (sys.argv[1],sys.argv[2]))
        exit()

    #Volumes were found in the config file, now check to see if the volumes exist within the service
    else:   
        listed_but_not_present = {'datavols':[],'logvols':[]}
        for volume in datavols:
            if volume not in fs_map_hash:
                listed_but_not_present['datavols'].append(volume)
        for volume in logvols:
            if volume not in fs_map_hash:
                listed_but_not_present['logvols'].append(volume)
        if len(listed_but_not_present['datavols']) or len(listed_but_not_present['logvols']):
            print('The following volumes found in the configfile were not found within the volume service:')
            if len(listed_but_not_present['datavols']) > 0:
                print('Datavolumes:')
                for volume in listed_but_not_present['datavols']:
                    print('\t%s' % (volume))
            if len(listed_but_not_present['logvols']) > 0:
                print('Logvolumes:')
                for volume in listed_but_not_present['logvols']:
                    print('\t%s' % (volume))
            exit()
    #If we make it this far, return the volume lists
    return datavols, logvols



#Oracle Backup Function
def oracle_hot_backup(configFile = None, fs_map_hash = None, headers = None, oracleSid = None, preview = None, project = None, region = None, url = None):
    #Capture the volumes from the config file
    datavols, logvols = oracle_config_capture(configFile = configFile, fs_map_hash = fs_map_hash, oracleSid = oracleSid, project = project)
    #If we get this far, place the database in hot backup mode
    if not preview:
        out=orautils.enter_hotbackupmode(oracleSid)
    else:
        print('"alter database begin backup;" against oracle sid %s simulated' % (oracleSid))

    #Create Snapshots of data volumes
    now = date_to_epoch(now = True)
    snapCreate( fs_map_hash = fs_map_hash, headers = headers, name = oracleSid + '-' + str(now) ,preview = preview, region = region, url = url, volume_list = datavols)
    #Take out of backup mode
    if not preview:
        out=orautils.leave_hotbackupmode(oracleSid)
    elif preview:
        print('"alter database end backup;" against oracle sid %s simulated' % (oracleSid))
        print('"alter system archive log current;" against oracle sid %s simulated' % (oracleSid))
    #Create Snapshots of log volumes
    snapCreate( fs_map_hash = fs_map_hash, headers = headers, name = oracleSid + '-' + str(now) ,preview = preview, region = region, url = url, volume_list = logvols)

##Oracle Recover Function
def oracle_recover_database(configFile = None, fs_map_hash = None, headers = None, latest = None, name = None, oracleSid = None, preview = None, project = None, region = None, url = None):
    #Capture the volumes from the config file
    datavols, logvols = oracle_config_capture(configFile = configFile, fs_map_hash = fs_map_hash, oracleSid = oracleSid, project = project)
    #If we get this far, shutdown the database using abort
    if not preview:
        out=orautils.shutdown_abort(oracleSid)
    else:
        print('"shutdown abort;" against oracle sid %s simulated' % (oracleSid))
    #Revert the data volumes
    snapRevert(force = True, fs_map_hash = fs_map_hash, headers = headers, name = name, preview = preview, region = region, url = url, volume_list = datavols)
    #Take out of backup mode
    if not preview:
        out=orautils.recover_database(oracleSid)
    else:
        print('"startup mount;" against oracle sid %s simulated' % (oracleSid))
        print('"recover automatic;" against oracle sid %s simulated' % (oracleSid))
        print('"alter database open;" against oracle sid %s simulated' % (oracleSid))


def extract_oracle_json(configfile = None,project = None, oraclesid = None):
   if os.path.exists(configfile):
      with open(configfile,'r') as fh:
         config = json.load(fh)
         if 'project' not in config.keys(): 
            print('project key Not Present in In Config File: %s' % (configfile))
            exit()
         elif project not in config['project']:
            print('project %s Not Present in In Config File: %s' % (project, configfile))
            exit()
         elif 'oraclesid' not in config['project'][project]:
            print('oraclesid key Not Present in project %s In Config File: %s' % (project, configfile))
            exit()
         elif oraclesid not in config['project'][project]['oraclesid']:
            print('oracleid %s Not Present in within project %s In Config File: %s' % (oraclesid, project, configfile))
            exit()
         else:
            if 'datavols' not in config['project'][project]['oraclesid'][oraclesid].keys():
                datavols = False
            else:
                datavols = config['project'][project]['oraclesid'][oraclesid]['datavols']
            if 'logvols' not in config['project'][project]['oraclesid'][oraclesid].keys():
                logvols = False
            else:
                logvols = config['project'][project]['oraclesid'][oraclesid]['logvols']
            return datavols, logvols
   else:
       print('Oracle Bakup configuration file was not found: %s' % (configfile))
       exit()
        

'''MAIN'''
command_line()
