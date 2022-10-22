from sys import argv
import pandas
import pathlib
import urllib.request
import glob
import yaml
import json
import os

VARIANTS_LIST_KEY = "summarized"
LINEAGES_LIST_KEY = "lineages"
ABUNDANCES_LIST_KEY = "abundances"
COVERAGE_KEY = "coverage"
MIN_ACCEPTABLE_COVERAGE = 60
FREYJA_FNAME_KEY = "Unnamed: 0"
FREYJA_RESULTS_FNAME_SUFFIX = "_freyja_aggregated.tsv"
COMPONENT_KEY = "component"
COMPONENT_FRAC_KEY = "component_fraction"
COMPONENT_TYPE_KEY = "component_type"
VARIANT_COMP_TYPE = "variant"
LINEAGE_COMP_TYPE = "lineage"
LINEAGE_YML_URL = "https://raw.githubusercontent.com/cov-lineages/lineages-website/master/data/lineages.yml"
LINEAGE_LABEL_DELIMITER = "."
LINEAGE_LABEL_WILDCARD = "X"
SITE_LOCATION_KEY = "site_location"
SITE_PREFIX_KEY = "site_prefix"
LINEAGE_LABEL_KEY = "lineage_label"
VARIANT_LABEL_KEY = "variant_label"
OTHER_LABEL = "Other"
OTHER_LINEAGE_LABEL = "Other lineage"
ROLLUP_LABEL_KEY = "rollup_label"
MUNGED_LINEAGE_LABEL_KEY = "munged_lineage_label"
DEALIASED_MUNGED_LINEAGE_LABEL_KEY = "dealiased_munged_lineage_label"
METADATA_SAMPLE_KEY = "Sample"
METADATA_DATE_KEY = "sample_collection_datetime"
METADATA_VIRAL_LOAD_KEY = "viral_load"


def _munge_lineage_label(a_label):
    result = a_label
    if a_label.endswith(f"{LINEAGE_LABEL_DELIMITER}{LINEAGE_LABEL_WILDCARD}"):
        result = a_label.removesuffix(LINEAGE_LABEL_WILDCARD)
    return result


def _get_lineage_to_parents_dict(lineage_file):
    # Below code borrowed from Andersen lab outbreak-info at
    # https://github.com/outbreak-info/outbreak.info/blob/c068d139e18fc16370ba14f72dd5595c5122b35a/curated_reports_prep/generate_curated_lineages_json.py#L110-L115
    lineages = yaml.load(lineage_file, Loader=yaml.BaseLoader)
    lineage_to_parent_dict = {}
    for lineage in lineages:
        lineage_to_parent_dict[lineage["name"]] = lineage.get("parent")

    return lineage_to_parent_dict


def _explode_variants(seq_pool_df):
    variants_series = seq_pool_df.loc[:, VARIANTS_LIST_KEY]
    validate_length(variants_series, VARIANTS_LIST_KEY, [1])

    # this is a list of tuples of (var_name, var_abundance) produced by
    # evaluating a string of the form
    # "[('BA.2* [Omicron (BA.2.X)]', 0.49641195397196025), ('Omicron', 0.46685900090836957), ('Other', 0.0067319954584884175)]"  # noqa E501
    variants_tuple_list = eval(variants_series.iloc[0])
    # this is a 2-item list containing parallel lists: the first is
    # variant names, the second is variant abundances
    variant_and_abundance_lists = list(map(list, (zip(*variants_tuple_list))))

    output_df = pandas.DataFrame(
        {COMPONENT_KEY: variant_and_abundance_lists[0],
         COMPONENT_FRAC_KEY: variant_and_abundance_lists[1]})
    output_df[COMPONENT_TYPE_KEY] = VARIANT_COMP_TYPE
    return output_df


