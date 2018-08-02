#!/usr/bin/python
from os.path import expanduser
import argparse
import json
import os
import sys

def command_line():
    parser = argparse.ArgumentParser(prog='cvs_keys.py',description='%(prog)s is used to configure the aws_cvs_config base file')
    parser.add_argument('--project','-p',type=str,help='To enable use of multiple Cloud Volume environments, enter an arbitrary project name.  If none if provided, default is used')
    parser.add_argument('--url','-u',type=str,help='Enter the url for the cloud volumes api service')
    parser.add_argument('--secretkey','-s', type=str,help='Enter the cloud volumes secret-key')
    parser.add_argument('--apikey','-a', type=str,help='Enter the cloud volumes api-key')
    parser.add_argument('--region','-r', type=str,help='Enter the cloud volumes region')
    arg = vars(parser.parse_args())
  
    if arg['url'] and arg['secretkey'] and arg['apikey'] and arg['region']:  

        '''
        define project for the purpose of multi environment use cases
        '''
        if arg['project']:
            project = arg['project']
        else:
            project = 'default'
               
        '''
        extract the contents of the current file if present to only overwrite the section in play
        '''
        home = expanduser("~")
        if os.path.exists(home + '/aws_cvs_config'):
            with open(home + '/aws_cvs_config','r') as config_file:
                config = json.load(config_file)
            if project not in config.keys():
                config[project] = {}
        else:
            config = {}
            config[project] = {}
        '''
        build the config 
        '''
        if 'http' in arg['url']:
            for key in arg.keys():
                if key != 'project':
                    config[project][key] = arg[key]

            with open(home + '/aws_cvs_config','w') as config_file:
                json.dump(config,config_file)
            print('\nConfig File Created: %s/aws_cvs_config\n' % (home))
        else:
            print('\nImproper url specified, Bypassed creation of %s/aws_cvs_config\n' % (home))
    else:
        parser.print_help()
        exit()

command_line()
