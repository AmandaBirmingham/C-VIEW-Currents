#!/usr/bin/env bash

# Inputs
#   RUN_WORKSPACE
#   REPORT_NAME
#   SUMMARY_S3_DIR
#   METADATA_S3URL
#   REPORT_TYPE
#   OUTPUT_S3_DIR
#   VERSION_INFO
#   CAMPUS_DASHBOARD_S3_DIR

ANACONDADIR=/shared/workspace/software/anaconda3/bin

# Clear workspace directory if node is being reused
WORKSPACE="$RUN_WORKSPACE/reports"
rm -rf "$WORKSPACE"
mkdir -p "$WORKSPACE"

echo "$VERSION_INFO" >> "$WORKSPACE"/"$REPORT_NAME".version.log

generate_freyja_reports() {
  mkdir "$WORKSPACE"/inputs
  mkdir "$WORKSPACE"/outputs
  mkdir "$WORKSPACE"/temp

  aws s3 cp "$METADATA_S3URL" "$WORKSPACE"/inputs

  # get the error log(s) from the summary dir;
  # if any errors happened upstream of here, report creation should not happen
  echo "Downloading and gathering error logs"
  aws s3 cp "$SUMMARY_S3_DIR"/ "$WORKSPACE"/temp/ \
    --recursive \
    --exclude "*" \
    --include "*error.log"

  cat "$WORKSPACE"/temp/*error.log > "$WORKSPACE"/"$REPORT_NAME"_reports.error.log
  rm -rf "$WORKSPACE"/temp

  if [ -s "$WORKSPACE"/"$REPORT_NAME"_reports.error.log ]; then  # if file not empty
    echo "Errors in processing $RUN_NAME; report creation cancelled"
    return 1  # exit function, go straight to aws upload
  fi

  # Activate conda env cview_currents
  source $ANACONDADIR/activate cview_currents

  # copy inputs to temporary local files
  echo "downloading report inputs for $REPORT_NAME"
  download_report_inputs "$SUMMARY_S3_DIR" "$WORKSPACE"/inputs
  echo -e "download_report_inputs exit code: $?" >> "$WORKSPACE/$REPORT_NAME"_reports.exit.log

   echo "running search dashboard reports for $REPORT_NAME"
  if [ "$REPORT_TYPE" == "search" ]; then
    make_search_reports "$WORKSPACE"/inputs "$WORKSPACE"/outputs
    echo -e "make_search_reports exit code: $?" >> "$WORKSPACE/$REPORT_NAME"_reports.exit.log
  elif [ "$REPORT_TYPE" == "campus" ]; then
    make_campus_reports "$WORKSPACE"/inputs "$WORKSPACE"/outputs
    echo -e "make_campus_reports exit code: $?" >> "$WORKSPACE/$REPORT_NAME"_reports.exit.log
  elif [ "$REPORT_TYPE" == "none" ]; then
    echo "No report generated because report type is 'none'"
  fi

  # Gather error code(s), if any
  grep -v "exit code: 0" "$WORKSPACE/$REPORT_NAME"_reports.exit.log | head -n 1 >> "$WORKSPACE/$REPORT_NAME"_reports.error.log

# TODO: decide if want to modify and put back
#  Removed bc want to put file in s3://whatever-bucket/campus_dashboard/ucsd but
#  current way of constructing $CAMPUS_DASHBOARD_S3_DIR would end up putting it
#  in s3://whatever-bucket/freyja/campus_dashboard/ucsd since usual top-level
#  s3 input is s3://whatever-bucket/freyja
#  if [ ! -s "$WORKSPACE"/"$REPORT_NAME"_reports.error.log ]; then  # if file IS empty
#    if [ "$REPORT_TYPE" == "campus" ]; then
#      echo "Uploading $REPORT_NAME report to campus dashboard s3 bucket"
#      aws s3 cp "$WORKSPACE"/outputs/ "$CAMPUS_DASHBOARD_S3_DIR"/ --recursive --exclude "*" --include "*_campus_dashboard_report_*.csv"
#    fi
#  fi
}

{ time ( generate_freyja_reports ) ; } > "$WORKSPACE/$REPORT_NAME"_reports.log 2>&1

aws s3 cp "$WORKSPACE"/ "$OUTPUT_S3_DIR"/ --recursive
