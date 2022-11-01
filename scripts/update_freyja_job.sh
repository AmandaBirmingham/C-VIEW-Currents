#!/usr/bin/env bash

# NB: This process NEEDS to be run on a cluster node
# because the head node of our cluster configuration
# doesn't have enough memory and it fails with a cryptic error
# (FileNotFoundError: [Errno 2] No such file or directory: './lineagePaths.txt')
# because an intermediate file can't be created.

ANACONDADIR=/shared/workspace/software/anaconda3/bin

# TODO: add some logging so we know if this failed!

echo "updating freyja"
source $ANACONDADIR/activate freyja-env

# by default, the usher_barcodes.csv and curated_lineages.json files
# end up in
# /shared/workspace/software/anaconda3/envs/freyja-env/lib/python3.10/site-packages/freyja/data
freyja update

source $ANACONDADIR/deactivate

