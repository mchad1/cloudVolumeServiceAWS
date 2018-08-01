#!/usr/bin/python
from os.path import expanduser
import argparse
import json
import os
import sys

def command_line():
    parser = argparse.ArgumentParser(prog='cvs_keys.py',description='%(prog)s is used to configure the aws_cvs_config base file')
    parser.add_argument('--url','-u',type=str,help='Enter an alternative url for the cloud volumes api service only if neccessary')
    parser.add_argument('--secretkey','-s', type=str,help='Enter the cloud volumes secret-key')
    parser.add_argument('--apikey','-a', type=str,help='Enter the cloud volumes api-key')
    parser.add_argument('--region','-r', type=str,help='Enter the cloud volumes region')
    arg = vars(parser.parse_args())
    if len(set(arg.values())) != 4:
        parser.print_help()
        exit()
    home = expanduser("~")
    if arg['url'] and arg['secretkey'] and arg['apikey']:
        if 'http' in arg['url']:
            with open(home + '/aws_cvs_config','w') as config_file:
                json.dump(arg,config_file)
            print('Config File Created: %s/aws_cvs_config\n' % (home))
        else:
            print('Improper url specified, Bypassed creation of %s/aws_cvs_config\n' % (home))
     

command_line()
