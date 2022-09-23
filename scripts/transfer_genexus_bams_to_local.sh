#!/usr/bin/env bash
# Download BAMs from the Genexus machine to local instance
# into folder of cumulative BAMs
#
# NOTE: before using this script on a new instance, *first ensure*:
# * the public rsa key has been placed on the genexus machine, AND
# * any "placeholder" constants below have been replaced with their real values
#
# This script identifies the BAMS using a file of desired sample names.
#
# Sample usage:
# bash /shared/workspace/software/cutils/scripts/transfer_genexus_bams_to_local.sh /shared/temp/genexus_wastewater_bams /shared/temp/gxs_ww_samples1.txt
# where the sample_names.txt file contains no header and one sample name per line, e.g.,
#
# CALM_SEP_008066_19
# EXC_MW4_367431
# EXC_MW4_394788
#
# Derived from download_bams_genexus.sh (2022-03-21) (Niema Moshiri)

# important constants
GENEXUS_USERNAME='placeholder'
GENEXUS_IP='placeholder'
GENEXUS_REPORTS='placeholder'
GENEXUS_BAM='merged.bam.ptrim.bam'
GENEXUS_RSA_FP=~/genexus/id_rsa
OUT_BAM_SUF='trimmed.sorted.unfiltered.bam'

# check usage
if [ "$#" -ne 2 ] ; then
  echo "USAGE: $0 <output_dir> <sample_names.txt>"; exit 1
else
  LOCAL_DIR=$1
  SAMPLENAMES_FP=$2
fi

# check local folder
if [ -d "$LOCAL_DIR" ] ; then
    echo "Specified local folder already exists; continuing"
elif [ -f "$LOCAL_DIR" ] ; then
    echo "Specified local folder already exists as a file: $LOCAL_DIR" ; exit 1
else
    echo "Creating local folder: $LOCAL_DIR"
    mkdir "$LOCAL_DIR"
fi

FOLDER_IDENTIFIERS=($(cat "$SAMPLENAMES_FP"))
BAM_PATHS=()
for folder_id in "${FOLDER_IDENTIFIERS[@]}" ; do
    BAM_PATHS+=($(ssh -i "$GENEXUS_RSA_FP" "$GENEXUS_USERNAME@$GENEXUS_IP" ls "$GENEXUS_REPORTS/*$folder_id*/$GENEXUS_BAM"))
done

# download BAMs
RIGHT_CRUFT="$GENEXUS_REPORTS/AssayDev_"
for bam_path in "${BAM_PATHS[@]}" ; do
  temp_name=${bam_path/${RIGHT_CRUFT}/}  # Remove the left part.
  sample_name=${temp_name%%_SARS-CoV-2Insight*}  # Remove the right part.

  local_path="$LOCAL_DIR/$sample_name.$OUT_BAM_SUF"

  echo "Downloading: $bam_path to $local_path"
  scp -i "$GENEXUS_RSA_FP" "$GENEXUS_USERNAME@$GENEXUS_IP:$bam_path" "$local_path"
  scp -i "$GENEXUS_RSA_FP" "$GENEXUS_USERNAME@$GENEXUS_IP:$bam_path".bai "$local_path".bai
done