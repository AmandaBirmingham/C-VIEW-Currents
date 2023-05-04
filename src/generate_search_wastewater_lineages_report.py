import os.path
from sys import argv
import pathlib
import pandas
import src.freyja_processing_utils as fpu

MONTH_POS = 0
DAY_POS = 1
YEAR_POS = 2
SAMPLE_ID_KEY = "sample_id"
ABUNDANCE_SUM_KEY = "abundance_sum"
DATE_KEY = "Date"


def _get_date_for_sample_id(sample_df, sample_id):
    sample_date_str = None
    if DATE_KEY in sample_df:
        sample_dates = sample_df.loc[:, DATE_KEY]
        sample_date_str = sample_dates.iloc[0]

    if not sample_date_str:
        raise ValueError(f"No date found for sample_id '{sample_id}'")
        # str_date_pieces = _extract_date_from_sampleid(sample_id)
        # sample_date_str = "/".join(str_date_pieces)

    return sample_date_str


def _generate_component_label_roll_up_values(input_df, component_label_key):
    label_groups = input_df.groupby(component_label_key)
    sum_agg = pandas.NamedAgg(column=fpu.COMPONENT_FRAC_KEY, aggfunc="sum")
    output_df = label_groups.agg(**{ABUNDANCE_SUM_KEY: sum_agg})
    return output_df


def _generate_sample_row(
        sample_date, variant_abundances_df, lineage_abundances_df):
    temp_df = pandas.concat([variant_abundances_df, lineage_abundances_df])
    temp_df[ABUNDANCE_SUM_KEY] = temp_df[ABUNDANCE_SUM_KEY] * 100
    temp_df = temp_df.round(1)
    output_df = temp_df.transpose()
    output_df.reset_index(drop=True)
    output_df.loc[:, DATE_KEY] = sample_date
    output_df.columns = [fpu.unmunge_lineage_label(x) for x in output_df.columns]
    # Drop columns for "other" lineage and variant categories, if they exist
    output_df = output_df.drop([fpu.OTHER_LABEL, fpu.OTHER_LINEAGE_LABEL],
                               axis=1, errors="ignore")
    return output_df


def generate_dashboard_report_df(
        site_labels_df, lineage_to_parent_dict, curated_lineages,
        sample_ids, previous_report_df, freyja_w_id_df, output_dir=None):

    required_cols = [DATE_KEY]
    required_cols.extend(list(site_labels_df.loc[:, fpu.ROLLUP_LABEL_KEY]))
    new_dfs_to_concat = [pandas.DataFrame(columns=required_cols)]

    sample_ids = sorted(sample_ids)
    for curr_sample_id in sample_ids:
        curr_labeled_df, sample_df = \
            fpu.explode_and_label_sample_freyja_results(
                freyja_w_id_df, curr_sample_id, SAMPLE_ID_KEY, site_labels_df,
                lineage_to_parent_dict, curated_lineages)

        if output_dir:
            curr_labeled_df.to_csv(
                f"{output_dir}/{curr_sample_id}_labeled.csv", index=False)

        curr_lineage_rollup_df = _generate_component_label_roll_up_values(
            curr_labeled_df, fpu.LINEAGE_LABEL_KEY)
        curr_variant_rollup_df = _generate_component_label_roll_up_values(
            curr_labeled_df, fpu.VARIANT_LABEL_KEY)
        curr_sample_date = _get_date_for_sample_id(sample_df, curr_sample_id)
        curr_sample_df = _generate_sample_row(
            curr_sample_date, curr_variant_rollup_df, curr_lineage_rollup_df)
        new_dfs_to_concat.append(curr_sample_df)

    new_df = pandas.concat(new_dfs_to_concat, ignore_index=True)
    new_df.reset_index(inplace=True, drop=True)

    # sort by date.  Has to be cast from string to real date to ensure
    # e.g. 7/7 sorts before 7/18
    temp_col_key = 'cast_date'
    new_df[temp_col_key] = pandas.to_datetime(new_df[DATE_KEY])
    new_df.sort_values(by=[temp_col_key], inplace=True)
    new_df.drop([temp_col_key], axis=1, errors="ignore", inplace=True)

    if previous_report_df is not None:
        # (pandas will add NaNs in any cols in old report but not this one)
        output_df = pandas.concat(
            [previous_report_df, new_df], ignore_index=True)
    else:
        output_df = new_df
    output_df.reset_index(inplace=True, drop=True)
    output_df.fillna(0, inplace=True)

    return output_df


