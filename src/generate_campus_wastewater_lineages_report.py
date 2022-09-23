from datetime import datetime
from sys import argv
import pandas
import pathlib
import re
from src.freyja_processing_utils import make_freyja_w_id_df, validate_length,\
    get_input_fps_from_input_dir, get_freyja_results_fp, reformat_labels_df, \
    explode_and_label_sample_freyja_results, unmunge_lineage_label, \
    COMPONENT_KEY, COMPONENT_FRAC_KEY, LINEAGE_COMP_TYPE, \
    LINEAGE_LABEL_KEY, VARIANT_LABEL_KEY

SEQ_POOL_COMP_ID = "sequenced_pool_component_id"
SAMPLE_ID_KEY = "sample_id"
COLLECT_DATE_KEY = "sample_collection_datetime"
RUN_DATE_KEY = "sample_sequencing_datetime"
SEQUENCING_TECH_KEY = "sequencing_tech"
GOOGLE_SAMPLER_ID_KEY = "SamplerID"
SAMPLER_ID_KEY = "sampler_id"
GOOGLE_MANHOLE_ID_KEY = "ManholeID"
MANHOLE_ID_KEY = "manhole_id"
LINEAGE_KEY = LINEAGE_COMP_TYPE
LINEAGE_FRAC_KEY = f"{LINEAGE_KEY}_fraction"
LABELS_DATE_KEY = "labels_date"
FREYJA_DATE_KEY = "freyja_run_date"
BAM_S3_KEY = "trimmed_bam_s3"
SOURCE_KEY = "source"
RTL_SOURCE_VALUE = "RTL"
SPECIMEN_TYPE_KEY = "specimen_type"
WASTEWATER_SPECIMEN_TYPE_VAL = "wastewater"
TENX_COVG_KEY = "10_x_pc"

OUTPUT_COLS = [SEQ_POOL_COMP_ID, SAMPLE_ID_KEY, MANHOLE_ID_KEY,
               COLLECT_DATE_KEY, RUN_DATE_KEY, SEQUENCING_TECH_KEY,
               FREYJA_DATE_KEY, LABELS_DATE_KEY, LINEAGE_KEY,
               LINEAGE_FRAC_KEY, LINEAGE_LABEL_KEY, VARIANT_LABEL_KEY]


def _merge_wastewater_to_cview_summary(
        cview_summary_df, freyja_wastewater_df):

    freyja_w_id_df = make_freyja_w_id_df(
        freyja_wastewater_df, SEQ_POOL_COMP_ID)

    temp_df = freyja_w_id_df.merge(
        cview_summary_df, on=SEQ_POOL_COMP_ID, how="inner")
    validate_length(temp_df, "freyja-cview merge",
                    freyja_wastewater_df, "freyja results")

    return temp_df


def _make_wastewater_w_id_df(wastewater_df):
    # sample id is of format
    # 12.8.AS015_V2
    # where AS015 is the sampler id, which always looks like AS###
    sampler_id_regex = r".*(AS\d{3}).*"
    result_df = wastewater_df.copy()
    result_df.loc[:, SAMPLER_ID_KEY] = \
        result_df.loc[:, SAMPLE_ID_KEY].str.extract(sampler_id_regex)
    return result_df


def _merge_wastewater_to_manhole_ids(
        sampler_to_manhole_df, wastewater_df):

    wastewater_w_id_df = _make_wastewater_w_id_df(wastewater_df)
    unlabeled_mask = wastewater_w_id_df[SAMPLE_ID_KEY].str.endswith(
        "UNLABELED", na=False) | \
                     wastewater_w_id_df[SAMPLE_ID_KEY].str.endswith(
        "UNLABELLED", na=False)
    na_mask = wastewater_w_id_df[SAMPLER_ID_KEY].isna()
    mask_diff_df = unlabeled_mask.compare(na_mask)
    if len(mask_diff_df) > 0:
        raise ValueError(f"{len(mask_diff_df)} samples without recognizable "
                         f"sampler ids have a sample_id not ending in "
                         f"'UNLABELED' or 'UNLABELLED'")
    wastewater_w_id_df = wastewater_w_id_df[~unlabeled_mask]

    temp_df = wastewater_w_id_df.merge(
        sampler_to_manhole_df, left_on=SAMPLER_ID_KEY,
        right_on=GOOGLE_SAMPLER_ID_KEY, how="inner")
    validate_length(temp_df, "wastewater-manhole-info merge",
                    wastewater_w_id_df,
                    "wastewater-cview merge/unlabeled sampler drop")

    temp_df.drop(GOOGLE_SAMPLER_ID_KEY, axis=1, inplace=True)
    temp_df.rename(
        columns={GOOGLE_MANHOLE_ID_KEY: MANHOLE_ID_KEY}, inplace=True)

    return temp_df


