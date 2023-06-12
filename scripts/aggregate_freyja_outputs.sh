#!/usr/bin/env bash

# Inputs
#   RUN_WORKSPACE
#   SAMPLES_S3_DIR
#   RUN_NAME
#   OUT_AGG_FNAME
#   OUTPUT_S3_DIR
#   VERSION_INFO

ANACONDADIR=/shared/workspace/software/anaconda3/bin

# Clear workspace directory if node is being reused
WORKSPACE=$RUN_WORKSPACE/agg
rm -rf "$WORKSPACE"
mkdir -p "$WORKSPACE"

echo "$VERSION_INFO" >> "$WORKSPACE"/"$RUN_NAME"_aggregate.version.log

aggregate_freyja_outputs() {
  aws s3 cp "$SAMPLES_S3_DIR"/ "$WORKSPACE"/ \
    --recursive \
    --exclude "*" \
    --include "*.demix_tsv"

# get any error log(s)
  aws s3 cp "$SAMPLES_S3_DIR"/ "$WORKSPACE"/error_logs \
  --recursive \
  --exclude "*" \
  --include "*error.log" \

  # Gather per-sample error codes
  echo "Gathering per-sample exit codes."
  find "$WORKSPACE"/error_logs -name '*error.log' -type f -print0 | xargs -0 cat >"$WORKSPACE"/"$RUN_NAME"_freyja_aggregated.error.log
  # below works most of the time but errors if there are tons of files
  #cat "$WORKSPACE"/*/*error.log > "$WORKSPACE"/"$RUN_NAME"_freyja_aggregated.error.log

# TODO: Decide whether to put back
#  # Bail here if error log is not empty
#  if [[ -s "$WORKSPACE"/"$RUN_NAME"_freyja_aggregated.error.log ]]; then
#    echo "The freyja_aggregated.error.log is not empty, so aggregation is cancelled."
#    exit 1
#  fi

  find "$WORKSPACE" -name '*.demix_tsv' -type f -print0 | xargs -0 -I {} mv {} "$WORKSPACE"
  # below works most of the time but errors if there are tons of files
  #mv "$WORKSPACE"/*/*.demix_tsv "$WORKSPACE"

  # Activate conda env freyja-env
  source $ANACONDADIR/activate freyja-env

  echo "aggregating freyja calls for $RUN_NAME"
  freyja aggregate "$WORKSPACE"/ --output "$WORKSPACE"/"$OUT_AGG_FNAME" --ext demix_tsv
  echo -e "freyja demix exit code: $?" >> "$WORKSPACE"/"$RUN_NAME"_freyja_aggregated.exit.log

  # Gather aggregation error code(s)
  grep -v "exit code: 0" "$WORKSPACE"/"$RUN_NAME"_freyja_aggregated.exit.log | head -n 1 >> "$WORKSPACE"/"$RUN_NAME"_freyja_aggregated.error.log
}

{ time ( aggregate_freyja_outputs ) ; } > "$WORKSPACE"/"$RUN_NAME"_freyja_aggregated.log 2>&1

# upload only logs and .tsv to s3 in top-level dict
aws s3 cp "$WORKSPACE"/ "$OUTPUT_S3_DIR"/ --recursive --exclude "*" --include "*.log" --include "*.tsv" --exclude "*/*.*"
