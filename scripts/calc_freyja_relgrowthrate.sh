#!/usr/bin/env bash

# Inputs
#   RUN_WORKSPACE
#   RUN_NAME
#   TIMESTAMP
#   METADATA_S3URL
#   AGGREGATE_S3_DIR
#   OUTPUT_S3_DIR

ANACONDADIR=/shared/workspace/software/anaconda3/bin
FREYJA_AGGREGATE_PATTERN="_freyja_aggregated.tsv"

# Clear workspace directory if node is being reused
WORKSPACE=$RUN_WORKSPACE/agg
rm -rf $WORKSPACE
mkdir -p $WORKSPACE

calc_freyja_relgrowthrates() {
  # copy metadata to a temporary local file
  aws s3 cp "$METADATA_S3URL" "$WORKSPACE"/freyja_metadata.csv

  # find the aggregate file in the input directory (latest one if >1 present)
  FREYJA_AGGREGATE_FNAME=$(aws s3 ls $AGGREGATE_S3_DIR/ |  grep $FREYJA_AGGREGATE_PATTERN| sort | tail -n 1 | awk '{print $NF}')
  aws s3 cp "$AGGREGATE_S3_DIR"/"$FREYJA_AGGREGATE_FNAME" "$WORKSPACE"/"$FREYJA_AGGREGATE_FNAME"

  # Activate conda env freyja-env
  source $ANACONDADIR/activate freyja-env

  echo "aggregating freyja calls for $RUN_NAME"
  freyja relgrowthrate "$WORKSPACE"/"$FREYJA_AGGREGATE_FNAME" "$WORKSPACE"/freyja_metadata.csv
  echo -e "freyja relgrowthrate exit code: $?" >> $WORKSPACE/"$RUN_NAME"_freyja_relgrowthrate.exit.log

  mv rel_growth_rates.csv "$WORKSPACE"/"$RUN_NAME"_"$TIMESTAMP"_freyja_rel_growth_rates.csv
  echo -e "relgrowthrate output move exit code: $?" >> $WORKSPACE/"$RUN_NAME"_freyja_relgrowthrate.exit.log

  # Gather relgrowthrate error code, if any
  grep -v "exit code: 0" $WORKSPACE/"$RUN_NAME"_freyja_relgrowthrate.exit.log | head -n 1 >> $WORKSPACE/"$RUN_NAME"_freyja_relgrowthrate.error.log
}

{ time ( calc_freyja_relgrowthrates ) ; } > $WORKSPACE/"$RUN_NAME"_freyja_relgrowthrate.log 2>&1

# upload only logs and *_freyja_rel_growth_rates.csv to s3 in top-level dict
aws s3 cp $WORKSPACE/ $OUTPUT_S3_DIR/ --recursive --exclude "*" --include "*.log" --include "*freyja_rel_growth_rates.csv" --exclude "*/*.*"