def _make_exploded_df_w_extras(exploded_df, seq_pool_df,
                               labels_date, freyja_run_date):
    result_df = exploded_df.copy()

    # rename a couple of columns to be more informative
    result_df.rename(columns={
        COMPONENT_KEY: LINEAGE_KEY,
        COMPONENT_FRAC_KEY: LINEAGE_FRAC_KEY},
        inplace=True)

    result_df[LINEAGE_LABEL_KEY] = result_df[LINEAGE_LABEL_KEY].map(
        unmunge_lineage_label)

    result_df[LABELS_DATE_KEY] = labels_date
    result_df[FREYJA_DATE_KEY] = freyja_run_date

    col_keys_to_include = [SEQ_POOL_COMP_ID, SAMPLE_ID_KEY, COLLECT_DATE_KEY,
                           RUN_DATE_KEY, SEQUENCING_TECH_KEY, MANHOLE_ID_KEY]
    for curr_col_key in col_keys_to_include:
        # iloc[0] because there's only one row in the seq_pool_df and we
        # want the (single) value for the specified column in the first
        # (and only) row.
        result_df.loc[:, curr_col_key] = \
            seq_pool_df.loc[:, curr_col_key].iloc[0]

    return result_df


def _explode_freyja_result_for_seq_pool_comp(
        ww_plus_df, curr_seq_pool_comp_id, labels_df,
        lineage_to_parent_dict, curated_lineages,
        labels_date, freyja_run_date):
    exploded_df, seq_pool_df = explode_and_label_sample_freyja_results(
        ww_plus_df, curr_seq_pool_comp_id, SEQ_POOL_COMP_ID, labels_df,
        lineage_to_parent_dict, curated_lineages)
    result_df = _make_exploded_df_w_extras(exploded_df, seq_pool_df,
                                           labels_date, freyja_run_date)
    return result_df


def _explode_ww_results(
        ww_plus_df, labels_df, lineage_to_parent_dict, curated_lineages,
        labels_date, freyja_run_date):
    output_df = None
    seq_pool_comp_ids = list(pandas.unique(
        ww_plus_df.loc[:, SEQ_POOL_COMP_ID]))
    seq_pool_comp_ids = sorted(seq_pool_comp_ids)
    for curr_seq_pool_comp_id in seq_pool_comp_ids:
        curr_labeled_exploded_df = _explode_freyja_result_for_seq_pool_comp(
            ww_plus_df, curr_seq_pool_comp_id, labels_df,
            lineage_to_parent_dict, curated_lineages,
            labels_date, freyja_run_date)
        if output_df is None:
            output_df = curr_labeled_exploded_df
        else:
            output_df = pandas.concat([output_df, curr_labeled_exploded_df],
                                      ignore_index=True)
    # next sample_id

    return output_df


def _get_report_path(freyja_wastewater_fp, output_fp=None):
    if output_fp is None:
        ww_path = pathlib.Path(freyja_wastewater_fp)
        curr_datetime = datetime.now()
        curr_datetime_str = curr_datetime.strftime('%Y-%m-%d_%H-%M-%S')
        fname = f"{ww_path.stem}_campus_dashboard_report_" \
                f"{curr_datetime_str}.csv"

        output_fp = ww_path.parent / fname
    # end if output fp wasn't provided

    return output_fp


