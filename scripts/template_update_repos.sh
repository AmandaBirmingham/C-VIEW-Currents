# get the aggregated and (if present) relgrowthrate files and their log(s)
aws s3 cp SUMMARY_S3_DIR/ TMP_DIR/ \
  --quiet \
  --recursive \
  --include "*error.log" \
  --include "*.csv" \
  --include "*.tsv"

# get the report error log(s)
aws s3 cp REPORT_RUN_S3_DIR/ TMP_DIR/ \
--quiet \
--recursive \
--include "*error.log"

echo "Gathering exit codes"
cat TMP_DIR/*error.log > TMP_DIR/RUN_NAME.error.log

# if any errors happened upstream of here, the results shouldn't be pushed
# to the repositories
if [ -s TMP_DIR/RUN_NAME_repos.error.log ]; then
  echo "Errors in processing RUN_NAME; repo upload cancelled"
  exit 1
fi

#  # Upload freyja metadata and aggregate/relgrowthrate results to Josh's repo
#  cd $REPOS_DIR/SD-Freyja-Outputs || exit
#  git checkout main
#  git pull
#
#  mv TMP_DIR/*.csv REPOS_DIR/SD-Freyja-Outputs
#  mv TMP_DIR/*.tsv REPOS_DIR/SD-Freyja-Outputs
#
#  # commit/push changes direct to josh repo
#  git commit -a -m "RUN_NAME"
#  git push

# Upload report files to local fork and then make PR for andersen lab repo;
# start by pulling down the updated report files
aws s3 cp REPORT_RUN_S3_DIR/outputs/ TMP_DIR/ \
--quiet \
--recursive \
--include "*.csv"

cd REPOS_DIR/SARS-CoV-2_WasteWater_San-Diego || exit
git checkout master
git pull upstream master  # get any updates from andersen lab (original) repo

mv TMP_DIR/*.csv REPOS_DIR/SARS-CoV-2_WasteWater_San-Diego

git commit -a -m "RUN_NAME"  # orig repo updates + local changes, to fork
git push

# TODO: put back in
# Make a PR to the andersen lab (original) repo
#gh pr create --repo andersen-lab/SARS-CoV-2_WasteWater_San-Diego \
#  --title "RUN_NAME" --body "Automated PR from C-VIEW Currents"