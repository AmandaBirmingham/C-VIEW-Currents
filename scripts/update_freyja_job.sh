#!/usr/bin/env bash

# NB: This process NEEDS to be run on a cluster node
# because the head node of our cluster configuration
# doesn't have enough memory and it fails with a cryptic error
# (FileNotFoundError: [Errno 2] No such file or directory: './lineagePaths.txt')
# because an intermediate file can't be created.

# Activate conda env freyja-env
ANACONDADIR=/shared/workspace/software/anaconda3/bin
source $ANACONDADIR/activate freyja-env

# by default, the usher_barcodes.csv and curated_lineages.json files
# end up in
# /shared/workspace/software/anaconda3/envs/freyja-env/lib/python3.10/site-packages/freyja/data

echo "updating freyja"
# TODO: decide whether to put back the outdir param
freyja update # --outdir $LOCAL_RUN_DIR
source $ANACONDADIR/deactivate