def _explode_lineages(seq_pool_df):
    # the lineages value has the form
    # "BA.2.12.1 BA.2.12 BA.5.1 BA.5.2.1 BA.4 BA.4.1 BA.5.5 BA.5.2 BA.2.38 BA.2.16 BA.5.3.1 BE.1 BA.2.56 BF.1 BG.2 XAD BA.2.36 BA.2.65 BA.2.58 BA.2.13 miscBA2BA1PostSpike BA.2.11 BA.2.63 BA.2.53 BA.2.3.16 BA.2.50 BA.2.59 XQ BG.1 BA.2.19 BA.4.1.1 BA.2.48 BA.2.52 BA.2.70 BA.2.29 BA.2.72 BA.2.9.2 BA.2.10.3 BA.2.44 BA.2.71 BA.2.20 BA.2.31 BA.2.9.1 XZ BA.2.18 XY BA.2.22 BA.2.62 BA.5.3.2 BA.2.26 BA.2.61 BA.2.8 proposed757 BA.2.27 BA.2.25.1 BA.2.10.1 BA.2.3.7" # noqa E501
    # the abundances value has the form
    # "0.21823342 0.11696584 0.09523810 0.09436590 0.07060140 0.05007211 0.03996610 0.03476859 0.02966765 0.02391699 0.02351210 0.01724930 0.01116309 0.01028510 0.00901632 0.00835987 0.00813625 0.00787049 0.00782773 0.00652733 0.00541020 0.00528737 0.00458439 0.00410290 0.00377330 0.00348668 0.00341615 0.00306484 0.00268751 0.00262608 0.00255949 0.00225742 0.00220213 0.00219436 0.00206107 0.00202581 0.00199670 0.00199578 0.00196223 0.00189474 0.00189434 0.00186916 0.00183360 0.00179924 0.00179745 0.00168437 0.00167778 0.00166347 0.00162866 0.00161987 0.00156593 0.00135783 0.00132180 0.00128932 0.00126574 0.00126024 0.00114131"  # noqa E501

    lineages_series = seq_pool_df.loc[:, LINEAGES_LIST_KEY]
    validate_length(lineages_series, LINEAGES_LIST_KEY, [1])
    # default split is on whitespace
    lineages_list = lineages_series.iloc[0].split()

    abundances_series = seq_pool_df.loc[:, ABUNDANCES_LIST_KEY]
    validate_length(abundances_series, ABUNDANCES_LIST_KEY, [1])
    str_abundances_list = abundances_series.iloc[0].split()
    abundances_list = [float(x) for x in str_abundances_list]

    validate_length(abundances_list, ABUNDANCES_LIST_KEY,
                    lineages_list, LINEAGES_LIST_KEY)

    output_df = pandas.DataFrame(
        {COMPONENT_KEY: lineages_list,
         COMPONENT_FRAC_KEY: abundances_list})
    output_df[COMPONENT_TYPE_KEY] = LINEAGE_COMP_TYPE
    return output_df


def _get_lineage_from_alias(an_alias, lineage_to_parent_dict):
    alias_pieces = an_alias.split(LINEAGE_LABEL_DELIMITER)
    lineage_suffix = alias_pieces[-1]
    if len(alias_pieces) == 1:
        # NB: stopping when at something with no dots, even if that thing might
        # have a parent--e.g., stopping when an_alias is B, even though B
        # technically has a parent (which is A)
        return an_alias

    if an_alias in lineage_to_parent_dict:
        alias_parent = lineage_to_parent_dict.get(an_alias)
        if not alias_parent:
            return an_alias
    else:  # if not in lineage_to_parent_dict
        alias_parent = LINEAGE_LABEL_DELIMITER.join(alias_pieces[:-1])
    # end if alias is/is not in lineage_to_parent_dict

    parent_lineage = _get_lineage_from_alias(
        alias_parent, lineage_to_parent_dict)
    a_lineage = LINEAGE_LABEL_DELIMITER.join([parent_lineage, lineage_suffix])
    return a_lineage


def _identify_label_for_lineage(a_lineage, lineage_to_label_dict, other_label):
    labelled_lineages = lineage_to_label_dict.keys()

    # this handles cases like:
    # BA.1.1 was input and should match BA.1.1 or
    # BA.5. was input and should match BA.5.
    # (this second case only happens when called recursively)
    if a_lineage in labelled_lineages:
        return lineage_to_label_dict[a_lineage]

    # this handles the case where e.g. BA.5 was input and should match to
    # labelled lineage BA.5. (i.e. BA.5.X)
    a_lineage_dot = a_lineage + "."
    if a_lineage_dot in labelled_lineages:
        return lineage_to_label_dict[a_lineage_dot]

    # this handles cases like BA or (from a recursive call) BA.
    a_lineage_wo_dot = a_lineage.rstrip(".")
    label_pieces = a_lineage_wo_dot.split(LINEAGE_LABEL_DELIMITER)
    if len(label_pieces) < 2:
        return other_label

    # if input was e.g. BA.5.2.1 and no match to it was found,
    # recurse to look for a match to BA.5.2. (i.e. BA.5.2.X)
    truncated_lineage = LINEAGE_LABEL_DELIMITER.join(label_pieces[:-1]) + LINEAGE_LABEL_DELIMITER
    return _identify_label_for_lineage(
        truncated_lineage, lineage_to_label_dict, other_label)


