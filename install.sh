#!/bin/bash

# ------ BEFORE this script ------
# create a clean t2.medium ubuntu 20.04 instance
# [NB: it MUST be version 20.04, NOT the latest version (e.g. 22.04)
# because 20.04 is the latest version supported by AWS ParallelCluster]
# with a 35 GB root drive and a 150 GB EBS drive,
# and security group allowing:
# SSH	via TCP	on port 22
# all traffic via all protocols on all ports
#
# ssh onto new instance to set up file system and mount:
# lsblk
# for the remainder, assume lsblk shows that the name of the
# EBS volume is xvdb:
# sudo file -s /dev/xvdb
# sudo mkfs -t xfs /dev/xvdb
# sudo mkdir /shared
# sudo mount /dev/xvdb /shared
# sudo chown `whoami` /shared
#
# install anaconda and python:
# cd /shared
# wget https://repo.anaconda.com/archive/Anaconda3-2020.11-Linux-x86_64.sh
# bash Anaconda3-2020.11-Linux-x86_64.sh
# (NB: install anaconda into /shared/workspace/software/anaconda3
# and say "yes" to having the installer initialize anaconda
# by running conda init)

# THEN EXIT THE TERMINAL
# and re-enter it
# ------------------------------------

# cd /shared
# then run this script:
# bash install.sh

# ------ AFTER this script ------
# make a snapshot of the 300 gb volume.
# use cview parallelcluster template to make
# a new cluster based on this snapshot.
# ssh into head node of cluster and run
#   aws configure
# to set up aws access
# ------------------------------------

SOFTWAREDIR=/shared/workspace/software
ANACONDADIR=$SOFTWAREDIR/anaconda3

# ------ Install basic tools ------
sudo apt-get update
sudo apt-get install git
sudo apt install awscli

# ------- Make log and software directories ------
mkdir -p /shared/logs
mkdir -p /shared/runfiles
mkdir -p $SOFTWAREDIR

# ------- Ensure no environment is active, and that conda is sourced ------
source $ANACONDADIR/bin/deactivate

# ------ Install freyja ------
conda create -n freyja-env
source $ANACONDADIR/bin/activate freyja-env

conda config --add channels defaults
conda config --add channels bioconda
conda config --add channels conda-forge

conda install freyja

source $ANACONDADIR/bin/deactivate

# ------- Install C-VIEW Currents -------
git clone https://github.com/AmandaBirmingham/C-VIEW-Currents.git $SOFTWAREDIR/cview_currents

conda create -n cview_currents pandas pyyaml gh
conda activate cview_currents

pip install -e $SOFTWAREDIR/cview_currents