def generate_dashboard_reports(arg_list):
    input_dir = arg_list[1]
    output_dir = arg_list[2]
    exploded_out_dir = output_dir
    if arg_list[-1] == "suppress":
        exploded_out_dir = None
        arg_list.pop(-1)
    alt_sample_id_key = None if len(arg_list) < 4 else arg_list[3]

    output_path = pathlib.Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    labels_to_aggregate_df, lineage_to_parents_dict, \
        curated_lineages, freyja_ww_df = fpu.load_inputs_from_input_dir(
            input_dir)

    # TODO: this should go away once date column names are rationalized
    freyja_ww_df.rename(
        columns={fpu.METADATA_DATE_KEY: DATE_KEY}, inplace=True)

    # Apply QC threshold to freyja results, extract and write out failed ones
    freyja_fails_fp = fpu.make_fails_fp(input_dir, output_dir)
    freyja_passing_ww_df, _ = fpu.extract_qc_failing_freyja_results(
        freyja_ww_df, freyja_fails_fp)

    # Now extract sample_id info into the df
    freyja_passing_ww_w_id_df = fpu.make_freyja_w_id_df(freyja_passing_ww_df, SAMPLE_ID_KEY)
    if alt_sample_id_key:
        freyja_passing_ww_w_id_df = _mine_metadata_from_cview_summary(
            freyja_passing_ww_w_id_df, input_dir, alt_sample_id_key)
    # endif there is an alt sample id key

    labels_fp = fpu.get_labels_fp(input_dir)
    labels_df = pandas.read_csv(labels_fp)
    output_fps = []
    for curr_location in pandas.unique(labels_df[fpu.SITE_LOCATION_KEY]):
        curr_report_fname = f"{curr_location}_sewage_seqs.csv"
        curr_prev_report_fp = f"{input_dir}/{curr_report_fname}"
        curr_output_fp = f"{output_dir}/{curr_report_fname}"

        if os.path.exists(curr_prev_report_fp):
            curr_prev_report_df = pandas.read_csv(curr_prev_report_fp)
        else:
            print(f"WARNING: No pre-existing file for '{curr_location}' "
                  f"(expecting' {curr_prev_report_fp}')")
            curr_prev_report_df = None

        output_df = _generate_dashboard_report_for_location(
            curr_location, curr_prev_report_df,
            labels_to_aggregate_df, lineage_to_parents_dict,
            freyja_passing_ww_w_id_df, curated_lineages, exploded_out_dir)
        output_df.to_csv(curr_output_fp, index=False)
        output_fps.append(curr_output_fp)
    # next location

    return output_fps


def _mine_metadata_from_cview_summary(
        freyja_ww_w_id_df, input_dir, alt_sample_id_key):
    cview_id = "sequenced_pool_component_id"
    freyja_ww_w_id_df.rename(columns={SAMPLE_ID_KEY: cview_id}, inplace=True)

    # get the cview metadata
    cview_summary_fp = fpu.get_single_file_by_suffix(
        input_dir, "_summary-report_all.csv")
    cview_summary_df = pandas.read_csv(cview_summary_fp)
    partial_cview_summary_df = \
        cview_summary_df.loc[:, [cview_id,
                                 alt_sample_id_key,
                                 fpu.METADATA_DATE_KEY]].copy()
    partial_cview_summary_df[fpu.METADATA_DATE_KEY] = \
        pandas.to_datetime(
            partial_cview_summary_df[fpu.METADATA_DATE_KEY]).dt.strftime(
            '%m/%d/%Y')

    # merge it with the freyja ww df
    freyja_ww_w_id_df = freyja_ww_w_id_df.merge(
        partial_cview_summary_df, on=cview_id,
        how="left", validate="1:1")

    # replace the default sample id with the alt sample id
    freyja_ww_w_id_df[SAMPLE_ID_KEY] = \
        freyja_ww_w_id_df[alt_sample_id_key]

    return freyja_ww_w_id_df