def _extract_date_from_filename(fp_string):
    file_path = pathlib.Path(fp_string)
    run_date_regex = r".*(20\d{2}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}).*"

    re_match = re.match(run_date_regex, file_path.stem)
    run_date_str = re_match.group(1)
    return run_date_str


def generate_dashboard_report_df(
        cview_summary_df, freyja_ww_df, manhole_id_df, labels_df,
        lineage_to_parent_dict, curated_lineages,
        labels_date, freyja_run_date):

    temp_df = _merge_wastewater_to_cview_summary(
        cview_summary_df, freyja_ww_df)
    temp_2_df = _merge_wastewater_to_manhole_ids(manhole_id_df, temp_df)
    output_df = _explode_ww_results(
        temp_2_df, labels_df, lineage_to_parent_dict, curated_lineages,
        labels_date, freyja_run_date)

    return output_df


def generate_dashboard_report(arg_list):
    # TODO: this may be temporary ... might add code to pull this straight
    #  from the google sheet
    labels_fp = arg_list[1]
    sampler_to_manhole_fp = arg_list[2]
    cview_summary_fp = arg_list[3]
    freyja_input_dir = arg_list[4]
    output_fp = arg_list[5] if len(arg_list) > 5 else None

    labels_date = _extract_date_from_filename(labels_fp)
    freyja_results_fp = get_freyja_results_fp(freyja_input_dir)
    freyja_run_date = _extract_date_from_filename(freyja_results_fp)

    cview_summary_df = pandas.read_csv(cview_summary_fp)
    manhole_id_df = pandas.read_csv(
        sampler_to_manhole_fp, skiprows=2,
        usecols=lambda x: x in [GOOGLE_SAMPLER_ID_KEY, GOOGLE_MANHOLE_ID_KEY])

    labels_to_aggregate_df, lineage_to_parent_dict, \
    curated_lineages, freyja_ww_df = get_input_fps_from_input_dir(
        labels_fp, freyja_input_dir)

    search_labels_df, _ = reformat_labels_df(
        labels_to_aggregate_df, lineage_to_parent_dict, "PointLoma")

    output_df = generate_dashboard_report_df(
        cview_summary_df, freyja_ww_df, manhole_id_df, search_labels_df,
        lineage_to_parent_dict, curated_lineages, labels_date, freyja_run_date)

    output_fp = _get_report_path(freyja_results_fp, output_fp)
    output_df.to_csv(output_fp, columns=OUTPUT_COLS, index=False)
    return output_fp


def extract_bam_urls(args_list):
    output_suffix = "_rtl_wastewater_highcov_s3_urls.txt"

    # ignore args_list[1]--that's just "bamurls"
    cview_summary_fp = args_list[2]
    output_dir = None if len(args_list) <= 3 else args_list[3]

    # NB: expects a *-all_summary-report_all.csv cview file
    cview_summary_df = pandas.read_csv(cview_summary_fp)
    rtl_mask = cview_summary_df[SOURCE_KEY] == RTL_SOURCE_VALUE
    wastewater_mask = \
        cview_summary_df[SPECIMEN_TYPE_KEY] == WASTEWATER_SPECIMEN_TYPE_VAL
    gte_60pct_10x_coverage_mask = cview_summary_df[TENX_COVG_KEY] >= 60
    rtl_wastewater_highcov_mask = rtl_mask & wastewater_mask & \
                                  gte_60pct_10x_coverage_mask

    relevant_bam_urls = \
        cview_summary_df.loc[rtl_wastewater_highcov_mask, BAM_S3_KEY]

    if output_dir:
        output_dir_path = pathlib.Path(output_dir)
        cview_summary_path = pathlib.Path(cview_summary_fp)
        output_fname = cview_summary_path.stem + output_suffix
        output_fp = output_dir_path / output_fname
    else:
        output_fp = cview_summary_fp.replace(".csv", output_suffix)
    relevant_bam_urls.sort_values(inplace=True)
    relevant_bam_urls.to_csv(output_fp, index=False, header=False)
    return output_fp


if __name__ == '__main__':
    if argv[1] == "bamurls":
        extract_bam_urls(argv)
    else:
        generate_dashboard_report(argv)
