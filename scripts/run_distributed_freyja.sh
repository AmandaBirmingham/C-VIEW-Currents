#!/usr/bin/env bash
# Run freyja on a set of Genexus bams listed by their S3 url in an input file
# and produce an aggregated tsv of results, distributing tasks via slurm
#
# NOTE: before using this script on a new instance, *first ensure*:
# * any "placeholder" constants below have been replaced with their real values
#
# Sample usage:
# bash /shared/workspace/software/cview_currents/scripts/run_distributed_freyja.sh /shared/temp/220708_run_bam_s3_urls.txt 220708_run s3://ucsd-rtl-test

REPOS_DIR=/shared/workspace/software
CVIEWCURRENTS_DIR="$REPOS_DIR"/cview_currents
FREYJA_DATA_DIR=/shared/workspace/software/anaconda3/envs/freyja-env/lib/python3.10/site-packages/freyja/data
METADATA_LINE_PREFIX="# metadata:"
CURR_DIR="$(dirname "$(realpath "$0")")"

if [ "$#" -ne 4 ] ; then
  echo "USAGE: $0 <s3_urls_fp> <run_name> <s3_output_base> <report_type>"; exit 1
else
  S3_URLS_FP=$1
  RUN_NAME=$2
  S3_OUTPUT_BASE=$3
  REPORT_TYPE=$4
  TIMESTAMP=$(date +'%Y-%m-%d_%H-%M-%S')
  REPORT_NAME="$TIMESTAMP"_"$RUN_NAME"_"$REPORT_TYPE"
  OUTPUT_S3_DIR="$S3_OUTPUT_BASE"/"$RUN_NAME"/"$RUN_NAME"_results/"$TIMESTAMP"
  SAMPLES_OUTPUT_S3_DIR="$OUTPUT_S3_DIR"/"$RUN_NAME"_samples
  AGG_OUTPUT_S3_DIR="$OUTPUT_S3_DIR"/"$RUN_NAME"_summary
  REPORT_RUN_S3_DIR="$S3_OUTPUT_BASE"/reports/"$REPORT_NAME"
  RUN_WORKSPACE="/scratch/$RUN_NAME/$TIMESTAMP"
fi

if [[ ! "$REPORT_TYPE" =~ ^(search|campus)$ ]]; then
  echo "Error: REPORT_TYPE must be one of 'search' or 'campus'"
  exit 1
fi

cd $CVIEWCURRENTS_DIR || exit 1
# see CVIEW show_version.sh for full description of this command
VERSION_INFO=$( (git describe --tags && git log | head -n 1  && git checkout) | tr ' ' '_' | tr '\t' '_' | sed -z 's/\n/./g;s/.$/\n/')
cd "$CURR_DIR" || exit 1

# upload the current freyja data files to the output dir
aws s3 cp $FREYJA_DATA_DIR/usher_barcodes.csv "$OUTPUT_S3_DIR"/usher_barcodes.csv
aws s3 cp $FREYJA_DATA_DIR/curated_lineages.json "$OUTPUT_S3_DIR"/curated_lineages.json

# copy the inputs/settings info to the output s3 directory for tracking
aws s3 cp "$S3_URLS_FP" "$OUTPUT_S3_DIR/s3_urls.txt"

METADATA_S3URL=""
SAMPLES_JOB_IDS=""
while read -r SAMPLE_S3URL; do
  if [[ "$SAMPLE_S3URL" == "$METADATA_LINE_PREFIX"* ]]; then
      METADATA_S3URL=${SAMPLE_S3URL/"${METADATA_LINE_PREFIX}"/}
      # continue to next line
  else
    SAMPLE=$(basename "$SAMPLE_S3URL")

    echo "submitting freyja job for $SAMPLE"
    # NB: *don't* double-quote dependency param
    SAMPLES_JOB_IDS=$SAMPLES_JOB_IDS:$(sbatch $TRANSFER_DEPENDENCY_PARAM \
      --export=$(echo "SAMPLE_S3URL=$SAMPLE_S3URL,\
                VERSION_INFO=$VERSION_INFO,\
                OUTPUT_S3_DIR=$SAMPLES_OUTPUT_S3_DIR,\
                RUN_WORKSPACE=$RUN_WORKSPACE" | sed 's/ //g') \
      -J "$SAMPLE"_"$RUN_NAME"_"$TIMESTAMP" \
      -D /shared/logs \
      -c 2 \
      $CVIEWCURRENTS_DIR/scripts/run_freyja_on_sample.sh)
  fi

  # TODO remove debug exit
  exit 1
done <"$S3_URLS_FP"

SAMPLES_JOB_IDS=$(echo "$SAMPLES_JOB_IDS" | sed 's/Submitted batch job //g')

# NB: other dependency param declarations include a ":" after "afterok"
# but this one does NOT, because the leading ":" is already included in the
# $SAMPLES_JOB_IDS contents
SAMPLES_DEPENDENCY_PARAM="--dependency=afterok$SAMPLES_JOB_IDS"

