#!/usr/bin/env bash

# Inputs
#   RUN_WORKSPACE
#   SAMPLES_S3_DIR
#   RUN_NAME
#   TIMESTAMP
#   OUTPUT_S3_DIR

ANACONDADIR=/shared/workspace/software/anaconda3/bin

# Clear workspace directory if node is being reused
WORKSPACE=$RUN_WORKSPACE/agg
rm -rf $WORKSPACE
mkdir -p $WORKSPACE

aggregate_freyja_outputs() {
  aws s3 cp $SAMPLES_S3_DIR/ $WORKSPACE/ \
    --quiet \
    --recursive \
    --exclude "*" \
    --include "*.demix_tsv" \
    --include "*error.log"

  # Gather per-sample error codes
  echo "Gathering per-sample exit codes."
  cat $WORKSPACE/*/*error.log > $WORKSPACE/"$RUN_NAME"_freyja_aggregated.error.log

  # Bail here if error log is not empty
  if [[ -s $WORKSPACE/"$RUN_NAME"_freyja_aggregated.error.log ]]; then
    echo "The freyja_aggregated.error.log is not empty, so aggregation is cancelled."
    exit 1
  fi

  mv $WORKSPACE/*/*.demix_tsv $WORKSPACE

  # Activate conda env freyja-env
  source $ANACONDADIR/activate freyja-env

  echo "aggregating freyja calls for $RUN_NAME"
  freyja aggregate $WORKSPACE/ --output $WORKSPACE/"$RUN_NAME"_"$TIMESTAMP"_freyja_aggregated.tsv --ext demix_tsv
  echo -e "$SAMPLE\tfreyja demix exit code: $?" >> $WORKSPACE/"$RUN_NAME"_freyja_aggregated.exit.log

  # Gather aggregation error code(s)
  grep -v "exit code: 0" $WORKSPACE/"$RUN_NAME"_freyja_aggregated.exit.log | head -n 1 >> $WORKSPACE/"$RUN_NAME"_freyja_aggregated.error.log
}

{ time ( aggregate_freyja_outputs ) ; } > $WORKSPACE/"$RUN_NAME"_freyja_aggregated.log 2>&1

# upload only logs and .tsv to s3 in top-level dict
aws s3 cp $WORKSPACE/ $OUTPUT_S3_DIR/ --recursive --exclude "*" --include "*.log" --include "*.tsv" --exclude "*/*.*"
