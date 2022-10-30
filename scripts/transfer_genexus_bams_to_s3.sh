#!/usr/bin/env bash
# Download BAMs from the Genexus machine to local instance,
# then upload them to S3 and delete local copies.
#
# NOTE: before using this script on a new instance, *first ensure*:
# * aws cli has been configured on the instance
# * an rsa key is in ~/genexus/id_rsa
# * the public rsa key has been placed on the genexus machine, AND
# * any "placeholder" constants below have been replaced with their real values
#
# Sample usage:
# bash /shared/workspace/projects/covid/scripts/transfer_genexus_bams_to_s3.sh /shared/workspace/projects/covid/data s3://ucsd-rtl-test 20220401_CLIA /shared/workspace/projects/covid/data/sample_names.txt
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
GENEXUS_REPORTS='/serverdata/results/analysis/output/reports'
GENEXUS_BAM='merged.bam.ptrim.bam'
GENEXUS_RSA_FP=~/genexus/id_rsa
OUT_BAM_SUF='trimmed.sorted.unfiltered.bam'

# check usage
if [ "$#" -ne 4 ] ; then
  echo "USAGE: $0 <output_dir> <s3_bucket_url> <run_name> <sample_names.txt>"; exit 1
else
  SAMPLENAMES_FP=$4
fi

LOCAL_DIR=$1
# if the local dir ends with a slash, remove the slash
if [[ "$LOCAL_DIR" == */ ]]; then
  LOCAL_DIR=${LOCAL_DIR%/*}
fi

S3_BUCKET=$2
RUN_NAME=$3
OUTPUT_S3_URLS_FP="$LOCAL_DIR/$RUN_NAME"_s3_urls.txt
OUTPUT_SAMPLE_NAMES_FP="$LOCAL_DIR/$RUN_NAME"_samples.txt
UPLOAD_S3_FOLDER="$S3_BUCKET/$RUN_NAME"
UPLOAD_S3_BAM_FOLDER="$UPLOAD_S3_FOLDER/$RUN_NAME"_bam

# check local folder
LOCAL_RUN_DIR=$LOCAL_DIR/$RUN_NAME
if [ -d "$LOCAL_RUN_DIR" ] ; then
    echo "Specified local folder already exists: $LOCAL_RUN_DIR" ; exit 1
elif [ -f "$LOCAL_RUN_DIR" ] ; then
    echo "Specified local folder already exists as a file: $LOCAL_RUN_DIR" ; exit 1
else
    echo "Creating local folder: $LOCAL_RUN_DIR"
    mkdir "$LOCAL_RUN_DIR"
fi

# take the first column of a comma-delimited file;
# note that it is fine for the file to contain only one column
# (and thus no commas)
FOLDER_IDENTIFIERS=($(awk -F "," '{print $1}' "$SAMPLENAMES_FP"))

BAM_PATHS=()
for folder_id in "${FOLDER_IDENTIFIERS[@]}" ; do
    BAM_PATHS+=($(ssh -i "$GENEXUS_RSA_FP" "$GENEXUS_USERNAME@$GENEXUS_IP" ls "$GENEXUS_REPORTS/*$folder_id*/$GENEXUS_BAM"))
done

# download BAMs
LEFT_CRUFT="$GENEXUS_REPORTS/AssayDev_"
for bam_path in "${BAM_PATHS[@]}" ; do
  temp_name=${bam_path/"${LEFT_CRUFT}"/}  # Remove the left part.
  sample_name=${temp_name%%_SARS-CoV-2Insight*}  # Remove the right part.

  # assume sample names don't follow naming convention used by C-VIEW,
  # so munge them into that format for compatibility
  sample_name="$sample_name"__NA__NA__"$RUN_NAME"__00X
  echo "$sample_name" >> "$OUTPUT_SAMPLE_NAMES_FP"

  sample_fname="$sample_name.$OUT_BAM_SUF"
  local_path="$LOCAL_RUN_DIR/$sample_fname"
  s3_bam_url="$UPLOAD_S3_BAM_FOLDER/$sample_fname"

  echo "Downloading: $bam_path to $local_path"
  scp -i "$GENEXUS_RSA_FP" "$GENEXUS_USERNAME@$GENEXUS_IP:$bam_path" "$local_path"
  scp -i "$GENEXUS_RSA_FP" "$GENEXUS_USERNAME@$GENEXUS_IP:$bam_path".bai "$local_path".bai

  echo "$s3_bam_url" >> "$OUTPUT_S3_URLS_FP"
done

# TODO: Alternately, could capture S3 locations from stdio output of s3 cp
#  which looks like
#  upload: myDir/test1.txt to s3://mybucket/test1.txt
#  Although would need some massaging, would also be more strictly accurate

# make freyja metadata file and add to s3 outputs
echo "Generating freyja-compliant metadata file"
FREYJA_METADATA_FNAME="$RUN_NAME"_freyja_metadata.csv
FREYJA_METADATA_FP="$LOCAL_DIR/$FREYJA_METADATA_FNAME"
make_freyja_metadata "$OUTPUT_SAMPLE_NAMES_FP" "$SAMPLENAMES_FP" "$FREYJA_METADATA_FP"

FREYJA_METADATA_S3_URL="$UPLOAD_S3_FOLDER"/"$FREYJA_METADATA_FNAME"
echo "# metadata:$FREYJA_METADATA_S3_URL" >> "$OUTPUT_S3_URLS_FP"

echo "Uploading local folder contents to s3"
# upload metadata file to the run folder
aws s3 cp "$FREYJA_METADATA_FP" "$FREYJA_METADATA_S3_URL"
# upload all the local bam folder contents to the run's bam folder
aws s3 cp "$LOCAL_RUN_DIR/" "$UPLOAD_S3_BAM_FOLDER" --recursive

echo "Removing local folder: $LOCAL_RUN_DIR"
rm -rf "$LOCAL_RUN_DIR"
