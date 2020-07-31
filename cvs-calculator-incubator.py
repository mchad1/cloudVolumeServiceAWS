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
    parser.add_argument('--gigabytes','-g',type=str,help='Volume gigabytes in Gigabytes, value accepted between 100 and 102,400. Supports volCreate')
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


    if  arg['volCreate']:
        volCreate( bandwidth = bandwidth, gigabytes = gigabytes)
        
        ##########################################################
        #                      Volume Commands
        ##########################################################
        

def volCreate(
            bandwidth = None,
            gigabytes = None,
           ):

    if gigabytes and bandwidth:
        error = False 
        error_value = {}
  
        local_error = is_number(gigabytes)
        if local_error == True:
            error = True
            error_value['gigabytes_integer'] = 'Capacity was not a numeric value'
        elif int(gigabytes) < 100 or int(gigabytes) > 102400:
            error = True
            error_value['size'] = 'Capacity was either smaller than 100GiB or greater than 102,400GiB'
        local_error = is_number(bandwidth)
        if local_error == True:
            error = True
            error_value['bw_integer'] = 'Bandwidth was not a numeric value'
        elif int(bandwidth) < 0:
            error = True
            error_value['bw'] = ('Negative value entered: %s, requested values must be => 0.  If value == 0 or value > 4500 then maximum bandwidth will be assigned' % (bandwidth))
        servicelevel, quotainbytes, bandwidthMiB, cost = servicelevel_and_quota_lookup(bwmb = bandwidth, gigabytes = gigabytes)
 
        if error == False: 
            volume_creation(bandwidth = bandwidthMiB,
                            cost = cost,
                            quota_in_bytes = quotainbytes,
                            servicelevel = servicelevel
                            )
        else:
            print('The volCreate command failed, see the following json output for the cause:\n')
            pretty_hash(error_value)
            volCreate_error_message()
    else:
        print('Error Bandwidth: %s, GiB: %s'%(bandwidth,gigabytes))


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
Issue call to create volume
'''
def volume_creation(bandwidth = None,
                    cost = None,
                    quota_in_bytes = None,
                    servicelevel = None):
    print('\n\tserviceLevel:%s ($%s)\
          \n\tallocatedCapacityGiB:%s\
          \n\tavailableBandwidthMiB:%s'
          % (servicelevel,cost,int(quota_in_bytes) / 2**30,bandwidth))

'''
Determine the best gigabytes and service level based upon input
input == bandwidth in MiB, gigabytes in GiB
output == service level and gigabytes in GiB
'''

def servicelevel_and_quota_lookup(bwmb = None, gigabytes = None):
    servicelevel_and_quota_hash = quota_and_servicelevel_parser()

    bwmb = float(bwmb)
    gigabytes = float(gigabytes)
    standard_cost_per_gb = float(servicelevel_and_quota_hash['prices']['standard'])
    premium_cost_per_gb = float(servicelevel_and_quota_hash['prices']['premium'])
    ultra_cost_per_gb = float(servicelevel_and_quota_hash['prices']['ultra'])

    standard_bw_per_gb = float(servicelevel_and_quota_hash['bandwidth']['standard'])
    premium_bw_per_gb = float(servicelevel_and_quota_hash['bandwidth']['premium'])
    ultra_bw_per_gb = float(servicelevel_and_quota_hash['bandwidth']['ultra'])

    '''
    if bwmb == 0, then the user didn't know the bandwidth, so set to maximum which we've seen is 3800MiB/s. 
    '''
    if bwmb == 0 or bwmb > 4500:
        bwmb = 4500 
    '''
    convert mb to kb
    '''
    bwkb = bwmb * 1024.0
    
    '''
    gigabytes needed based upon bandwidth needs
    '''
    standard_gigabytes_by_bw = bwkb / standard_bw_per_gb
    if standard_gigabytes_by_bw < gigabytes:
        standard_cost = gigabytes * standard_cost_per_gb
    else:
        standard_cost = standard_gigabytes_by_bw * standard_cost_per_gb

    premium_gigabytes_by_bw = bwkb / premium_bw_per_gb
    if premium_gigabytes_by_bw  < gigabytes:
        premium_cost = gigabytes * premium_cost_per_gb
    else:
        premium_cost = premium_gigabytes_by_bw * premium_cost_per_gb

    ultra_gigabytes_by_bw = bwkb / ultra_bw_per_gb
    if ultra_gigabytes_by_bw < gigabytes:
        ultra_cost = gigabytes * ultra_cost_per_gb
    else:
        ultra_cost = ultra_gigabytes_by_bw * ultra_cost_per_gb

    '''
    calculate right service level and gigabytes based upon cost
    '''
    cost_hash = {'standard':standard_cost,'premium':premium_cost,'ultra':ultra_cost}
    capacity_hash = {'standard':standard_gigabytes_by_bw,'premium':premium_gigabytes_by_bw,'ultra':ultra_gigabytes_by_bw}
    bw_hash = {'standard':standard_bw_per_gb,'premium':premium_bw_per_gb,'ultra':ultra_bw_per_gb}
    lowest_price = min(cost_hash.values())
    print('lowest_price:%s,Cheapest_Service_level:%s'%(cost_hash,lowest_price))
    for key in cost_hash.keys():
        if cost_hash[key] == lowest_price:
            servicelevel = key
            if capacity_hash[key] < gigabytes:
                gigabytes = int(math.ceil(gigabytes))
                bandwidthKiB = int(math.ceil(gigabytes)) * bw_hash[servicelevel] 
            else:
                gigabytes =  int(math.ceil(capacity_hash[key]))
                bandwidthKiB =  int(math.ceil(capacity_hash[key])) * bw_hash[servicelevel]
   
            '''
            convert from Bytes to GiB 
            '''
            gigabytes *= 2**30
            bandwidthMiB = int(bandwidthKiB / 1024)
            break

    return servicelevel, gigabytes, bandwidthMiB, lowest_price

'''
Calculate the bandwidth based upon passed in service level and quota
'''
def bandwidth_calculator(servicelevel = None, quotaInBytes = None):
    servicelevel_and_quota_hash = quota_and_servicelevel_parser()
    '''
    gigabytes converted from Bytes to KiB
    '''
    #quotaInBytes *= 2**30
    if servicelevel in servicelevel_and_quota_hash['bandwidth'].keys():
        capacityGiB = quotaInBytes / 2**30
        bandwidthMiB = (capacityGiB * servicelevel_and_quota_hash['bandwidth'][servicelevel]) / 1024
    else:
        bandwidthMiB = None
        capacityGiB = None
    return bandwidthMiB, capacityGiB

def volCreate_error_message():
    print('\nThe following volCreate flags are required:\
           \n\t--gigabytes | -g [0 < X <= 102,400]\t#Allocated volume capacity in Gigabyte\
           \n\t--bandwidth | -b [0 <= X <= 4500]\t#Requested maximum volume bandwidth in Megabytes')
    exit()


'''MAIN'''
command_line()
