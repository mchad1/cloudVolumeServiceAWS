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
    group.add_argument('--volCreate',action='store_const',const=True,)
    parser.add_argument('--gigabytes','-g',type=str,help='Volume gigabytes in Gigabytes, value accepted between 100 and 100,000. Supports volCreate')
    parser.add_argument('--bandwidth','-b',type=str,help='Volume bandwidth requirements in Megabytes per second. If unknown enter 0 and maximum\
                                                     bandwidth is assigned. Supports volCreate')
    arg = vars(parser.parse_args())

    #Preview sets of the automation to simulate the command and return simulated results, if not entered assume False

    if arg['bandwidth']:
        bandwidth = arg['bandwidth']    
    else:
        bandwidth = None

    if arg['gigabytes']:
        gigabytes = arg['gigabytes']    
    else:
        gigabytes = None


    elif arg['volCreate']:
        volCreate( bandwidth = bandwidth, gigabytes = gigabytes)
        
        ##########################################################
        #                      Volume Commands
        ##########################################################
        

def volCreate(
            bandwidth = None,
            gigabytes = None,
           ):

    if name:
        if gigabytes and bandwidth and cidr and name and region:
            error = False 
            error_value = {}
   
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
                error_value['bw'] = ('Negative value entered: %s, requested values must be => 0.  If value == 0 or value > 4500 then maximum bandwidth will be assigned' % (bandwidth))
            servicelevel, quotainbytes, bandwidthMB = servicelevel_and_quota_lookup(bwmb = bandwidth, gigabytes = gigabytes)
  
            if error == False: 
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
                print('The volCreate command failed, see the following json output for the cause:\n')
                pretty_hash(error_value)
                volCreate_error_message()
        else:
            volCreate_error_message()
    else:   
        print('The volCreate command resulted in an error.\tThe required flag --name was not specified.')
        volCreate_error_message()

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
         


##########################################################
#                     Volume Functions
##########################################################
 

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
                    quota_in_bytes = None,
                    servicelevel = None):
    if servicelevel == 'basic':
        servicelevel_alt = 'standard'
    elif servicelevel == 'standard':
        servicelevel_alt = 'premium'
    elif servicelevel == 'extreme':
        servicelevel_alt = 'extreme'
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


'''MAIN'''
command_line()
