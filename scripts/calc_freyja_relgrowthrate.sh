#!/usr/bin/env bash

# Inputs
#   RUN_WORKSPACE
#   RUN_NAME
#   METADATA_S3URL
#   AGGREGATE_S3URL
#   OUT_FNAME
#   OUTPUT_S3_DIR

ANACONDADIR=/shared/workspace/software/anaconda3/bin

# Clear workspace directory if node is being reused
WORKSPACE=$RUN_WORKSPACE/relgrowthrate
rm -rf $WORKSPACE
mkdir -p $WORKSPACE

calc_freyja_relgrowthrates() {
  # copy inputs to temporary local files
  aws s3 cp "$METADATA_S3URL" "$WORKSPACE"/freyja_metadata.csv
  aws s3 cp "$AGGREGATE_S3URL" "$WORKSPACE"/freyja_aggregated.csv

  # Activate conda env freyja-env
  source $ANACONDADIR/activate freyja-env

  echo "running freyja relgrowthrate for $RUN_NAME"
  freyja relgrowthrate "$WORKSPACE"/freyja_aggregated.csv "$WORKSPACE"/freyja_metadata.csv
  echo -e "freyja relgrowthrate exit code: $?" >> $WORKSPACE/"$RUN_NAME"_freyja_relgrowthrate.exit.log

  mv rel_growth_rates.csv "$WORKSPACE"/"$OUT_FNAME"
  echo -e "relgrowthrate output move exit code: $?" >> $WORKSPACE/"$RUN_NAME"_freyja_relgrowthrate.exit.log

  # Gather relgrowthrate error code, if any
  grep -v "exit code: 0" $WORKSPACE/"$RUN_NAME"_freyja_relgrowthrate.exit.log | head -n 1 >> $WORKSPACE/"$RUN_NAME"_freyja_relgrowthrate.error.log
}

{ time ( calc_freyja_relgrowthrates ) ; } > $WORKSPACE/"$RUN_NAME"_freyja_relgrowthrate.log 2>&1

# upload only logs and *_freyja_rel_growth_rates.csv to s3 in top-level dict
aws s3 cp $WORKSPACE/ $OUTPUT_S3_DIR/ --recursive --exclude "*" --include "*.log" --include "*freyja_rel_growth_rates.csv" --exclude "*/*.*"
