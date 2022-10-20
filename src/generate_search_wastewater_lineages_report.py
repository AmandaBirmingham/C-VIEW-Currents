from sys import argv
import pathlib
import pandas
from src.freyja_processing_utils import make_freyja_w_id_df, \
    explode_and_label_sample_freyja_results, load_inputs_from_input_dir, \
    unmunge_lineage_label, reformat_labels_df, get_ref_dir, \
    SITE_LOCATION_KEY, ROLLUP_LABEL_KEY, OTHER_LABEL, OTHER_LINEAGE_LABEL, \
    LINEAGE_LABEL_KEY, VARIANT_LABEL_KEY, COMPONENT_FRAC_KEY

MONTH_POS = 0
DAY_POS = 1
YEAR_POS = 2
SAMPLE_ID_KEY = "sample_id"
ABUNDANCE_SUM_KEY = "abundance_sum"
DATE_KEY = "Date"


def _extract_date_from_sampleid(sample_id):
    name_split = sample_id.split(".")

    str_date_pieces = name_split[0:3]  # slice end is exclusive
    try:
        [int(x) for x in str_date_pieces]
    except ValueError:
        raise ValueError(f"Invalid/unrecognized date in sample id "
                         f"'{sample_id}'")
    return str_date_pieces


def _get_date_for_sample_id(sample_df, sample_id):
    sample_date_str = None
    if DATE_KEY in sample_df:
        sample_dates = sample_df.loc[:, DATE_KEY]
        sample_date_str = sample_dates.iloc[0]

    if not sample_date_str:
        str_date_pieces = _extract_date_from_sampleid(sample_id)
        sample_date_str = "/".join(str_date_pieces)

    return sample_date_str

    # import datetime
    # if len(str_date_pieces[YEAR_POS]) == 2:
    #     str_date_pieces[YEAR_POS] = f"20{str_date_pieces[YEAR_POS]}"
    # date_pieces = [int(x) for x in str_date_pieces]
    #
    # sample_date = datetime.date(
    #     date_pieces[YEAR_POS], date_pieces[MONTH_POS], date_pieces[DAY_POS])
    #
    # return sample_date


def _generate_component_label_roll_up_values(input_df, component_label_key):
    label_groups = input_df.groupby(component_label_key)
    sum_agg = pandas.NamedAgg(column=COMPONENT_FRAC_KEY, aggfunc="sum")
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
    output_df.columns = [unmunge_lineage_label(x) for x in output_df.columns]
    # Drop columns for "other" lineage and variant categories, if they exist
    output_df = output_df.drop([OTHER_LABEL, OTHER_LINEAGE_LABEL],
                               axis=1, errors="ignore")
    return output_df


def generate_dashboard_report_df(
        dashboard_labels_df, lineage_to_parent_dict, curated_lineages,
        report_location, previous_report_df, freyja_ww_df, output_dir=None):

    freyja_w_id_df = make_freyja_w_id_df(freyja_ww_df, SAMPLE_ID_KEY)
    site_labels_df, site_prefix = reformat_labels_df(
        dashboard_labels_df, lineage_to_parent_dict, report_location)

    required_cols = [DATE_KEY]
    required_cols.extend(list(site_labels_df.loc[:, ROLLUP_LABEL_KEY]))
    new_dfs_to_concat = [pandas.DataFrame(columns=required_cols)]

    site_prefix_mask = freyja_w_id_df[SAMPLE_ID_KEY].str.lstrip(
        '0123456789.').str.startswith(site_prefix, na=False)
    sample_ids = list(pandas.unique(
        freyja_w_id_df.loc[site_prefix_mask, SAMPLE_ID_KEY]))
    sample_ids = sorted(sample_ids)
    for curr_sample_id in sample_ids:
        curr_labeled_df, sample_df = explode_and_label_sample_freyja_results(
            freyja_w_id_df, curr_sample_id, SAMPLE_ID_KEY, site_labels_df,
            lineage_to_parent_dict, curated_lineages)

        if output_dir:
            curr_labeled_df.to_csv(
                f"{output_dir}/{curr_sample_id}_labeled.csv", index=False)

        curr_lineage_rollup_df = _generate_component_label_roll_up_values(
            curr_labeled_df, LINEAGE_LABEL_KEY)
        curr_variant_rollup_df = _generate_component_label_roll_up_values(
            curr_labeled_df, VARIANT_LABEL_KEY)
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

    # (pandas will add NaNs in any cols in old report but not this one)
    output_df = pandas.concat([previous_report_df, new_df], ignore_index=True)
    output_df.reset_index(inplace=True, drop=True)
    output_df.fillna(0, inplace=True)

    return output_df


def generate_dashboard_reports(arg_list):
    input_dir = arg_list[0]
    output_dir = arg_list[1]
    if len(arg_list) > 2:
        labels_fp = arg_list[2]
    else:
        ref_dir = get_ref_dir()
        labels_fp = _get_latest_file(ref_dir, "sewage_seq_labels_")

    exploded_out_dir = output_dir
    if arg_list[-1] == "suppress":
        exploded_out_dir = None

    output_path = pathlib.Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    labels_to_aggregate_df, lineage_to_parents_dict, \
    curated_lineages, freyja_ww_df = load_inputs_from_input_dir(
        labels_fp, input_dir)

    labels_df = pandas.read_csv(labels_fp)
    output_fps = []
    for curr_location in pandas.unique(labels_df[SITE_LOCATION_KEY]):
        curr_report_fname = f"{curr_location}_sewage_seqs.csv"
        curr_prev_report_fp = f"{input_dir}/{curr_report_fname}"
        curr_output_fp = f"{output_dir}/{curr_report_fname}"

        curr_prev_report_df = pandas.read_csv(curr_prev_report_fp)
        previous_report_fstem = pathlib.PurePath(curr_prev_report_fp).stem
        report_location = previous_report_fstem.split("_")[0]

        output_df = generate_dashboard_report_df(
            labels_to_aggregate_df, lineage_to_parents_dict, curated_lineages,
            report_location, curr_prev_report_df, freyja_ww_df,
            exploded_out_dir)
        output_df.to_csv(curr_output_fp, index=False)
        output_fps.append(curr_output_fp)
    # next location

    return output_fps


def _get_latest_file(dir_path, filename_root=""):
    dir_path_obj = pathlib.Path(dir_path)
    latest_fp = None
    relevant_fps = list(dir_path_obj.glob(f"*{filename_root}*"))
    if len(relevant_fps) > 0:
        latest_fp = max(relevant_fps,
                        key=lambda item: item.stat().st_ctime)
    return latest_fp


def main():
    generate_dashboard_reports(argv)


if __name__ == '__main__':
    main()