def _generate_dashboard_report_for_location(curr_location, curr_prev_report_df,
        labels_to_aggregate_df, lineage_to_parents_dict,
        freyja_w_id_df, curated_lineages, exploded_out_dir):

    site_labels_df, site_prefix = fpu.reformat_labels_df(
        labels_to_aggregate_df, lineage_to_parents_dict, curr_location)

    included_mask = [True] * len(freyja_w_id_df.index)  # include everything
    if site_prefix:
        included_mask = freyja_w_id_df[SAMPLE_ID_KEY].str.lstrip(
            '0123456789.').str.startswith(site_prefix, na=False)
    sample_ids = list(pandas.unique(
        freyja_w_id_df.loc[included_mask, SAMPLE_ID_KEY]))

    output_df = generate_dashboard_report_df(
        site_labels_df, lineage_to_parents_dict, curated_lineages,
        sample_ids, curr_prev_report_df, freyja_w_id_df,
        exploded_out_dir)

    return output_df


def generate_freyja_metadata(arg_list):
    temp_name_key = "temp_name"

    cview_sample_names_fp = arg_list[1]
    sample_info_fp = arg_list[2]
    output_metadata_fp = arg_list[3]

    cview_sample_names_df = pandas.read_csv(cview_sample_names_fp, header=None)
    cview_sample_names_df = cview_sample_names_df.rename(
        columns={cview_sample_names_df.columns[0]: fpu.METADATA_SAMPLE_KEY})

    temp_df = cview_sample_names_df.iloc[:, 0].str.split(
        "__", expand=True)
    cview_sample_names_df[temp_name_key] = temp_df.iloc[:, 0]

    sample_info_df = pandas.read_csv(sample_info_fp, header=None)
    sample_info_df.columns = [temp_name_key, fpu.METADATA_DATE_KEY]

    fpu.validate_length(cview_sample_names_df, "cview-style sample names",
                    sample_info_df, "sample info")
    sample_info_df = sample_info_df.merge(
        cview_sample_names_df, on=temp_name_key,
        how="outer", validate="1:1")
    fpu.validate_length(sample_info_df, "sample names/sample info merge",
                    cview_sample_names_df, "sample names list")

    # output a freyja-style metadata file
    sample_info_df[fpu.METADATA_SAMPLE_KEY] = \
        sample_info_df[fpu.METADATA_SAMPLE_KEY] + ".tsv"
    sample_info_df[fpu.METADATA_VIRAL_LOAD_KEY] = ""
    metadata_df = sample_info_df.loc[:, [fpu.METADATA_SAMPLE_KEY,
                                         fpu.METADATA_DATE_KEY,
                                         fpu.METADATA_VIRAL_LOAD_KEY]]

    metadata_df.to_csv(output_metadata_fp, index=False)


def make_freyja_metadata():
    generate_freyja_metadata(argv)


def generate_reports():
    generate_dashboard_reports(argv)


if __name__ == "__main__":
    # TODO: remove hardcoded arguments!
    arglist = ["",
               "/Users/abirmingham/Desktop/2023-03-14_22-33-14_2023-02-18_01-21-40-all_summary-report_all_sfo_ww_wastewater_highcov_wo_err_bams_none/inputs",
               "/Users/abirmingham/Desktop/2023-03-14_22-33-14_2023-02-18_01-21-40-all_summary-report_all_sfo_ww_wastewater_highcov_wo_err_bams_none/outputs",
               "sample_id"
               ]
    generate_dashboard_reports(arglist)
