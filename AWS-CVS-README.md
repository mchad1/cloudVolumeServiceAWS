# CVS-AWS.py #
### Snapshots ###
It can list snapshots for one to many volumes, same logic and do so based on pattern matching of volumes names (create a snapshot on one volume, a subset of volumes or all volumes)
It can delete one to many snapshots using the same logic.
It can create one to many snapshots using the same logic
### volumes ###
It can list one to many volumes, same logic
It can delete one to many volumes, same logic
It can snap revert one to many volumes again based on the logic above.
It can create one to many volumes (based on –count).  The logic here is kind of neat, rather than asking for a service level it asks for bandwidth need (0 == unknown and then it sets the need to 3500MB/s which is my tested limit).  Based upon the stated capacity and bandwidth needs it determines the  most cost effective service level and sets it.  Then when its lists the results, it lists the available bandwidth as part of the output.

$ **cvs-aws.py -h**
usage: cloudvolumes.py [-h]<br/>
                       (--volCreate | --volDelete | --volList | --snapCreate | --snapDelete | --snapList | --snapRevert)<br/>
                       [--project PROJECT] [--Force] [--pattern]<br/>
                       [--volume VOLUME] [--region REGION] [--name NAME]<br/>
                       [--gigabytes GIGABYTES] [--bandwidth BANDWIDTH]<br/>
                       [--cidr CIDR] [--label LABEL] [--count COUNT]<br/><br/>
cloudvolumes.py is used to issue api calls on your behalf<br/><br/>
optional arguments:<br/>
  -h, --help            show this help message and exit<br/>
  --volCreate
  --volDelete
  --volList
  --snapCreate
  --snapDelete
  --snapList
  --snapRevert
  --project PROJECT, -p PROJECT
                        Enter the project name to interact with, otherwise the
                        default project is selected
  --Force               If specfied, enables substring's to work *Delete and
                        Revert operations. Supports all *Delete operations as
                        well as snapRevert.
  --pattern, -P         Search for volumes using name as substring. Supports<br/>
                        snapList and volList nativley, snapDelete and<br/>
                        volDelete as well as snapRevert with --Force.<br/>
  --volume VOLUME, -v VOLUME
                        Enter a volume name to search for
  --region REGION, -r REGION
                        Specify the region when performing creation
                        operations, specify only if different than that listed
                        already in the aws_cvs_config.json file. Supports
                        snapCreate and volCreate
  --name NAME, -n NAME  Specify the object name to create. Supports snap* and
                        volCreate. When used with volCreate, body must match
                        [a-zA-Z][a-zA-Z0-9-] and be 16 - 33 character long
  --gigabytes GIGABYTES, -g GIGABYTES
                        Volume gigabytes in Gigabytes, value accepted between
                        1 and 100,000. Supports volCreate
  --bandwidth BANDWIDTH, -b BANDWIDTH
                        Volume bandwidth requirements in Megabytes per second.
                        If unknown enter 0. Supports volCreate
  --cidr CIDR, -c CIDR  Volume bandwidth requirements in Megabytes per second.
                        If unkown enter 0. Supports volCreate
  --label LABEL, -l LABEL<br/>
                        Volume label. Supports volCreate
  --count COUNT, -C COUNT