def _identify_label_for_aliased_lineage(
        a_lineage, lineage_to_label_dict, lineage_to_parents_dict,
        other_label=OTHER_LINEAGE_LABEL):
    mapped_label = _identify_label_for_lineage(
        a_lineage, lineage_to_label_dict, other_label)

    if mapped_label == other_label:
        dealiased_lineage = _get_lineage_from_alias(
            a_lineage, lineage_to_parents_dict)
        mapped_label = _identify_label_for_lineage(
            dealiased_lineage, lineage_to_label_dict, other_label)

    return mapped_label


def _make_lineage_labels_dict(allowed_labels_df):
    allowed_alias_labels = list(
        allowed_labels_df.loc[:, MUNGED_LINEAGE_LABEL_KEY])
    allowed_alias_dict = dict(zip(allowed_alias_labels, allowed_alias_labels))

    allowed_dealiased_labels = list(
        allowed_labels_df.loc[:, DEALIASED_MUNGED_LINEAGE_LABEL_KEY])
    dealiased_to_aliased_dict = dict(
        zip(allowed_dealiased_labels, allowed_alias_labels))

    # merge dictionaries
    result = allowed_alias_dict | dealiased_to_aliased_dict
    return result


def _make_variant_labels_dict(allowed_labels_df, curated_lineages):
    variants_mask = allowed_labels_df[COMPONENT_TYPE_KEY] == VARIANT_COMP_TYPE
    variants_of_interest = list(
        allowed_labels_df.loc[variants_mask, ROLLUP_LABEL_KEY])

    found_variants = []
    lineage_to_variant_dict = {}
    for curr_curated_lin in curated_lineages:
        curr_who_name = curr_curated_lin.get("who_name")
        if curr_who_name:
            if curr_who_name in variants_of_interest:
                found_variants.append(curr_who_name)
                pango_descendants = curr_curated_lin["pango_descendants"]
                for curr_descendant in pango_descendants:
                    if curr_descendant in lineage_to_variant_dict:
                        raise ValueError(
                            f"The lineage '{curr_descendant}' is assigned to "
                            f"lineage '{curr_who_name}' and lineage "
                            f"'{lineage_to_variant_dict[curr_descendant]}'")
                    lineage_to_variant_dict[curr_descendant] = curr_who_name

    if set(variants_of_interest) != set(found_variants):
        raise ValueError("Not all variants of interest found in "
                         "curated lineages")

    return lineage_to_variant_dict


def _map_lineage_and_variant_labels(
        exploded_df, allowed_labels_df,
        lineage_to_parents_dict, curated_lineages):

    lineage_to_label_dict = _make_lineage_labels_dict(allowed_labels_df)
    lineage_to_variant_dict = _make_variant_labels_dict(
        allowed_labels_df, curated_lineages)

    def _map_lineage_label(a_lineage):
        return _identify_label_for_aliased_lineage(
            a_lineage, lineage_to_label_dict, lineage_to_parents_dict)

    def _map_variant_label(a_lineage):
        return _identify_label_for_aliased_lineage(
            a_lineage, lineage_to_variant_dict, lineage_to_parents_dict,
            other_label=OTHER_LABEL)

    lineages_mask = exploded_df[COMPONENT_TYPE_KEY] == LINEAGE_COMP_TYPE
    temp_df = exploded_df.loc[lineages_mask, :].copy()
    temp_df.reset_index(drop=True)

    lineages_series = temp_df.loc[:, COMPONENT_KEY]
    temp_df.loc[:, LINEAGE_LABEL_KEY] = lineages_series.map(_map_lineage_label)
    temp_df.loc[:, VARIANT_LABEL_KEY] = lineages_series.map(_map_variant_label)
    return temp_df


def _get_single_file_by_suffix(input_dir, suffix, require_file=True):
    result = None
    found_fps = glob.glob(f"{input_dir}/*{suffix}")
    if require_file:
        validate_length(found_fps, f"'<wildcard>{suffix}' glob", [1])
    if len(found_fps) > 0:
        result = found_fps[0]
    return result


def _get_freyja_metadata_fp(input_dir, require_metadata):
    return _get_single_file_by_suffix(
        input_dir, "_freyja_metadata.csv", require_file=require_metadata)


