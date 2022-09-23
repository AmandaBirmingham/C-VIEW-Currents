#!/usr/bin/env bash

FREYJA_DATA_DIR=/shared/workspace/software/anaconda3/envs/freyja-env/lib/python3.10/site-packages/freyja/data
aws s3 cp $FREYJA_DATA_DIR/usher_barcodes.csv $OUTPUT_S3_DIR/usher_barcodes.csv
aws s3 cp $FREYJA_DATA_DIR/curated_lineages.json $OUTPUT_S3_DIR/curated_lineages.json