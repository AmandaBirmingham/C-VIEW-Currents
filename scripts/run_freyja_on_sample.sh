#!/usr/bin/env bash

# Inputs
#   SAMPLE_S3URL
#   RUN_WORKSPACE
#   OUTPUT_S3_DIR
#   VERSION_INFO

IGM_REF_NAME="NC_045512.2"
GENEXUS_REF_NAME="2019-nCoV"
REF_DIR=/shared/workspace/software/cview_currents/reference_files
ANACONDADIR=/shared/workspace/software/anaconda3/bin

SAMPLE_FNAME=$(basename "$SAMPLE_S3URL")
if [[ "$SAMPLE_FNAME" == *trimmed.sorted.bam ]]; then
    BAM_SUF='.trimmed.sorted.bam'
elif [[ "$SAMPLE_FNAME" == *trimmed.sorted.unfiltered.bam ]]; then
    BAM_SUF='.trimmed.sorted.unfiltered.bam'
fi

# double % because we want to remove the LONGEST match to .* (e.g. .trimmed.bam), not the shortest (e.g., .bam)
SAMPLE=${SAMPLE_FNAME%%"$BAM_SUF"}
SAMPLE_S3_OUTPUT_DIR="$OUTPUT_S3_DIR/$SAMPLE"

# Clear workspace directory if node is being reused
WORKSPACE="$RUN_WORKSPACE/$SAMPLE"
rm -rf "$WORKSPACE"
mkdir -p "$WORKSPACE"

echo "$VERSION_INFO" >> "$WORKSPACE/$SAMPLE.version.log"

run_freyja_on_sample() {
  # single # because we want to remove the SHORTEST match before the . , thus
  # leaving the whole complex extension (e.g. trimmed.bam rather than just bam)
  EXIT_LOG_FP="$WORKSPACE/$SAMPLE".exit.log

  if [[ "$BAM_SUF" == '.trimmed.sorted.bam' ]]; then
    REF_NAME="$IGM_REF_NAME"
  elif [[ "$BAM_SUF" == '.trimmed.sorted.unfiltered.bam' ]]; then
    REF_NAME="$GENEXUS_REF_NAME"
  else
    echo "Unrecognized suffix in sample name  $SAMPLE_FNAME"
    echo -e "$SAMPLE\treference selection exit code: 1" >> "$EXIT_LOG_FP"
    exit 1
  fi

  # download the bam and the bam.bai for this sample from S3 ...
  aws s3 cp "$SAMPLE_S3URL" "$WORKSPACE/$SAMPLE_FNAME"
  aws s3 cp "$SAMPLE_S3URL".bai "$WORKSPACE/$SAMPLE_FNAME".bai

  # Activate conda env freyja-env
  source "$ANACONDADIR"/activate freyja-env

  echo "calling variants for $SAMPLE"
  freyja variants "$WORKSPACE/$SAMPLE_FNAME" --variants "$WORKSPACE/$SAMPLE.tsv" --depths "$WORKSPACE/$SAMPLE"_depths.txt --ref "$REF_DIR/$REF_NAME.fas" --refname "$REF_NAME"
  echo -e "$SAMPLE\tfreyja variants exit code: $?" >> "$EXIT_LOG_FP"

  echo "demixing $SAMPLE"
  freyja demix  "$WORKSPACE/$SAMPLE.tsv" "$WORKSPACE/$SAMPLE"_depths.txt --output "$WORKSPACE/$SAMPLE".demix_tsv --confirmedonly
  echo -e "$SAMPLE\tfreyja demix exit code: $?" >> "$EXIT_LOG_FP"

  # Collect failure exit codes to error.log
  grep -v 'exit code: 0' "$EXIT_LOG_FP" | head -n 1 > "$WORKSPACE/$SAMPLE".error.log
}

{ time ( run_freyja_on_sample ) ; } > "$WORKSPACE/$SAMPLE".log 2>&1

# Upload everything in workspace except *.bam and *.bam.bai to s3
# This is outside the function so that even if it fails, the logs get uploaded
aws s3 cp "$WORKSPACE/" "$SAMPLE_S3_OUTPUT_DIR/" --recursive --include "*" --exclude "*$BAM_SUF" --exclude "*.bai"
