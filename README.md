# cloudVolumeServiceAWS
Command Line Interface for the NetApp Cloud Volume Service in AWS

There are four steps to getting started:
#### 1) initialize a virtual environment
  $ virtualenv cloudVolumeServiceAWS
#### 2) Activate the virtual envrioment
  $ source cloudVolumeServiceAWS/bin/activate
#### 3) Install the requests python library
  $ pip install requests
#### 4) Initialize the ~/aws_cvs_config file.  
  $ ~/cvs_keys.py
usage: cvs_keys.py [-h] [-p PROJECT] [-u URL] [-s SECRETKEY] [--a APIKEY] [--r REGION]<br/>
cvs_keys.py is used to configure the aws_cvs_config base file<br/><br/>
optional arguments:<br/>
-h, --help            show this help message and exit<br/>
--project PROJECT, -p PROJECT<br/>  Enables use of multiple CV tenants.  If none is provided, default is used<br/>
--url URL, -u URL     Enter the url for the cloud volumes api service<br/>
--secretkey SECRETKEY, -s SECRETKEY         Enter the cloud volumes secret-key<br/>
--apikey APIKEY, -a APIKEY                  Enter the cloud volumes api-key<br/>
--region REGION, -r REGION                 Enter the cloud volumes region<br/><br/>
Examples:<br/>
~/cvs_keys.py --url https://cds-aws-bundles.netapp.com:8080/v1 -s 123456asdfgh1234556 -a fdsfghf -r us-east<br/> 
~/cvs_keys.py --url https://cds-aws-bundles.netapp.com:8080/v1 -s 123456asdfgh1234556 -a fdsfghf -r us-west<br/>
~/cvs_keys.py --url https://cds-aws-bundles.netapp.com:8080/v1 -s 123456asdfgh1234556 -a fdsfghf -r us-east -p chad<br/>
                
