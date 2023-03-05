#!/usr/bin/env bash

# WARNING: This script is NOT suitable for use as a cluster job;
# it is meant to be run stand-alone
#
# BEFORE running this script:
# pull down the oldest inputs folder (for _sewage_seqs.csv files)
# pull down _freyja_aggregated.tsv and _freyja_metadata.csv for all runs to be incorporated, and add them to the oldest_inputs folder
# pull down newest inputs folder (for _report_labels.csv, curated_lineages.json, lineages.yml)
#
# Sample usage:
# bash concat_past_freyja_runs.sh ~/Desktop/oldest_search_inputs ~/Desktop/newest_search_inputs ~/Desktop 2023-01-09_17-52-42_230107_WW_search_from_2022-11-28_01-28-46_221123_WW

# check usage
if [ "$#" -ne 4 ] ; then
  echo "USAGE: $0 <oldest_input_dir> <newest_input_dir> <parent_output_dir> <concat_name>"; exit 1
else
  OLDEST_INPUT_DIR=$1
  NEWEST_INPUT_DIR=$2
  PARENT_OUTPUT_DIR=$3
  CONCAT_NAME=$4
fi

# if the parent output dir ends with a slash, remove the slash
if [[ "$PARENT_OUTPUT_DIR" == */ ]]; then
  PARENT_OUTPUT_DIR=${PARENT_OUTPUT_DIR%/*}
fi

CONCAT_NAME_DIR=$PARENT_OUTPUT_DIR/$CONCAT_NAME

# check local folder
if [ -d "$CONCAT_NAME_DIR" ] ; then
    echo "Concat name directory already exists; exiting"; exit 1
elif [ -f "$CONCAT_NAME_DIR" ] ; then
    echo "Concat name directory already exists as a file: $CONCAT_NAME_DIR" ; exit 1
else
    echo "Creating concat name directory: $CONCAT_NAME_DIR"
    mkdir "$CONCAT_NAME_DIR"
fi

# copy everything in the newest input dir to the new concat dir
cp $NEWEST_INPUT_DIR/*.* $CONCAT_NAME_DIR

# drop _freyja_aggregated.tsv, _freyja_metadata.csv, and _sewage_seqs.csv's
# that came from from newest inputs folder
rm $CONCAT_NAME_DIR/*_freyja_aggregated.tsv
rm $CONCAT_NAME_DIR/*_freyja_metadata.csv
rm $CONCAT_NAME_DIR/*_sewage_seqs.csv

# copy _sewage_seqs.csv's from oldest inputs folder to concat name folder
cp $OLDEST_INPUT_DIR/*_sewage_seqs.csv $CONCAT_NAME_DIR

# concat all the _freyja_aggregated.tsv's in the oldest inputs folder
# (with only one header line) and write out as new _freyja_aggregated.tsv file
# into concat name folder.
# from https://stackoverflow.com/a/16890695 :
# FNR is the number of lines (records) read so far in the current file.
# NR is the number of lines read overall. So the condition
# 'FNR==1 && NR!=1{next;}' says, "Skip this line if it's the first line
# of the current file, and at least 1 line has been read overall."
# This has the effect of printing the CSV header of the first file while
# skipping it in the rest.

awk 'FNR==1 && NR!=1{next;}{print}' $OLDEST_INPUT_DIR/*_freyja_aggregated.tsv > $CONCAT_NAME_DIR/"$CONCAT_NAME"_freyja_aggregated.tsv

# concat all the _freyja_metadata.csv's in the oldest inputs folder
# (with only one header line) and write out as new _freyja_metadata.csv file
# into concat name folder
awk 'FNR==1 && NR!=1{next;}{print}' $OLDEST_INPUT_DIR/*_freyja_metadata.csv > $CONCAT_NAME_DIR/"$CONCAT_NAME"_freyja_metadata.csv
