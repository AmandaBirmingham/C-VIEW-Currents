#!/usr/bin/env bash

# Activate conda env freyja-env
ANACONDADIR=/shared/workspace/software/anaconda3/bin
source $ANACONDADIR/activate freyja-env

# by default, the usher_barcodes.csv and curated_lineages.json files
# end up in
# /shared/workspace/software/anaconda3/envs/freyja-env/lib/python3.10/site-packages/freyja/data

echo "updating freyja"
# TODO: decide whether to put back the outdir param
freyja update # --outdir $LOCAL_RUN_DIR