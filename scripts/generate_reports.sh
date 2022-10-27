#!/usr/bin/env bash

# Inputs
#   RUN_WORKSPACE
#   REPORT_NAME
#   SUMMARY_S3_DIR
#   METADATA_S3URL
#   REPORT_TYPE
#   OUTPUT_S3_DIR

ANACONDADIR=/shared/workspace/software/anaconda3/bin

# Clear workspace directory if node is being reused
WORKSPACE=$RUN_WORKSPACE/reports
rm -rf $WORKSPACE
mkdir -p $WORKSPACE

generate_freyja_reports() {
  mkdir "$WORKSPACE"/inputs
  mkdir "$WORKSPACE"/outputs

  aws s3 cp $METADATA_S3URL "$WORKSPACE"/inputs

  # Activate conda env cview_currents
  source $ANACONDADIR/activate cview_currents

  # copy inputs to temporary local files
  echo "downloading report inputs for $REPORT_NAME"
  download_report_inputs "$SUMMARY_S3_DIR" "$WORKSPACE"/inputs
  echo -e "download_report_inputs exit code: $?" >> $WORKSPACE/"$REPORT_NAME"_reports.exit.log

   echo "running search dashboard reports for $REPORT_NAME"
  if [ "$REPORT_TYPE" == "search" ]; then
    make_search_reports "$WORKSPACE"/inputs "$WORKSPACE"/outputs
    echo -e "make_search_reports exit code: $?" >> $WORKSPACE/"$REPORT_NAME"_reports.exit.log
  elif [ "$REPORT_TYPE" == "campus" ]; then
    make_campus_reports "$WORKSPACE"/inputs "$WORKSPACE"/outputs
    echo -e "make_campus_reports exit code: $?" >> $WORKSPACE/"$REPORT_NAME"_reports.exit.log
  fi

  # Gather error code(s), if any
  grep -v "exit code: 0" $WORKSPACE/"$REPORT_NAME"_reports.exit.log | head -n 1 >> $WORKSPACE/"$REPORT_NAME"_reports.error.log
}

{ time ( generate_freyja_reports ) ; } > $WORKSPACE/"$REPORT_NAME"_reports.log 2>&1

aws s3 cp $WORKSPACE/ $OUTPUT_S3_DIR/ --recursive
