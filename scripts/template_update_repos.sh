# get the freyja metadata file
aws s3 cp METADATA_S3URL TMP_DIR/

# get the aggregated and (if present) relgrowthrate files and their log(s)
aws s3 cp SUMMARY_S3_DIR/ TMP_DIR/ \
  --recursive \
  --exclude "*" \
  --include "*error.log" \
  --include "*.csv" \
  --include "*.tsv"

# get the report error log(s)
aws s3 cp REPORT_RUN_S3_DIR/ TMP_DIR/ \
  --recursive \
  --exclude "*" \
  --include "*error.log"

echo "Gathering error logs"
cat TMP_DIR/*error.log > TMP_DIR/RUN_NAME_repos.error.log

# if any errors happened upstream of here, the results shouldn't be pushed
# to the repositories
if [ -s TMP_DIR/RUN_NAME_repos.error.log ]; then
  echo "Errors in processing RUN_NAME; repo upload cancelled"
  exit 1
fi

# Upload new freyja metadata and aggregate/relgrowthrate results to Josh's repo
cd REPOS_DIR/SD-Freyja-Outputs || exit
git checkout main
git pull

mv TMP_DIR/*.csv REPOS_DIR/SD-Freyja-Outputs
mv TMP_DIR/*.tsv REPOS_DIR/SD-Freyja-Outputs

# NB: -- denotes end of command line options, so any file names beginning
# with - won't be treated as git options. Not that there should be any here ...
git add -- *.csv
git add -- *.tsv

git commit -a -m "RUN_NAME"
git push

# Upload updated report files to local fork and then make PR for andersen
# lab repo; start by pulling down the updated report files
aws s3 cp REPORT_RUN_S3_DIR/outputs/ TMP_DIR/ \
  --recursive \
  --exclude "*" \
  --include "*.csv"

cd REPOS_DIR/SARS-CoV-2_WasteWater_San-Diego || exit
git checkout master
git pull upstream master  # get any updates from andersen lab (original) repo

mv TMP_DIR/*.csv REPOS_DIR/SARS-CoV-2_WasteWater_San-Diego

# NB: no need to `git add` because we are only updating existing files
git commit -a -m "RUN_NAME"  # orig repo updates + local changes, to fork
git push

# Make a PR to the andersen lab (original) repo
source ANACONDADIR/activate cview_currents
gh pr create --repo andersen-lab/SARS-CoV-2_WasteWater_San-Diego \
  --title "RUN_NAME" --body "Automated PR from C-VIEW Currents"
source ANACONDADIR/deactivate