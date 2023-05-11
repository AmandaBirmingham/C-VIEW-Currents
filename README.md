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
4. [Configuring the Pipeline for Genexus Access](#Configuring-the-Pipeline-for-Genexus-Access)
5. [Running the SEARCH Pipeline](#Running-the-SEARCH-Pipeline)
6. [Running the Campus Pipeline](#Running-the-Campus-Pipeline)


## Overview

C-VIEW Currents runs freyja on specified input bam files and collates the results
into reports formatted for use by either the [SEARCH dashboard](https://searchcovid.info/dashboards/wastewater-surveillance/)
or the UCSD campus dashboard.  For the SEARCH pipeline, various results are
committed to Github repositories powering the SEARCH dashboard, while for the 
campus pipeline, the output report file is uploaded to the S3 bucket monitored 
by the campus dashboard.

In both cases, full intermediate and results files are stored on S3 with the 
following folder-/file-naming structure:

* <s3_output_dir> (e.g., `s3://ucsd-rtl-test/freyja/`)
    * <run_name> (e.g., `221020_WW`)
      * <run_name>_results (e.g., `221020_WW_results`)
        * <analysis_timestamp> (e.g., `2022-10-26_23-03-12`): analysis input files
          * <run_name>_summary (e.g., `221020_WW_summary`)
            * <run_name>_<analysis_timestamp>_freyja_aggregated.tsv (e.g. `221020_WW_2022-10-26_23-03-12_freyja_aggregated.tsv`): `aggregate` results for all samples in run
            * <run_name>_freyja_aggregated.error.log (e.g. `221020_WW_freyja_aggregated.error.log`): log of errors from `aggregate` run; zero bytes if it succeeded
            * [Optional] <run_name>_<analysis_timestamp>_freyja_aggregated.tsv (e.g., `221020_WW_2022-10-26_23-03-12_freyja_rel_growth_rates.csv`): `relgrowthrate` results for all samples in run, if called
            * [Optional] <run_name>_freyja_relgrowthrate.error.log (e.g., `221020_WW_freyja_relgrowthrate.error.log`): log of errors from `relgrowthrate` run, if called; zero bytes if it was called and succeeded
          * <run_name>_samples (e.g., `221020_WW_samples`)
            * <a_sample_name> (e.g., `10.20.22.SB19.R1__NA__NA__221020_WW__00X`): `demix` intermediates and results for a sample
    * reports
      * <report_timestamp>_ <run_name>_<report_type> (e.g., `2022-10-26_23-03-12_221020_WW_search`)
        * <report_timestamp>_ <run_name>_<report_type>_reports.error.log (e.g., `2022-10-26_23-03-12_221020_WW_search_reports.error.log`): log of errors from report generation; zero bytes if it succeeded
        * inputs: inputs to report generation, including original versions of repo files
        * outputs: outputs of report generation, including modified versions of repo files

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

Before beginning, note that setting up a new cluster requires the following information:
* An AWS user with S3 permissions, with known access key and secret access key
* A Github account with known user name and email,
  * Having contributor access to 
    * https://github.com/AmandaBirmingham/SARS-CoV-2_WasteWater_San-Diego
    * https://github.com/joshuailevy/SD-Freyja-Outputs
  * Attached to an ssh key, with known public and private keys
  
To create a new cluster:

1. Ensure that version 3.2 or later AWS ParallelCluster is installed on your local machine; if it
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
2. Ensure you have, locally, a pem file registered with AWS
3. Ensure that you have run `aws configure` locally to set up AWS command line access from your local machine
4. Prepare a cluster configuration yaml file using the below template:

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

5. Create a new cluster from the command line by running `pcluster create-cluster` as shown below 
   1. If you experience an error referencing Node.js, you may need to once again
   run `source ~/.nvm/nvm.sh` to ensure it is accessible from your shell. 
   2. The cluster creation progress can be monitored from the `CloudFormation`->`Stacks` section of the AWS Console.

```
pcluster create-cluster \
    --cluster-name <your-cluster-name> \
    --cluster-configuration <your-config-file-name>.yaml
```

6. Once the cluster is successfully created, log in to the head node. 
   1. To avoid having to use its public IPv4 DNS, one can run `pcluster ssh` as shown below, which fills in the cluster IP address and username automatically.

```pcluster ssh --cluster-name <your_cluster_name> -i /path/to/keyfile.pem```

7. On the head node of the cluster, perform cluster-specific set-up
   1. Configure AWS command-line access
      1. Find the chosen AWS access key and secret access key
      2. Run `aws configure` to set up the head node with these credentials so it can access the 
      necessary AWS S3 resources
   2. Configure `git` check-in information
      1. Run `git config --global --edit` to edit the config doc; then
      2. Set the user name and email for the chosen github account, uncomment those lines, and resave
   3. Configure Github ssh access
      1. Get the RSA key-pair (both public and private) for github user's ssh key
      2. Copy the key-pair into `/home/ubuntu/.ssh/<keyname>`
      3. Ensure the private key has limited permissions by running `chmod 600 /home/ubuntu/.ssh/<keyname>` 
      4. Modify the `.bashrc` file to add the public key to the ssh-agent on login
         1. Run `nano ~/.bashrc` to edit the `.bashrc` file
         2. At the bottom of the file, paste in the following three lines:
            1. `# C-VIEW Currents addition: add CviewMachineAcct ssh to ssh agent`
            2. `eval "$(ssh-agent)"`
            3. `ssh-add /home/ubuntu/.ssh/id_ed25519_CviewMachineAcct`
         3. Save the changes and log out of the cluster
         4. Log back so the changes take effect
      5. Validate ssh access to github is working
         1. Run `ssh -T git@github.com`
         2. Confirm the addition of github.com to the list of known hosts
         3. Access is validated if you receive a message stating `You've successfully authenticated, but GitHub does not provide shell access`
   4. Configure `cli` access for `gh`
      1. Run `source /shared/workspace/software/anaconda3/bin/activate cview_currents` to activate the cview_currents environment
      2. Run `gh auth login`
      3. Choose `GitHub.com` as the account to log into
      4. Choose `SSH` as the protocol
      5. Choose `/home/ubuntu/.ssh/<keyname>` as the ssh key
      6. Title the key `<keyname>`
      7. Open a browser and *ensure that you are logged in with your chosen github account!*
      8. As directed by the `gh` auth process, open the url `https://github.com/login/device`
      9. Paste in the one-time code provided by the process and confirm access
         1. If you receive an "[HTTP 422 error key is already in use](https://github.com/cli/cli/discussions/6271)" error message, this is ok, as described in the link
   5. Clone the SEARCH repos (note that this must come AFTER configuring Github ssh access)
      1. Run `cd /shared/workspace/software`
      2. Run `git clone git@github.com:joshuailevy/SD-Freyja-Outputs.git` to clone the (private) repo for the raw results
      3. Run `git clone git@github.com:AmandaBirmingham/SARS-CoV-2_WasteWater_San-Diego.git` to clone the (public) fork of the Andersen lab repo for dashboard inputs
      4. Run `cd SARS-CoV-2_WasteWater_San-Diego`
      5. Run `git remote add upstream https://github.com/andersen-lab/SARS-CoV-2_WasteWater_San-Diego.git` to add the Andersen lab repo as an upstream to the fork repo

## Configuring the Pipeline for Genexus Access

Much of the data run through C-VIEW Currents comes from the Genexus instrument. 
This machine is accessed via an RSA key-pair with the public key being placed on
the instrument and the private key placed on the C-VIEW Currents head node. 
*Note* that this key-pair is *distinct from* the Github access 
keypair used during new cluster set-up.

To configure automated Genexus access:

   1. If you have not been provided with a Genexus access key-pair, create your own RSA key-pair
   2. Contact the personnel in charge of the Genexus instrument
      1. Ask them for the username and IP address of the Genexus instrument
      2. Ask them for the URL, login, and password for the Genexus instrument's web portal
      3. If you have not been provided with a Genexus access key-pair, provide them with your RSA public key (created in step 1) for placement on the instrument
   3. SSH onto the C-VIEW Currents cluster head node and
      1. Copy the RSA key-pair into a known location (such as a folder named `~/genexus/`)
      2. Ensure the private key has limited permissions by running, e.g., `chmod 600 ~/genexus/<keyname>` 
      3. Find the two `transfer_genexus_bams_*` scripts in `/shared/workflow/software/cview_currents/scripts`
      4. For each script, set the `GENEXUS_USERNAME` and `GENEXUS_IP` variables to the values received in configuration step 1.1
      5. Set the `GENEXUS_RSA_FP` variable to the path to the RSA private key
         1. The default value is `~/genexus/id_rsa`
      
## Running the SEARCH Pipeline

Before beginning, ensure that the actions in the above 
[Configuring the Pipeline for Genexus Access](#Configuring-the-Pipeline-for-Genexus-Access) 
section have been completed.  The pipeline is run from the head node of the 
cluster, via the following steps:

1. Load the data onto S3
   1. Log onto the Genexus instrument's web portal
   2. Capture the name of the latest run (e.g., `221013_WW`) and the sample names included in it (e.g., `10.11.22.ENCOCT11.R2`, `10.13.22.PLOCT09.R2`, etc)
   3. On the cluster head node, construct a two-column, comma-delimited, no-header text file containing the sample names for this run followed by their collection date
      1. For example, run `nano /shared/runfiles/221013_WW_samples.txt` and paste in the sample names and dates

```
# Example:

nano /shared/runfiles/221013_WW_samples.txt
# then paste the following into the text editor and save:

10.11.22.ENCOCT06.R2,10/6/22
10.11.22.ENCOCT11.R2,10/11/22
10.13.22.PLOCT09.R2,10/9/22
10.13.22.PLOCT10.R2,10/10/22
10.13.22.PLOCT11.R2,10/11/22
10.13.22.PLOCT12.R2,10/12/22
10.13.22.SBOCT09.R2,10/9/22
10.13.22.SBOCT10.R2,10/10/22
```

2. Transfer the relevant `.bam` and their associated `.bai` files from the Genexus to S3
   1. Run the `transfer_genexus_bams_to_s3.sh` script with the following positional arguments:
      1. The local directory in which to temporarily store Genexus files (e.g., `/shared/temp`)
      2. The S3 directory in which a folder holding these bams should be created (e.g., `s3://ucsd-rtl-test`)
      3. The run name (e.g., `221013_WW`)
      4. The file of sample names for this run (e.g., `/shared/runfiles/221013_WW_samples.txt`)
   2. This step also automatically generates a freyja-format metadata csv and uploads it to the run's S3 directory

```
# Example:

cd /shared/workspace/software/cview_currents/scripts
# Command format:
# bash transfer_genexus_bams_to_s3.sh <local_dir> <s3_parent_directory> <run_name> <samples_file>
bash transfer_genexus_bams_to_s3.sh /shared/temp s3://ucsd-rtl-test 221013_WW /shared/runfiles/221013_WW_samples.txt
```

3. Update Freyja to get the latest barcodes and lineages
   1. Run the `update_freyja.sh` script; no arguments are needed
   2. Run `squeue` to check its progress; do not continue until the queue is empty

```
# Example:

cd /shared/workspace/software/cview_currents/scripts
bash update_freyja.sh
```

4. Run Freyja
   1. Prepare a one-column, no-header text file of S3 urls to the bam files to be processed 
      1. The file must also include a line specifying the S3 url of the freyja-format metadata csv
      2. NOTE: This file *is created automatically* if the bams were transferred to S3 with using the `transfer_genexus_bams_to_s3.sh` script described above; in this case, it is located in `<local_dir>/<run_name>_s3_urls.txt`
      
```
# Example: contents of /shared/temp/221013_WW_s3_urls.txt:

s3://ucsd-rtl-test/221010_WW/221010_WW_bam/10.4.22.ENCOCT03.R2__NA__NA__221010_WW__00X.trimmed.sorted.unfiltered.bam
s3://ucsd-rtl-test/221010_WW/221010_WW_bam/10.4.22.ENCSEP29.R2__NA__NA__221010_WW__00X.trimmed.sorted.unfiltered.bam
s3://ucsd-rtl-test/221010_WW/221010_WW_bam/10.7.22.PLOCT02.R2__NA__NA__221010_WW__00X.trimmed.sorted.unfiltered.bam
s3://ucsd-rtl-test/221010_WW/221010_WW_bam/10.7.22.PLOCT03.R2__NA__NA__221010_WW__00X.trimmed.sorted.unfiltered.bam
s3://ucsd-rtl-test/221010_WW/221010_WW_bam/10.7.22.PLOCT04.R2__NA__NA__221010_WW__00X.trimmed.sorted.unfiltered.bam
s3://ucsd-rtl-test/221010_WW/221010_WW_bam/10.7.22.PLOCT05.R2__NA__NA__221010_WW__00X.trimmed.sorted.unfiltered.bam
s3://ucsd-rtl-test/221010_WW/221010_WW_bam/10.7.22.SBOCT04.R2__NA__NA__221010_WW__00X.trimmed.sorted.unfiltered.bam
s3://ucsd-rtl-test/221010_WW/221010_WW_bam/10.7.22.SBOCT06.R2__NA__NA__221010_WW__00X.trimmed.sorted.unfiltered.bam
```

   3. Kick off the pipeline by running the `run_distributed_freyja.sh` script with the following positional arguments:
      1. The file of S3 URLs to the relevant bam files (e.g., `/shared/temp/221013_WW_s3_urls.txt`)
      2. The run name (e.g., `221013_WW`)
      3. The S3 directory in which a folder for this run should be created (e.g., `s3://ucsd-rtl-test/freyja` and note this path **must not** have a slash on the end of it)
      4. The report type to generate (either `search` or `campus`)

```
# Example:

cd /shared/workspace/software/cview_currents/scripts
# Command format:
# bash run_distributed_freyja.sh <bam_urls_file> <run_name> <s3_parent_directory>
bash run_distributed_freyja.sh /shared/temp/221013_WW_s3_urls.txt 221013_WW s3://ucsd-rtl-test/freyja search
```
   4. Notice the guidance for using completed results
      1. The pipeline prints out customized instructions for next steps. Be sure to locate these instructions, which begin with the line `Check on job progress by running:`

```
# Example customized instructions from pipeline:

Check on job progress by running:
  squeue
When the queue is empty, review (if desired) the customized repo upload script:
  more /tmp/cview-currents-JdsVoaNirv/2022-10-31_22-31-15_221027_WW_search_update_repos.sh
Run the customized repo upload script:
  bash /tmp/cview-currents-JdsVoaNirv/2022-10-31_22-31-15_221027_WW_search_update_repos.sh
When finished, delete the temporary directory:
   rm -rf /tmp/cview-currents-JdsVoaNirv
  
REMINDER: Did you remember to run
  bash /shared/workspace/software/cview_currents/scripts/update_freyja.sh
to update Freyja before this?  If not, cancel these jobs with
  scancel -u $USER
and update freyja before continuing!
```      

5. Check the pipeline status
   1. Run `squeue` from time to time until the queue shows empty
6. Commit result to Github
   1. Follow the customized instructions printed out by `run_distributed_freyja.sh`
      1. If desired, view the customized Github repo upload script
      2. Run the customized Github upload script
      3. Remove the temporary directory holding the customized script

```
# Example:

more /tmp/cview-currents-JdsVoaNirv/2022-10-31_22-31-15_221027_WW_search_update_repos.sh
bash /tmp/cview-currents-JdsVoaNirv/2022-10-31_22-31-15_221027_WW_search_update_repos.sh
rm -rf /tmp/cview-currents-JdsVoaNirv
```


## Running the Campus Pipeline

The pipeline is run from the head node of the cluster, via the following steps:

1. Generate a file of relevant bam S3 urls
   2. Capture the S3 url of the C-VIEW `*_summary-report_*.csv` to search for inputs
      1. If you want to process all campus samples ever, use the summary report from a cumulative run
      2. If you want to process only campus samples from a particular run, use the summary report from that run
   3. Run `get_cview_bam_urls` with the following positional arguments:
      1. The C-VIEW report S3 URL captured above (e.g., `s3://ucsd-rtl-test/phylogeny/2022-08-10_01-07-42-all/2022-08-10_01-07-42-all_summary-report_all.csv`)
      2. The local directory in which the output file should be placed (e.g., `/shared/temp`)
      3. If *and only if* you want to extract samples for a source *OTHER* than campus, you may pass an optional third argument containing that source (e.g., `SFO_WW`)

```
# Example:

conda activate cview_currents
# if the above gives the error `conda: command not found`, run
source /shared/workspace/software/anaconda3/bin/activate 
# then rerun the conda activate command

# Command format:
# get_cview_bam_urls  <cview_report_s3_url> <local_dir>
get_cview_bam_urls s3://ucsd-rtl-test/phylogeny/2022-08-10_01-07-42-all/2022-08-10_01-07-42-all_summary-report_all.csv /shared/temp
```

2. Locate the output file, which will be named with the prefix of the `*_summary-report_all.csv` input file and with the suffix `_rtl_wastewater_highcov_s3_urls.txt` 
   1. Example:
      1. Input: C-VIEW report `2022-08-10_01-07-42-all_summary-report_all.csv`
      2. Output: bam S3 url file `2022-08-10_01-07-42-all_rtl_wastewater_highcov_s3_urls.txt`
   2. Note that this file contains one bam S3 url per line, plus one additional metadata line holding the S3 url of the C-VIEW report
      1. The metadata line is prefixed with `# metadata:`

```
# Example: contents of /shared/temp/2022-08-10_01-07-42-all_rtl_wastewater_highcov_s3_urls.txt:

s3://ucsd-rtl-test/220527_A01535_0137_BHY5VWDSX3/220527_A01535_0137_BHY5VWDSX3_results/2022-06-08_23-12-15_pe/220527_A01535_0137_BHY5VWDSX3_samples/SEARCH-91768__E0003116__K17__220527_A01535_0137_BHY5VWDSX3__002/SEARCH-91768__E0003116__K17__220527_A01535_0137_BHY5VWDSX3__002.trimmed.sorted.bam
s3://ucsd-rtl-test/220527_A01535_0137_BHY5VWDSX3/220527_A01535_0137_BHY5VWDSX3_results/2022-06-08_23-12-15_pe/220527_A01535_0137_BHY5VWDSX3_samples/SEARCH-91770__E0003116__M17__220527_A01535_0137_BHY5VWDSX3__002/SEARCH-91770__E0003116__M17__220527_A01535_0137_BHY5VWDSX3__002.trimmed.sorted.bam
s3://ucsd-rtl-test/220527_A01535_0137_BHY5VWDSX3/220527_A01535_0137_BHY5VWDSX3_results/2022-06-08_23-12-15_pe/220527_A01535_0137_BHY5VWDSX3_samples/SEARCH-91776__E0003116__C18__220527_A01535_0137_BHY5VWDSX3__002/SEARCH-91776__E0003116__C18__220527_A01535_0137_BHY5VWDSX3__002.trimmed.sorted.bam
# metadata:s3://ucsd-rtl-test/phylogeny/2022-08-10_01-07-42-all/2022-08-10_01-07-42-all_summary-report_all.csv
```      


3. Update Freyja to get the latest barcodes and lineages
   1. Run the `update_freyja.sh` script; no arguments are needed
   2. Run `squeue` to check its progress; do not continue until the queue is empty
   
```
# Example:

cd /shared/workspace/software/cview_currents/scripts
bash update_freyja.sh
```

4. Run Freyja and generate a report
   1. Run the `run_distributed_freyja.sh` script with the following positional arguments:
      1. The file of S3 URLs to the relevant bam files (e.g., `/shared/temp/2022-08-10_01-07-42-all_rtl_wastewater_highcov_s3_urls.txt`)
      2. A "run name" describing the dataset being processed (e.g., `2022-08-10_01-07-42-all_rtl_wastewater_highcov`)
      3. The S3 directory in which a folder for this run should be created (e.g., `s3://ucsd-rtl-test/freyja` and note this path **must not** have a slash on the end of it)
      4. The report type `campus`
   2. Check results, stored in `<s3_directory>/freyja/reports/<freyja_processing_timestamp>_<bam_urls_filename_filestem>_campus/outputs/` (where `<bam_urls_filename_filestem>` for the above example is `2022-08-10_01-07-42-all_rtl_wastewater_highcov_s3_urls`)
      1. Look through any Freyja QC failures, which (if any exist) are stored in the results directory in `<bam_urls_filename_filestem>_<freyja_processing_timestamp>_freyja_qc_fails.tsv` 
      2. Look through the report output, which is stored in the results directory in `<bam_urls_filename_filestem>_<freyja_processing_timestamp>_freyja_aggregated_campus_dashboard_report_<report_processing_timestamp>.csv`
      3. Assuming the QC failures are not worrisome, manually copy the report output to the `campus_dashboard` folder in the s3 bucket being used
```
# Example:

cd /shared/workspace/software/cview_currents/scripts
# Command format:
# bash run_distributed_freyja.sh <bam_urls_file> <run_name> <s3_parent_directory>
bash run_distributed_freyja.sh /shared/temp/2022-08-10_01-07-42-all_rtl_wastewater_highcov_s3_urls.txt 2022-08-10_01-07-42-all_rtl_wastewater_highcov s3://ucsd-rtl-test/freyja campus
# If desired, check job status by running:
squeue
```