def _load_and_merge_freyja_results_and_metadata(
        input_dir, require_metadata=False):
    freyja_raw_results_fp = get_freyja_results_fp(input_dir)
    metadata_fp = _get_freyja_metadata_fp(
        input_dir, require_metadata=require_metadata)

    freyja_raw_results_df = pandas.read_csv(freyja_raw_results_fp, sep="\t")
    freyja_results_df = freyja_raw_results_df
    if metadata_fp is not None:
        metadata_df = pandas.read_csv(metadata_fp)
        validate_length(freyja_raw_results_df, "raw freyja results",
                        metadata_df, "freyja metadata")

        freyja_w_dates_df = freyja_raw_results_df.merge(
            metadata_df, left_on=FREYJA_FNAME_KEY,
            right_on=METADATA_SAMPLE_KEY, how="outer")
        validate_length(freyja_w_dates_df, "freyja results/metadata merge",
                        freyja_raw_results_df, "raw freyja results")
        # remove the duplicate sample name column
        freyja_w_dates_df.pop(METADATA_SAMPLE_KEY)

        freyja_results_df = freyja_w_dates_df

    return freyja_results_df


def unmunge_lineage_label(a_label):
    result = a_label
    if a_label.endswith(LINEAGE_LABEL_DELIMITER):
        result = a_label + LINEAGE_LABEL_WILDCARD
    return result


def reformat_labels_df(
        dashboard_labels_df, lineage_to_parent_dict, site_location):
    def _get_lineage(a_label):
        dealiased_label = _get_lineage_from_alias(a_label, lineage_to_parent_dict)
        return _munge_lineage_label(dealiased_label)

    site_mask = dashboard_labels_df[SITE_LOCATION_KEY].str.startswith(
        site_location, na=False)
    site_prefixes = pandas.unique(
        dashboard_labels_df.loc[site_mask, SITE_PREFIX_KEY])
    validate_length(site_prefixes, f"site prefixes for '{site_location}'", [1])

    result_df = dashboard_labels_df.loc[site_mask, :].copy()
    labels_series = result_df.loc[:, ROLLUP_LABEL_KEY]
    result_df[MUNGED_LINEAGE_LABEL_KEY] = labels_series.map(_munge_lineage_label)
    result_df[DEALIASED_MUNGED_LINEAGE_LABEL_KEY] = labels_series.map(
        _get_lineage)

    return result_df, site_prefixes[0]


def make_freyja_w_id_df(freyja_wastewater_df, sample_id_key):
    # The freyja output file name (e.g.
    # "SEARCH-17735__D103692__H16__210213_A00953_0232_BHY3GLDRXX__001002.tsv")
    # is in the first column of the freyja aggregate results, and this column
    # is unnamed.
    # NB: As of 06/29/2022, R. Knight affirms that the campus wastewater
    # dashboard's sequencing-based lineage data (as opposed to ddPCR-based)
    # will ONLY come from samples sequenced through IGM (not e.g. Genexus) so
    # it is legitimate to expect that the name of the freyja output file will
    # always be the sequenced pool component id + ".tsv".
    stem_regex = r"(.*)\..*"
    result_df = freyja_wastewater_df.copy()
    result_df.loc[:, sample_id_key] = \
        result_df.loc[:, FREYJA_FNAME_KEY].str.extract(stem_regex)

    result_df.drop(FREYJA_FNAME_KEY, axis=1, inplace=True)
    return result_df


def validate_length(found, found_source, expected, expected_source=None):
    expected_len = len(expected)
    found_len = len(found)
    if expected_len != found_len:
        expected_str = f" per {expected_source}" if expected_source else ""
        raise ValueError(f"Found {found_len} records in {found_source} "
                         f"but expected {expected_len}{expected_str}")


def explode_sample_freyja_results(freyja_results_w_id_df,
                                  sample_id, sample_id_key,
                                  explode_variants=False):
    sample_mask = freyja_results_w_id_df.loc[:, sample_id_key] == \
                         sample_id
    sample_df = freyja_results_w_id_df.loc[sample_mask, :].copy()
    validate_length(sample_df, f"{sample_id_key} dataframe", [1])

    lineages_df = _explode_lineages(sample_df)
    to_concat = [lineages_df]
    if explode_variants:
        variants_df = _explode_variants(sample_df)
        to_concat.append(variants_df)

    exploded_df = pandas.concat(to_concat, ignore_index=True)

    return exploded_df, sample_df


