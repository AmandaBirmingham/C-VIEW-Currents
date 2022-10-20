#!/usr/bin/env bash
# Run freyja on a set of Genexus bams listed by their S3 url in an input file
# and produce an aggregated tsv of results, distributing tasks via slurm
#
# NOTE: before using this script on a new instance, *first ensure*:
# * any "placeholder" constants below have been replaced with their real values
#
# Sample usage:
# bash /shared/workspace/software/cview_currents/scripts/run_distributed_freyja.sh /shared/temp/220708_run_bam_s3_urls.txt 220708_run s3://ucsd-rtl-test

CUTILSDIR=/shared/workspace/software/cview_currents

if [ "$#" -ne 3 ] ; then
  echo "USAGE: $0 <s3_urls_fp> <run_name> <s3_output_base>"; exit 1
else
  S3_URLS_FP=$1
  RUN_NAME=$2
  S3_OUTPUT_BASE=$3
  TIMESTAMP=$(date +'%Y-%m-%d_%H-%M-%S')
  OUTPUT_S3_DIR="$S3_OUTPUT_BASE"/"$RUN_NAME"/"$RUN_NAME"_results/"$TIMESTAMP"
  SAMPLES_OUTPUT_S3_DIR="$OUTPUT_S3_DIR"/"$RUN_NAME"_samples
  AGG_OUTPUT_S3_DIR="$OUTPUT_S3_DIR"/"$RUN_NAME"_summary
  RUN_WORKSPACE="/scratch/$RUN_NAME/$TIMESTAMP"
fi

echo "submitting freja update job"
UPDATE_SLURM_JOB_ID=$UPDATE_SLURM_JOB_ID:$(sbatch \
  -J update_$RUN_NAME \
  -D /shared/logs \
  -c 32 \
  $CUTILSDIR/scripts/update_freyja.sh)

UPDATE_DEPENDENCY_PARAM="--dependency=afterok:${UPDATE_SLURM_JOB_ID##* }"

TRANSFER_SETTINGS_SLURM_JOB_ID=$TRANSFER_SETTINGS_SLURM_JOB_ID:$(sbatch $UPDATE_DEPENDENCY_PARAM \
    --export=$(echo "OUTPUT_S3_DIR=$OUTPUT_S3_DIR" | sed 's/ //g') \
    -J settings_transfer_"$RUN_NAME"_"$TIMESTAMP" \
    -D /shared/logs \
    -c 2 \
    $CUTILSDIR/scripts/transfer_freyja_settings_files.sh)

TRANSFER_DEPENDENCY_PARAM="--dependency=afterok:${TRANSFER_SETTINGS_SLURM_JOB_ID##* }"

SAMPLES_JOB_IDS=""
while read -r SAMPLE_S3URL; do
  SAMPLE=$(basename "$SAMPLE_S3URL")
  echo "submitting freyja job for $SAMPLE"
  SAMPLES_JOB_IDS=$SAMPLES_JOB_IDS:$(sbatch $TRANSFER_DEPENDENCY_PARAM \
    --export=$(echo "SAMPLE_S3URL=$SAMPLE_S3URL,\
              OUTPUT_S3_DIR=$SAMPLES_OUTPUT_S3_DIR,\
              RUN_WORKSPACE=$RUN_WORKSPACE" | sed 's/ //g') \
    -J "$SAMPLE"_"$RUN_NAME"_"$TIMESTAMP" \
    -D /shared/logs \
    -c 2 \
    $CUTILSDIR/scripts/run_freyja_on_sample.sh)
done <"$S3_URLS_FP"

SAMPLES_JOB_IDS=$(echo $SAMPLES_JOB_IDS | sed 's/Submitted batch job //g')
# NB: other dependency param declarations include a ":" after "afterok"
# but this one does NOT, because the leading ":" is already included in the
# $SAMPLES_JOB_IDS contents
SAMPLES_DEPENDENCY_PARAM="--dependency=afterok$SAMPLES_JOB_IDS"

echo "submitting freyja aggregate job for $SAMPLES_OUTPUT_S3_DIR"
AGGREGATE_JOB_ID=$AGGREGATE_JOB_ID:$(sbatch $SAMPLES_DEPENDENCY_PARAM \
  --export=$(echo "RUN_NAME=$RUN_NAME,\
            RUN_WORKSPACE=$RUN_WORKSPACE,\
            TIMESTAMP=$TIMESTAMP, \
            SAMPLES_S3_DIR=$SAMPLES_OUTPUT_S3_DIR, \
            OUTPUT_S3_DIR=$AGG_OUTPUT_S3_DIR" | sed 's/ //g') \
  -J aggregate_$RUN_NAME \
  -D /shared/logs \
  -c 32 \
  $CUTILSDIR/scripts/aggregate_freyja_outputs.sh)

AGGREGATE_DEPENDENCY_PARAM="--dependency=afterok:${AGGREGATE_JOB_ID##* }"

# copy the inputs/settings info to the output s3 directory for tracking
# (NB: make sure to do this at end, after freyja update has refreshed barcodes/lineages/etc)
aws s3 cp $S3_URLS_FP $OUTPUT_S3_DIR/s3_urls.txt