echo "submitting freyja aggregate job for $SAMPLES_OUTPUT_S3_DIR"
AGG_FNAME="$RUN_NAME"_"$TIMESTAMP"_freyja_aggregated.tsv
# NB: *don't* double-quote dependency param
AGGREGATE_JOB_ID=$AGGREGATE_JOB_ID:$(sbatch $SAMPLES_DEPENDENCY_PARAM \
  --export=$(echo "RUN_NAME=$RUN_NAME,\
            VERSION_INFO=$VERSION_INFO,\
            RUN_WORKSPACE=$RUN_WORKSPACE,\
            OUT_AGG_FNAME=$AGG_FNAME, \
            SAMPLES_S3_DIR=$SAMPLES_OUTPUT_S3_DIR, \
            OUTPUT_S3_DIR=$AGG_OUTPUT_S3_DIR" | sed 's/ //g') \
  -J aggregate_"$RUN_NAME" \
  -D /shared/logs \
  -c 32 \
  $CVIEWCURRENTS_DIR/scripts/aggregate_freyja_outputs.sh)

AGGREGATE_DEPENDENCY_PARAM="--dependency=afterok:${AGGREGATE_JOB_ID##* }"

if [[ "$METADATA_S3URL" == "" ]]; then
  echo "Error: Unable to generate growth rate or report with empty METADATA_S3URL"
  exit 1
fi

echo "submitting report creation job for $REPORT_NAME"
# NB: depends on aggregate job but NOT on relgrowthrate job
# NB: *don't* double-quote dependency param
REPORT_JOB_ID=$REPORT_JOB_ID:$(sbatch $AGGREGATE_DEPENDENCY_PARAM \
  --export=$(echo "REPORT_NAME=$REPORT_NAME,\
            VERSION_INFO=$VERSION_INFO,\
            RUN_WORKSPACE=$RUN_WORKSPACE,\
            SUMMARY_S3_DIR=$AGG_OUTPUT_S3_DIR, \
            METADATA_S3URL=$METADATA_S3URL, \
            REPORT_TYPE=$REPORT_TYPE, \
            OUTPUT_S3_DIR=$REPORT_RUN_S3_DIR" | sed 's/ //g') \
  -J report_"$REPORT_NAME" \
  -D /shared/logs \
  -c 32 \
  $CVIEWCURRENTS_DIR/scripts/generate_reports.sh)

AGGREGATE_S3URL="$AGG_OUTPUT_S3_DIR"/"$AGG_FNAME"

if [[ "$REPORT_TYPE" == search ]]; then
  RELGROWTHRATE_FNAME="$RUN_NAME"_"$TIMESTAMP"_freyja_rel_growth_rates.csv

  echo "submitting freyja relgrowthrate job for $RUN_NAME"
  # NB: *don't* double-quote dependency param
  RELGROWTHRATE_JOB_ID=$RELGROWTHRATE_JOB_ID:$(sbatch $AGGREGATE_DEPENDENCY_PARAM \
    --export=$(echo "RUN_NAME=$RUN_NAME,\
              VERSION_INFO=$VERSION_INFO,\
              RUN_WORKSPACE=$RUN_WORKSPACE,\
              METADATA_S3URL=$METADATA_S3URL, \
              AGGREGATE_S3URL=$AGGREGATE_S3URL, \
              OUT_FNAME=$RELGROWTHRATE_FNAME, \
              OUTPUT_S3_DIR=$AGG_OUTPUT_S3_DIR" | sed 's/ //g') \
    -J growth_"$RUN_NAME" \
    -D /shared/logs \
    -c 32 \
    $CVIEWCURRENTS_DIR/scripts/calc_freyja_relgrowthrate.sh)

  # RELGROWTHRATE_DEPENDENCY_PARAM="--dependency=afterok:${RELGROWTHRATE_JOB_ID##* }"

  # Upload the results to the SEARCH-related Github repos;
  # Do this here rather than in a job because it changes files
  # in the /shared/workspace/software directory
  TMP_DIR=$(mktemp -d -t cview-currents-XXXXXXXXXX)
  NEW_SCRIPT_FP="$TMP_DIR/$REPORT_NAME"_update_repos.sh
  cat "$VERSION_INFO" > "$TMP_DIR/$REPORT_NAME"_version.log
  cp "$CURR_DIR"/template_update_repos.sh "$NEW_SCRIPT_FP"

  # NB: use | instead of / as sed command delimiter since some of the replaced
  # values contain /
  sed -i "s|TMP_DIR|$TMP_DIR|g" "$NEW_SCRIPT_FP"
  sed -i "s|SUMMARY_S3_DIR|$AGG_OUTPUT_S3_DIR|g" "$NEW_SCRIPT_FP"
  sed -i "s|REPORT_RUN_S3_DIR|$REPORT_RUN_S3_DIR|g" "$NEW_SCRIPT_FP"
  sed -i "s|RUN_NAME|$RUN_NAME|g" "$NEW_SCRIPT_FP"
  sed -i "s|REPOS_DIR|$REPOS_DIR|g" "$NEW_SCRIPT_FP"

  echo ""
  echo "Check on job progress by running:"
  echo "  squeue"
  echo "When the queue is empty, view the customized repo upload script:"
  echo "  more $NEW_SCRIPT_FP"
  echo "Run the customized repo upload script:"
  echo "  bash $NEW_SCRIPT_FP"
  echo "When finished, delete the temporary directory:"
  echo "   rm -rf $TMP_DIR"
fi

echo ""
echo "REMINDER: Did you remember to run"
echo "  bash scripts/update_freyja.sh"
echo "before this?  If not, cancel these jobs with"
echo '  scancel -u $USER'  #NB: single quotes bc don't WANT $USER to expand
echo "and update freyja before continuing!"
echo ""  # spacer line