def explode_and_label_sample_freyja_results(
        freyja_w_id_df, curr_sample_id, sample_id_key, labels_df,
        lineage_to_parent_dict, curated_lineages, explode_variants=False):

    curr_exploded_df, sample_df = explode_sample_freyja_results(
        freyja_w_id_df, curr_sample_id, sample_id_key, explode_variants)

    curr_labeled_df = _map_lineage_and_variant_labels(
        curr_exploded_df, labels_df,
        lineage_to_parent_dict, curated_lineages)

    return curr_labeled_df, sample_df


def get_freyja_results_fp(input_dir):
    return _get_single_file_by_suffix(input_dir, FREYJA_RESULTS_FNAME_SUFFIX)


def load_inputs_from_input_dir(labels_to_aggregate_fp, input_dir,
                               require_metadata=False):
    lineages_yaml_fp = f"{input_dir}/lineages.yml"
    curated_lineages_json_fp = f"{input_dir}/curated_lineages.json"

    labels_to_aggregate_df = pandas.read_csv(labels_to_aggregate_fp)
    with open(lineages_yaml_fp) as lineages_fh:
        lineage_to_parents_dict = _get_lineage_to_parents_dict(lineages_fh)

    with open(curated_lineages_json_fp) as json_fh:
        curated_lineages = json.load(json_fh)
    freyja_ww_df = _load_and_merge_freyja_results_and_metadata(
        input_dir, require_metadata=require_metadata)

    return (labels_to_aggregate_df, lineage_to_parents_dict,
            curated_lineages, freyja_ww_df)


def extract_qc_failing_freyja_results(freyja_results_df, fails_fp=None):
    qc_fails_mask = freyja_results_df[COVERAGE_KEY] < MIN_ACCEPTABLE_COVERAGE
    qc_fails_indices = freyja_results_df[qc_fails_mask].index
    # get failing records
    qc_fails_df = freyja_results_df.loc[qc_fails_indices, :]
    # now actually drop any failing records
    freyja_results_df.drop(qc_fails_indices, inplace=True)

    if fails_fp is not None:
        qc_fails_df.to_csv(fails_fp, sep="\t", index=False)

    return freyja_results_df, qc_fails_df


def get_ref_dir():
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.join(curr_dir, os.pardir)
    ref_dir = os.path.abspath(os.path.join(parent_dir, "reference_files"))
    return ref_dir


def download_inputs(summary_s3_url, output_dir, urls_fp=None):
    def _add_end_backslash(a_str):
        if not a_str.endswith("/"):
            a_str = a_str + "/"
        return a_str

    curated_json_fname = "curated_lineages.json"
    summary_s3_url = _add_end_backslash(summary_s3_url)
    output_dir = _add_end_backslash(output_dir)
    output_path = pathlib.Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # download all the urls in the input file, if there is one
    urls = []
    if urls_fp:
        with open(urls_fp) as urls_fh:
            # make sure to remove linebreaks ...
            urls = [x.strip() for x in urls_fh.readlines()]

    urls.append(LINEAGE_YML_URL)
    for curr_url in urls:
        curr_filename = pathlib.Path(curr_url).name
        curr_local_fp = output_path / curr_filename
        urllib.request.urlretrieve(curr_url, curr_local_fp)

    # download the freyja result(s) and the curated_lineages.json from
    # the specified run on S3.
    # I am doing this via a shell command rather than boto3 because I
    # don't want to code my AWS credentials into this script and I have already
    # run aws cli's config on my machine to store my credentials there
    summary_name = pathlib.Path(summary_s3_url).name
    curated_json_s3_url = summary_s3_url.replace(summary_name+"/", curated_json_fname)
    curated_json_local_fp = output_path / curated_json_fname
    cmd1 = f"aws s3 cp {curated_json_s3_url} {curated_json_local_fp}"
    cmd2 = f"aws s3 cp {summary_s3_url} {output_dir} --recursive " \
           f"--exclude \"*\" --include \"*{FREYJA_RESULTS_FNAME_SUFFIX}\""

    import subprocess
    subprocess.run(cmd1, shell=True)
    subprocess.run(cmd2, shell=True)


def freyja_download():
    summary_s3_url = argv[0]
    output_dir = argv[1]
    if len(argv) == 3:
        urls_fp = argv[2]
    else:
        ref_dir = get_ref_dir()
        urls_fp = os.join(ref_dir, "inputs_url.txt")

    download_inputs(summary_s3_url, output_dir, urls_fp)
