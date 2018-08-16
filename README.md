# cloudVolumeServiceAWS
Command Line Interface for the NetApp Cloud Volume Service in AWS

There are five steps to getting started:
1) initialize a virtual environment<br/>
  $ **virtualenv cloudVolumeServiceAWS**
2) Activate the virtual envrioment<br/>
  $ **source cloudVolumeServiceAWS/bin/activate**
3) Install the requests python library<br/>
  $ **pip install requests**
4) Initialize the aws_cvs_config file<br/>
  $ **cvs_keys.py**
uage: cvs_keys.py [-h] [--project PROJECT] [--url URL]<br/>
                   [--secretkey SECRETKEY] [--apikey APIKEY] [--region REGION]<br/><br/>
**cvs-keys.py is used to configure the aws_cvs_config base file**

Examples:<br/>
~/cvs_keys.py --url https://cds-aws-bundles.netapp.com:8080/v1 -s 123456asdfgh1234556 -a fdsfghf -r us-east<br/> 
~/cvs_keys.py --url https://cds-aws-bundles.netapp.com:8080/v1 -s 123456asdfgh1234556 -a fdsfghf -r us-west<br/>
~/cvs_keys.py --url https://cds-aws-bundles.netapp.com:8080/v1 -s 123456asdfgh1234556 -a fdsfghf -r us-east -p chad<br/>

5) Run the utility **cvs-aws.py** from within the virtual environment<br/>
  $ **cvs-aws.py**<br/>  
  usage: cvs-aws.py [-h]<br/>
                       (--volCreate | --volDelete | --volList | --snapCreate | --snapDelete | --snapList | --snapRevert)<br/>
                       [--project PROJECT] [--Force] [--pattern]<br/>
                       [--volume VOLUME] [--region REGION] [--name NAME]<br/>
                       [--gigabytes GIGABYTES] [--bandwidth BANDWIDTH]<br/>
                       [--cidr CIDR] [--label LABEL] [--count COUNT]<br/>
 **cvs-aws.py is a command line utility for interacting with your tenants NetApp Cloud Volumes Service.**                      


                
