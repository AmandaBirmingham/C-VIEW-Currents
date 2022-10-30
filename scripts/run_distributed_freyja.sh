#!/usr/bin/env bash
# Run freyja on a set of Genexus bams listed by their S3 url in an input file
# and produce an aggregated tsv of results, distributing tasks via slurm
#
# NOTE: before using this script on a new instance, *first ensure*:
# * any "placeholder" constants below have been replaced with their real values
#
# Sample usage:
# bash /shared/workspace/software/cview_currents/scripts/run_distributed_freyja.sh /shared/temp/220708_run_bam_s3_urls.txt 220708_run s3://ucsd-rtl-test

REPOS_DIR=/shared/workspace/software/
CVIEWCURRENTS_DIR="$REPOS_DIR"/cview_currents
METADATA_LINE_PREFIX="# metadata:"

update_repos() {
  tmp_dir=$(mktemp -d -t cview-currents-XXXXXXXXXX)
  echo "Select run data stored to temporary dir $tmp_dir"
  echo "When finished examining data, run"
  echo "rm -rf $tmp_dir"

  # get the aggregated and (if present) relgrowthrate files and their log(s)
	aws s3 cp $SUMMARY_S3_DIR/ $tmp_dir/ \
		--quiet \
		--recursive \
		--include "*error.log" \
		--include "*.csv" \
		--include "*.tsv"

  # get the report error log(s)
  aws s3 cp REPORT_RUN_S3_DIR/ $tmp_dir/ \
  --quiet \
  --recursive \
  --include "*error.log"

  echo "Gathering exit codes"
  cat $tmp_dir/*error.log > $tmp_dir/"$RUN_NAME".error.log

  # if any errors happened upstream of here, the results shouldn't be pushed
  # to the repositories
  if [ -s $tmp_dir/"$RUN_NAME"_repos.error.log ]; then
    echo "Errors in processing $RUN_NAME; repo upload cancelled"
    exit 1
  fi

#  # Upload freyja metadata and aggregate/relgrowthrate results to Josh's repo
#  cd $REPOS_DIR/SD-Freyja-Outputs || exit
#  git checkout main
#  git pull
#
#  mv $tmp_dir/*.csv $REPOS_DIR/SD-Freyja-Outputs
#  mv $tmp_dir/*.tsv $REPOS_DIR/SD-Freyja-Outputs
#
#  # commit/push changes direct to josh repo
#  git commit -a -m "$RUN_NAME"
#  git push

  # Upload report files to local fork and then make PR for andersen lab repo;
  # start by pulling down the updated report files
  aws s3 cp $REPORT_RUN_S3_DIR/outputs/ $tmp_dir/ \
  --quiet \
  --recursive \
  --include "*.csv"

  cd $REPOS_DIR/SARS-CoV-2_WasteWater_San-Diego || exit
  git checkout master
  git pull upstream master  # get any updates from andersen lab (original) repo

  mv $tmp_dir/*.csv $REPOS_DIR/SARS-CoV-2_WasteWater_San-Diego

  git commit -a -m "$RUN_NAME"  # orig repo updates + local changes, to fork
  git push

  # TODO: put back in
  # Make a PR to the andersen lab (original) repo
  #gh pr create --repo andersen-lab/SARS-CoV-2_WasteWater_San-Diego \
  #  --title "$RUN_NAME" --body "Automated PR from C-VIEW Currents"
}

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

echo "submitting freja update job"
#UPDATE_SLURM_JOB_ID=$UPDATE_SLURM_JOB_ID:$(sbatch \
#  -J update_$RUN_NAME \
#  -D /shared/logs \
#  -c 32 \
#  $CVIEWCURRENTS_DIR/scripts/update_freyja.sh)
#
#UPDATE_DEPENDENCY_PARAM="--dependency=afterok:${UPDATE_SLURM_JOB_ID##* }"
#
#TRANSFER_SETTINGS_SLURM_JOB_ID=$TRANSFER_SETTINGS_SLURM_JOB_ID:$(sbatch $UPDATE_DEPENDENCY_PARAM \
#    --export=$(echo "OUTPUT_S3_DIR=$OUTPUT_S3_DIR" | sed 's/ //g') \
#    -J settings_transfer_"$RUN_NAME"_"$TIMESTAMP" \
#    -D /shared/logs \
#    -c 2 \
#    $CVIEWCURRENTS_DIR/scripts/transfer_freyja_settings_files.sh)
#
#TRANSFER_DEPENDENCY_PARAM="--dependency=afterok:${TRANSFER_SETTINGS_SLURM_JOB_ID##* }"

METADATA_S3URL=""
SAMPLES_JOB_IDS=""
#while read -r SAMPLE_S3URL; do
#  if [[ "$SAMPLE_S3URL" == "$METADATA_LINE_PREFIX"* ]]; then
#      METADATA_S3URL=${SAMPLE_S3URL/"${METADATA_LINE_PREFIX}"/}
#      # continue to next line
#  else
#    SAMPLE=$(basename "$SAMPLE_S3URL")
#    echo "submitting freyja job for $SAMPLE"
#    SAMPLES_JOB_IDS=$SAMPLES_JOB_IDS:$(sbatch $TRANSFER_DEPENDENCY_PARAM \
#      --export=$(echo "SAMPLE_S3URL=$SAMPLE_S3URL,\
#                OUTPUT_S3_DIR=$SAMPLES_OUTPUT_S3_DIR,\
#                RUN_WORKSPACE=$RUN_WORKSPACE" | sed 's/ //g') \
#      -J "$SAMPLE"_"$RUN_NAME"_"$TIMESTAMP" \
#      -D /shared/logs \
#      -c 2 \
#      $CVIEWCURRENTS_DIR/scripts/run_freyja_on_sample.sh)
#  fi
#done <"$S3_URLS_FP"
#
#SAMPLES_JOB_IDS=$(echo $SAMPLES_JOB_IDS | sed 's/Submitted batch job //g')

## NB: other dependency param declarations include a ":" after "afterok"
## but this one does NOT, because the leading ":" is already included in the
## $SAMPLES_JOB_IDS contents
#SAMPLES_DEPENDENCY_PARAM="--dependency=afterok$SAMPLES_JOB_IDS"

echo "submitting freyja aggregate job for $SAMPLES_OUTPUT_S3_DIR"
AGG_FNAME="$RUN_NAME"_"$TIMESTAMP"_freyja_aggregated.tsv
#AGGREGATE_JOB_ID=$AGGREGATE_JOB_ID:$(sbatch $SAMPLES_DEPENDENCY_PARAM \
#  --export=$(echo "RUN_NAME=$RUN_NAME,\
#            RUN_WORKSPACE=$RUN_WORKSPACE,\
#            OUT_AGG_FNAME=$AGG_FNAME, \
#            SAMPLES_S3_DIR=$SAMPLES_OUTPUT_S3_DIR, \
#            OUTPUT_S3_DIR=$AGG_OUTPUT_S3_DIR" | sed 's/ //g') \
#  -J aggregate_$RUN_NAME \
#  -D /shared/logs \
#  -c 32 \
#  $CVIEWCURRENTS_DIR/scripts/aggregate_freyja_outputs.sh)
#
#AGGREGATE_DEPENDENCY_PARAM="--dependency=afterok:${AGGREGATE_JOB_ID##* }"
#
#if [[ "$METADATA_S3URL" == "" ]]; then
#  echo "Error: Unable to generate growth rate or report with empty METADATA_S3URL"
#  exit 1
#fi

#echo "submitting report creation job for $REPORT_NAME"
## NB: depends on aggregate job but NOT on relgrowthrate job
#REPORT_JOB_ID=$REPORT_JOB_ID:$(sbatch $AGGREGATE_DEPENDENCY_PARAM \
#  --export=$(echo "REPORT_NAME=$REPORT_NAME,\
#            RUN_WORKSPACE=$RUN_WORKSPACE,\
#            SUMMARY_S3_DIR=$AGG_OUTPUT_S3_DIR, \
#            METADATA_S3URL=$METADATA_S3URL, \
#            REPORT_TYPE=$REPORT_TYPE, \
#            OUTPUT_S3_DIR=$REPORT_RUN_S3_DIR" | sed 's/ //g') \
#  -J report_$REPORT_NAME \
#  -D /shared/logs \
#  -c 32 \
#  $CVIEWCURRENTS_DIR/scripts/generate_reports.sh)

AGGREGATE_S3URL="$AGG_OUTPUT_S3_DIR"/"$AGG_FNAME"
RELGROWTHRATE_FNAME="$RUN_NAME"_"$TIMESTAMP"_freyja_rel_growth_rates.csv

#if [[ "$REPORT_TYPE" == search ]]; then
#  echo "submitting freyja relgrowthrate job for $RUN_NAME"
#  RELGROWTHRATE_JOB_ID=$RELGROWTHRATE_JOB_ID:$(sbatch $AGGREGATE_DEPENDENCY_PARAM \
#    --export=$(echo "RUN_NAME=$RUN_NAME,\
#              RUN_WORKSPACE=$RUN_WORKSPACE,\
#              METADATA_S3URL=$METADATA_S3URL, \
#              AGGREGATE_S3URL=$AGGREGATE_S3URL, \
#              OUT_FNAME=$RELGROWTHRATE_FNAME, \
#              OUTPUT_S3_DIR=$AGG_OUTPUT_S3_DIR" | sed 's/ //g') \
#    -J growth_$RUN_NAME \
#    -D /shared/logs \
#    -c 32 \
#    $CVIEWCURRENTS_DIR/scripts/calc_freyja_relgrowthrate.sh)
#
#    RELGROWTHRATE_DEPENDENCY_PARAM="--dependency=afterok:${RELGROWTHRATE_JOB_ID##* }"
#fi
#
## copy the inputs/settings info to the output s3 directory for tracking
## (NB: make sure to do this at end, after freyja update has refreshed barcodes/lineages/etc)
#aws s3 cp $S3_URLS_FP $OUTPUT_S3_DIR/s3_urls.txt

tmp_dir=$(mktemp -d -t cview-currents-XXXXXXXXXX)
echo "Select run data stored to temporary dir $tmp_dir"
echo "When finished examining data, run"
echo "   rm -rf $tmp_dir"

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
NEW_SCRIPT_FP=$tmp_dir/"$REPORT_NAME"_update_repos.sh
cp "$SCRIPT_DIR"/template_update_repos.sh "$NEW_SCRIPT_FP"
# NB: use | instead of / as sed command delimiter since some of the replaced
# values contain /
sed -i "s|TMP_DIR|$tmp_dir|g" "$NEW_SCRIPT_FP"
sed -i "s|SUMMARY_S3_DIR|$AGG_OUTPUT_S3_DIR|g" "$NEW_SCRIPT_FP"
sed -i "s|REPORT_RUN_S3_DIR|$REPORT_RUN_S3_DIR|g" "$NEW_SCRIPT_FP"
sed -i "s|RUN_NAME|$RUN_NAME|g" "$NEW_SCRIPT_FP"
sed -i "s|REPOS_DIR|$REPOS_DIR|g" "$NEW_SCRIPT_FP"

echo "view $NEW_SCRIPT_FP"