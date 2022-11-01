#!/usr/bin/env bash
# Create a job to run freyja update to get latest barcodes and lineages
#
# NB: A job seems like overkill for this, but it is necessary
# because the head node of our cluster configuration
# doesn't have enough memory and it fails with a cryptic error
# (FileNotFoundError: [Errno 2] No such file or directory: './lineagePaths.txt')
# because an intermediate file can't be created.

CVIEWCURRENTS_DIR="$REPOS_DIR"/cview_currents

echo "submitting freja update job"
UPDATE_SLURM_JOB_ID=$UPDATE_SLURM_JOB_ID:$(sbatch \
  -J update_freyja \
  -D /shared/logs \
  -c 32 \
  "$CVIEWCURRENTS_DIR/scripts/update_freyja.sh")