![Vector currents](/images/blue-waves-2317606_1280_trimmed_squeezed.png?raw=true)

# C-VIEW Currents
An extension to the [C-VIEW](https://github.com/ucsd-ccbb/C-VIEW) 
(COVID-19 VIral Epidemiology Workflow) pipeline that uses 
[Freyja](https://github.com/andersen-lab/Freyja) to identify variants and 
lineages prevalent in mixed-input samples like wastewater.

# Table of Contents
1. [Overview](#Overview)
2. [Installing the Pipeline](#Installing-the-Pipeline)
3. [Creating a Cluster](#Creating-a-Cluster)
4. [Configuring the Pipeline for Genexus Access](Configuring-the-Pipeline-for-Genexus-Access)
5. [Running the Pipeline](#Running-the-Pipeline)


## Overview

TODO

## Installing the Pipeline

**Note: Usually it will NOT be necessary to install the pipeline from scratch.**  The most
current version of the pipeline is pre-installed on the so-labeled
Amazon Web Services snapshot in region us-west-2 (Oregon),
and this snapshot can be used directly to [create a cluster](#Creating-a-Cluster).

If a fresh installation *is* required, take the following steps:

1. On AWS, launch a new ubuntu 20.04 instance
   1. Note that it MUST be version 20.04, not the latest available ubuntu version (e.g. 22.04) because 20.04 is the latest version supported by AWS ParallelCluster.
   2. Select type t2.medium
   3. Add a 35 GB root drive and a 150 GB EBS drive
   4. Set the security group to allow SSH via TCP on port 22 and all traffic via all protocols on all ports
2. `ssh` onto new instance to set up file system and mount
   1. Run `lsblk` to find the name of the 300 GB EBS drive. For the remainder, of this section, assume `lsblk` shows that the name of the 300 GB volume is `xvdb`. 
   2. Run `sudo mkfs -t xfs /dev/xvdb` to make a filesystem on the new drive 
   3. Run `sudo mkdir /shared` to create a location for the installation 
   4. Run `sudo mount /dev/xvdb /shared` to mount the EBS volume to the new location
   5. Run ``sudo chown `whoami` /shared`` to grant the current user permissions to the new location
3. Install anaconda and python
   1. Run `cd /shared`
   2. Run `wget https://repo.anaconda.com/archive/Anaconda3-2020.11-Linux-x86_64.sh`
   3. Run `bash Anaconda3-2020.11-Linux-x86_64.sh`
   4. Answer `yes` when asked to accept the license agreement
   5. Enter `/shared/workspace/software/anaconda3` when asked for the install location
   6. Answer `yes` when asked whether to have the installer run conda init
   7. Log out of the `ssh` session and then back in to allow the conda install to take effect
4. Install C-VIEW Currents
   1. Run `cd /shared`
   2. Download `install.sh`
   3. Run `bash install.sh`
   4. Answer yes whenever asked for permission to proceed
5. On AWS, make a snapshot of the newly installed EBS volume


## Creating a Cluster

The pipeline is designed to run on a version 3 or later AWS ParallelCluster. 
Begin by ensuring that ParallelCluster is installed on your local machine; if it
is not, take these steps:

1. Set up a `conda` environment and and install ParallelCluster 
   1. Run `conda create --name parallelcluster3 python=3`
   2. Run `conda activate parallelcluster3`
   3. Run `python3 -m pip install --upgrade aws-parallelcluster`
2. In the `parallelcluster3` environment, install Node Version Manager and Node.js, which are (apparently) required by AWS Cloud Development Kit (CDK)
   1. Run `curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.38.0/install.sh | bash`
   2. Run `chmod ug+x ~/.nvm/nvm.sh`
   3. Run `source ~/.nvm/nvm.sh`
   4. Run `nvm install --lts`
   5. Check your install by running `node --version` and `pcluster version`

Next, ensure you have a pem file registered with AWS and that you have run `aws configure`
locally to set up AWS command line access from your local machine.  Then 
prepare a cluster configuration yaml file using the below template:

```
Region: us-west-2
Image:
  Os: ubuntu2004
SharedStorage:
  - MountDir: /shared
    Name: custom
    StorageType: Ebs
    EbsSettings:
      Size: 300
      SnapshotId: <snapshot of current cview release, e.g. snap-09264bf02660b54ad >
HeadNode:
  InstanceType: t2.medium
  Networking:
    SubnetId: subnet-06ff527fa2d5827a3
# subnet-06ff527fa2d5827a3 is parallelcluster:public-subnet
  Ssh:
    KeyName: <name of your pem file without extension, e.g. my_key for a file named my_key.pem >
Scheduling:
  Scheduler: slurm
  SlurmQueues:
    - Name: default-queue
      ComputeSettings:
        LocalStorage:
          RootVolume:
            Size: 500
      Networking:
        SubnetIds:
          - subnet-06ff527fa2d5827a3
# subnet-06ff527fa2d5827a3 is parallelcluster:public-subnet
      ComputeResources:
        - Name: default-resource
          MaxCount: 15
          InstanceType: r5d.24xlarge
```

To create a new cluster from the command line, run

```
pcluster create-cluster \
    --cluster-name <your-cluster-name> \
    --cluster-configuration <your-config-file-name>.yaml
```

(If you experience an error referencing Node.js, you may need to once again
run `source ~/.nvm/nvm.sh` to ensure it is accessible from your shell.)  The 
cluster creation progress can be monitored from the `CloudFormation`->`Stacks` section of the AWS Console.

Once the cluster is successfully created, log in to the head node.  To avoid 
having to use its public IPv4 DNS, one can run

`pcluster ssh --cluster-name <your_cluster_name> -i /path/to/keyfile.pem`

which fills in the cluster IP address and username automatically.

From the head node, run `aws configure` to set up the head node with credentials for accessing the 
necessary AWS S3 resources.

## Configuring the Pipeline for Genexus Access

Much of the data run through C-VIEW Currents comes from the Genexus instrument. 
This machine is accessed via an RSA key-pair, with the public key being placed on
the instrument and the private key placed on the C-VIEW Currents head node.

To configure automated Genexus access:

   1. Contact the personnel in charge of the Genexus instrument
      1. Ask them for the username and IP address of the Genexus instrument
      2. Ask them for the URL, login, and password for the Genexus instrument's web portal
      3. Provide them with your RSA public key for placement on the instrument
   2. SSH onto the C-VIEW Currents head node and
      1. Copy your RSA private key into the `~/genexus/id_rsa` folder
      2. Find the two `transfer_genexus_bams_*` scripts in `/shared/workflow/software/cview_currents/scripts`
      3. For each script, set the `GENEXUS_USERNAME` and `GENEXUS_IP` variables to the values received in configuration step 1.1
      
## Running the Pipeline

The pipeline is run from the head node of the cluster, via the following steps:

1. Load the data onto S3 (for Genexus data only)
   1. Log onto the Genexus instrument's web portal
   2. Capture the name of the latest run (e.g., `221013_WW`) and the sample names included in it (e.g., `10.11.22.ENCOCT11.R2`, `10.13.22.PLOCT09.R2`, etc)
   3. On the cluster head node, create a one-column, no-header text file containing the sample names for this run
      1. For example, run `nano /shared/runfiles/221013_WW_samples.txt` and paste in the sample names

```
# Example:
nano /shared/runfiles/221013_WW_samples.txt
# then paste the following into the text editor and save:
10.11.22.ENCOCT06.R2
10.11.22.ENCOCT11.R2
10.13.22.PLOCT09.R2
10.13.22.PLOCT10.R2
10.13.22.PLOCT11.R2
10.13.22.PLOCT12.R2
10.13.22.SBOCT09.R2
10.13.22.SBOCT10.R2
```

   4. Transfer the relevant `.bam` and their associated `.bai` files from the Genexus to S3 by running the `transfer_genexus_bams_to_s3.sh` script with the following positional arguments:
      1. The local directory in which to temporarily store Genexus files (e.g., `/shared/temp`)
      2. The S3 directory in which a folder holding these bams should be created (e.g., `s3://ucsd-all`)
      3. The run name (e.g., `221013_WW`)
      4. The file of sample names for this run (e.g., `/shared/runfiles/221013_WW_samples.txt`)

```
# Example:

cd /shared/workspace/software/cview_currents/scripts
# Command format:
# bash transfer_genexus_bams_to_s3.sh <local_dir> <s3_parent_directory> <run_name> <samples_file>
bash transfer_genexus_bams_to_s3.sh /shared/temp s3://ucsd-all 221013_WW /shared/runfiles/221013_WW_samples.txt
```

2. Run Freyja
   1. Prepare a one-column, no-header text file of S3 urls to the bam files to be processed
      1. NOTE: This file *is created automatically* if the bams were transferred to S3 with using the `transfer_genexus_bams_to_s3.sh` script described above; in this case, it is located in `<local_dir>/<run_name>_s3_urls.txt`
   
```
# Example: contents of /shared/temp/221013_WW_s3_urls.txt:

s3://ucsd-all/221010_WW/221010_WW_bam/10.4.22.ENCOCT03.R2__NA__NA__221010_WW__00X.trimmed.sorted.unfiltered.bam
s3://ucsd-all/221010_WW/221010_WW_bam/10.4.22.ENCSEP29.R2__NA__NA__221010_WW__00X.trimmed.sorted.unfiltered.bam
s3://ucsd-all/221010_WW/221010_WW_bam/10.7.22.PLOCT02.R2__NA__NA__221010_WW__00X.trimmed.sorted.unfiltered.bam
s3://ucsd-all/221010_WW/221010_WW_bam/10.7.22.PLOCT03.R2__NA__NA__221010_WW__00X.trimmed.sorted.unfiltered.bam
s3://ucsd-all/221010_WW/221010_WW_bam/10.7.22.PLOCT04.R2__NA__NA__221010_WW__00X.trimmed.sorted.unfiltered.bam
s3://ucsd-all/221010_WW/221010_WW_bam/10.7.22.PLOCT05.R2__NA__NA__221010_WW__00X.trimmed.sorted.unfiltered.bam
s3://ucsd-all/221010_WW/221010_WW_bam/10.7.22.SBOCT04.R2__NA__NA__221010_WW__00X.trimmed.sorted.unfiltered.bam
s3://ucsd-all/221010_WW/221010_WW_bam/10.7.22.SBOCT06.R2__NA__NA__221010_WW__00X.trimmed.sorted.unfiltered.bam
```

   2. Kick off the pipeline by running the `run_distributed_freyja.sh` script with the following positional arguments:
      1. The file of S3 URLs to the relevant bam files (e.g., `/shared/temp/221013_WW_s3_urls.txt`)
      2. The run name (e.g., `221013_WW`)
      3. The S3 directory in which a folder for this run should be created (e.g., `s3://ucsd-all/freyja`)

```
# Example:

cd /shared/workspace/software/cview_currents/scripts
# Command format:
# bash run_distributed_freyja.sh <bam_urls_file> <run_name> <s3_parent_directory>
bash run_distributed_freyja.sh /shared/temp/221013_WW_s3_urls.txt 221013_WW s3://ucsd-all/freyja
# If desired, check job status by running:
squeue
```

3. Generate reports
   1. TODO

