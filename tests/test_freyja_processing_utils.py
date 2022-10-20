import pandas
from io import StringIO
from tests.filetestcase import FileTestCase
from src.freyja_processing_utils import _munge_lineage_label,\
    _get_lineage_to_parents_dict, _get_lineage_from_alias, \
    _identify_label_for_lineage, _identify_label_for_aliased_lineage, \
    _make_lineage_labels_dict, _make_variant_labels_dict,\
    unmunge_lineage_label, reformat_labels_df, make_freyja_w_id_df, \
    validate_length, explode_sample_freyja_results, \
    explode_and_label_sample_freyja_results, get_freyja_results_fp, \
    load_inputs_from_input_dir, get_ref_dir, OTHER_LINEAGE_LABEL


class FreyjaProcessingUtilsTest(FileTestCase):
    freyja_dict = {
        "Unnamed: 0": [
            "SEARCH-91626__E0003116__M08__220527_A01535_0137_BHY5VWDSX3__002.tsv",
            "SEARCH-91606__E0003116__I07__220527_A01535_0137_BHY5VWDSX3__002.txt"],
        "summarized": [
            "[('BA.2* [Omicron (BA.2.X)]', 0.49641195397196025), ('Omicron', 0.46685900090836957), ('Other', 0.0067319954584884175)]",
            "[('Omicron', 0.49991486113136663), ('BA.2* [Omicron (BA.2.X)]', 0.4556013287335106), ('Other', 0.01207076124116462)]"],
        "lineages": [
            "BA.2.12.1 BA.2.12 BA.5.1 BA.5.2.1 BA.4 BA.4.1 BA.5.5 BA.5.2 BA.2.38 BA.2.16 BA.5.3.1 BE.1 BA.2.56 BF.1 BG.2 XAD BA.2.36 BA.2.65 BA.2.58 BA.2.13 miscBA2BA1PostSpike BA.2.11 BA.2.63 BA.2.53 BA.2.3.16 BA.2.50 BA.2.59 XQ BG.1 BA.2.19 BA.4.1.1 BA.2.48 BA.2.52 BA.2.70 BA.2.29 BA.2.72 BA.2.9.2 BA.2.10.3 BA.2.44 BA.2.71 BA.2.20 BA.2.31 BA.2.9.1 XZ BA.2.18 XY BA.2.22 BA.2.62 BA.5.3.2 BA.2.26 BA.2.61 BA.2.8 proposed757 BA.2.27 BA.2.25.1 BA.2.10.1 BA.2.3.7",
            "BA.2.12 BA.5.2 BA.4.1 BA.2.12.1 BA.5.1 BA.5.2.1 BA.5.5 BA.2.65 BA.4 BE.1 BG.2 BA.5.3.1 BA.2.3.5 miscBA2BA1PostSpike XAD BA.2.56 BA.2.3 BA.2.3.4 BG.1 BA.2.67 BA.2.61 BA.2.17 BA.2.22 BA.2.11 BA.2.42 BA.2.59 BA.2.10 BA.2.16 BA.2.27 BA.2.57 BA.2.52 BA.2.68 BA.2.72 BF.1 BA.4.1.1 BA.2.66 BA.2.8 BA.2.13 BA.1.1.5 XQ BA.2.71 BA.2.29 BA.2.3.16 BA.2.31 BA.2.53 BA.2.45 BA.2.70 BA.2.3.12 BA.5.3.2 BA.2.48 BA.2.19 BA.2.28 proposed590 BA.2.37 BA.2.40 BA.2.73"],
        "abundances": [
            "0.21823342 0.11696584 0.09523810 0.09436590 0.07060140 0.05007211 0.03996610 0.03476859 0.02966765 0.02391699 0.02351210 0.01724930 0.01116309 0.01028510 0.00901632 0.00835987 0.00813625 0.00787049 0.00782773 0.00652733 0.00541020 0.00528737 0.00458439 0.00410290 0.00377330 0.00348668 0.00341615 0.00306484 0.00268751 0.00262608 0.00255949 0.00225742 0.00220213 0.00219436 0.00206107 0.00202581 0.00199670 0.00199578 0.00196223 0.00189474 0.00189434 0.00186916 0.00183360 0.00179924 0.00179745 0.00168437 0.00167778 0.00166347 0.00162866 0.00161987 0.00156593 0.00135783 0.00132180 0.00128932 0.00126574 0.00126024 0.00114131",
            "0.21069000 0.12159864 0.11619024 0.10317434 0.05307850 0.05039021 0.04800864 0.03985987 0.03430699 0.02209150 0.01651844 0.01476350 0.01415340 0.01100568 0.00906176 0.00704470 0.00647347 0.00460503 0.00445935 0.00430377 0.00416445 0.00384183 0.00383441 0.00373471 0.00346779 0.00302982 0.00281367 0.00279720 0.00263366 0.00259605 0.00256129 0.00243105 0.00235849 0.00228919 0.00205717 0.00202122 0.00194230 0.00193510 0.00191316 0.00189274 0.00184190 0.00180144 0.00170077 0.00170068 0.00143396 0.00137958 0.00135124 0.00130661 0.00129484 0.00118534 0.00117706 0.00113843 0.00106508 0.00104502 0.00103862 0.00103306"]
    }

    lineage_to_parent_dict = {'A': None,
                              'B': 'A',
                              'B.1': 'B',
                              'B.1.529': 'B.1',
                              'BA.2': 'B.1.1.529',
                              'BA.5': 'B.1.1.529',
                              'BA.5.2': 'BA.5',
                              'BA.5.2.1': 'BA.5.2',
                              'BF.1': 'B.1.1.529.5.2.1',
                              'BA.2.12': 'BA.2'}

    curated_lineages = [
        {
            "who_name": "Omicron",
            "pango_descendants": [
                "B.1.1.529",
                "BA.1",
                "BA.2.12.1",
                "BA.2.12",
                "BA.2.65",
                "BA.5.1",
                "BA.5.2.1",
                "BA.4",
                "BA.4.1",
                "BA.5.5",
                "BA.5.2",
                "BF.1"]
        },
        {
            "who_name": "MadeUp",
            "pango_descendants": [
                "BA.3.65"]
        }
    ]

    seq_pool_comp_id = "SEARCH-91606__E0003116__I07__220527_A01535_0137_BHY5VWDSX3__002"
    sample_col_name = "samples"

    def test__munge_lineage_label_w_wildcard(self):
        an_input = "BA.5.2.1.X"
        expected_output = "BA.5.2.1."
        real_output = _munge_lineage_label(an_input)
        self.assertEqual(expected_output, real_output)

    def test__munge_lineage_label_wo_wildcard(self):
        an_input_1 = "BA.5.2.1."
        real_output_1 = _munge_lineage_label(an_input_1)
        self.assertEqual(an_input_1, real_output_1)

        an_input_2 = "BA.5.2.1"
        real_output_2 = _munge_lineage_label(an_input_2)
        self.assertEqual(an_input_2, real_output_2)

    def test__get_lineage_to_parents_dict(self):
        yml_str = """- name: A
  children:
      - A
      - B.1
      - B.1.528
      - B.1.529
- name: B
  children:
      - B.1.528
      - B.1.529
  parent: A
- name: B.1
  children:
  parent: B
- name: B.1.529
  children:
      - B.1.529
  parent: B.1
- name: BA.2
  children:
      - BA.2
  parent: B.1.1.529
- name: BA.5
  children:
      - BA.5
  parent: B.1.1.529
- name: BA.5.2
  children:
      - BA.5.2
      - BA.5.2.1
      - BA.5.2.2
      - BA.5.2.3
      - BA.5.2.4
      - BA.5.2.5
  parent: BA.5
- name: BA.5.2.1
  children:
      - BA.5.2.1
  parent: BA.5.2
- name: BF.1
  children:
      - BF.1
      - BF.1.1
  parent: B.1.1.529.5.2.1
- name: BA.2.12
  children:
      - BA.2.12
  parent: BA.2"""

        yml_fh = StringIO(yml_str)
        real_out = _get_lineage_to_parents_dict(yml_fh)
        self.assertDictEqual(self.lineage_to_parent_dict, real_out)

    def test__get_lineage_from_alias_aliased(self):
        an_input = "BF.1"
        expected_out = "B.1.1.529.5.2.1.1"
        real_out = _get_lineage_from_alias(
            an_input, self.lineage_to_parent_dict)
        self.assertEqual(expected_out, real_out)

    def test__get_lineage_from_alias_already_atomic(self):
        an_input = "B"
        # should get out "B", even though B does have a parent (A)
        # because alias system doesn't go up from one atomic letter to another
        expected_out = "B"
        real_out = _get_lineage_from_alias(
            an_input, self.lineage_to_parent_dict)
        self.assertEqual(expected_out, real_out)

    def test__get_lineage_from_alias_root(self):
        an_input = "A"
        # should get out "A"; A has an entry in the lineage_to_parent_dict
        # but that entry says the parent is None
        expected_out = "A"
        real_out = _get_lineage_from_alias(
            an_input, self.lineage_to_parent_dict)
        self.assertEqual(expected_out, real_out)

    def test__identify_label_for_lineage_aggregate_match(self):
        lineage_to_label = {"BA.5.": "BA.5",
                            "B.1.1.529.": "BA.5"}
        an_input = "BA.5"
        # BA.5 is included as part of BA.5.X (i.e., BA.5. )
        expected_out = "BA.5"
        real_out = _identify_label_for_lineage(
            an_input, lineage_to_label, OTHER_LINEAGE_LABEL)
        self.assertEqual(expected_out, real_out)

    def test__identify_label_for_lineage_aggregate_to_parent_match(self):
        lineage_to_label = {"BA.5.": "BA.5",
                            "B.1.1.529.": "BA.5"}
        an_input = "BA.5.2.1"
        # BA.5.2.1 should aggregate to the BA.5 label
        expected_out = "BA.5"
        real_out = _identify_label_for_lineage(
            an_input, lineage_to_label, OTHER_LINEAGE_LABEL)
        self.assertEqual(expected_out, real_out)

    def test__identify_label_for_lineage_exact_match(self):
        lineage_to_label = {"BA.5.": "BA.5",
                            "B.1.1.529.": "BA.5",
                            "BA.1.1": "BA.1.1"}
        an_input = "BA.1.1"
        # BA.1.1 doesn't aggregate (no dot at the end)--matches only exactly
        expected_out = "BA.1.1"
        real_out = _identify_label_for_lineage(
            an_input, lineage_to_label, OTHER_LINEAGE_LABEL)
        self.assertEqual(expected_out, real_out)

    def test__identify_label_for_lineage_other(self):
        lineage_to_label = {"BA.5.": "BA.5",
                            "B.1.1.529.": "BA.5",
                            "BA.1.1": "BA.1.1"}
        an_input = "BA.1.1.2"
        # labelled lineage BA.1.1 doesn't allow aggregation (no dot at the end)
        # --it accepts only exact matches--
        # so BA.1.1.2 doesn't match any of the labelled lineages and is thus
        # an "other"
        expected_out = OTHER_LINEAGE_LABEL
        real_out = _identify_label_for_lineage(
            an_input, lineage_to_label, OTHER_LINEAGE_LABEL)
        self.assertEqual(expected_out, real_out)

    def test__identify_label_for_aliased_lineage_aliased(self):
        lineage_to_label = {"BA.5.": "BA.5",
                            "B.1.1.529.": "BA.5",
                            "BA.1.1": "BA.1.1"}
        an_input = "BF.1"
        # BF.1 is a subtype of BA.5.2.1 and should aggregate to the BA.5 label
        expected_out = "BA.5"
        real_out = _identify_label_for_aliased_lineage(
            an_input, lineage_to_label, self.lineage_to_parent_dict)
        self.assertEqual(expected_out, real_out)

    def test__identify_label_for_aliased_lineage_unaliased(self):
        lineage_to_label = {"BA.5.": "BA.5",
                            "B.1.1.529.": "BA.5",
                            "BA.1.1": "BA.1.1"}
        an_input = "B.1.1.529.1"
        expected_out = "BA.5"
        real_out = _identify_label_for_aliased_lineage(
            an_input, lineage_to_label, self.lineage_to_parent_dict)
        self.assertEqual(expected_out, real_out)

    def test__make_lineage_labels_dict(self):
        reformatted_labels_dict = {
            "site_location": [
                "PointLoma", "PointLoma", "PointLoma", "PointLoma"],
            "site_prefix": [
                "PL", "PL", "PL", "PL"],
            "rollup_label": [
                "Omicron", "BA.1.1", "BA.4.X", "BA.5.X"],
            "component_type": [
                "variant", "lineage", "lineage", "lineage"],
            "munged_lineage_label": [
                "Omicron", "BA.1.1", "BA.4.", "BA.5."],
            "dealiased_munged_lineage_label": [
                "Omicron", "B.1.1.529.1.1", "BA.4.", "B.1.1.529.5."]
        }

        # NB: BA.4. is the same aliased and dealiased, so it appears only once
        expected_out_dict = {
            "Omicron": "Omicron",
            "BA.1.1": "BA.1.1",
            "BA.4.": "BA.4.",
            "BA.5.": "BA.5.",
            "B.1.1.529.1.1": "BA.1.1",
            "B.1.1.529.5.": "BA.5."
        }

        reformatted_labels_df = pandas.DataFrame(reformatted_labels_dict)
        real_out_dict = _make_lineage_labels_dict(reformatted_labels_df)
        self.assertDictEqual(expected_out_dict, real_out_dict)

    def test__make_variant_labels_dict(self):
        reformatted_labels_dict = {
            "site_location": [
                "PointLoma", "PointLoma", "PointLoma", "PointLoma"],
            "site_prefix": [
                "PL", "PL", "PL", "PL"],
            "rollup_label": [
                "Omicron", "MadeUp", "BA.4.1", "BA.5.X"],
            "component_type": [
                "variant", "variant", "lineage", "lineage"],
            "munged_lineage_label": [
                "Omicron", "MadeUp", "BA.4.1", "BA.5."],
            "dealiased_munged_lineage_label": [
                "Omicron", "MadeUp", "BA.4.1", "B.1.1.529.5."]
        }

        expected_out = {
            "B.1.1.529": "Omicron",
            "BA.1": "Omicron",
            "BA.2.12.1": "Omicron",
            "BA.2.12": "Omicron",
            "BA.2.65": "Omicron",
            "BA.5.1": "Omicron",
            "BA.5.2.1": "Omicron",
            "BA.4": "Omicron",
            "BA.4.1": "Omicron",
            "BA.5.5": "Omicron",
            "BA.5.2": "Omicron",
            "BA.3.65": "MadeUp",
            "BF.1": "Omicron"
        }

        allowed_labels_df = pandas.DataFrame(reformatted_labels_dict)
        real_out = _make_variant_labels_dict(
            allowed_labels_df, self.curated_lineages)
        self.assertDictEqual(expected_out, real_out)

    def test__make_variant_labels_dict_missing_variant_error(self):
        reformatted_labels_dict = {
            "site_location": [
                "PointLoma", "PointLoma", "PointLoma", "PointLoma"],
            "site_prefix": [
                "PL", "PL", "PL", "PL"],
            "rollup_label": [
                "Omicron", "MadeUp", "Delta", "BA.5.X"],
            "component_type": [
                "variant", "variant", "variant", "lineage"],
            "munged_lineage_label": [
                "Omicron", "MadeUp", "Delta", "BA.5."],
            "dealiased_munged_lineage_label": [
                "Omicron", "MadeUp", "Delta", "B.1.1.529.5."]
        }

        allowed_labels_df = pandas.DataFrame(reformatted_labels_dict)
        with self.assertRaisesRegex(
                ValueError, "Not all variants of interest found in "
                            "curated lineages"):
            _make_variant_labels_dict(allowed_labels_df, self.curated_lineages)

    def test__make_variant_labels_dict_duplicate_error(self):
        reformatted_labels_dict = {
            "site_location": [
                "PointLoma", "PointLoma", "PointLoma", "PointLoma"],
            "site_prefix": [
                "PL", "PL", "PL", "PL"],
            "rollup_label": [
                "Omicron", "MadeUp", "BA.4.1", "BA.5.X"],
            "component_type": [
                "variant", "variant", "lineage", "lineage"],
            "munged_lineage_label": [
                "Omicron", "MadeUp", "BA.4.1", "BA.5."],
            "dealiased_munged_lineage_label": [
                "Omicron", "MadeUp", "BA.4.1", "B.1.1.529.5."]
        }

        corrupted_curated_lineages = [
            {
                "who_name": "Omicron",
                "pango_descendants": [
                    "B.1.1.529",
                    "BA.1",
                    "BA.2.12.1",
                    "BA.2.12",
                    "BA.5.1",
                    "BA.5.2.1",
                    "BA.4",
                    "BA.4.1",
                    "BA.5.5",
                    "BA.5.2"]
            },
            {
                "who_name": "MadeUp",
                "pango_descendants": [
                    "BA.5.2",
                    "BA.2.65"]
            }
        ]

        allowed_labels_df = pandas.DataFrame(reformatted_labels_dict)
        with self.assertRaisesRegex(
                ValueError, "The lineage 'BA.5.2' is assigned to lineage "
                            "'MadeUp' and lineage 'Omicron'"):
            _make_variant_labels_dict(
                allowed_labels_df, corrupted_curated_lineages)

    def test_unmunge_lineage_label_munged(self):
        an_input = "BA.5."
        expected_out = "BA.5.X"
        real_out = unmunge_lineage_label(an_input)
        self.assertEqual(expected_out, real_out)

    def test_unmunge_lineage_label_unmunged(self):
        an_input = "BA.1.1"
        real_out = unmunge_lineage_label(an_input)
        self.assertEqual(an_input, real_out)

    def test_reformat_labels_df(self):
        dashboard_labels_dict = {
            "site_location": [
                "PointLoma", "PointLoma", "PointLoma", "PointLoma", "Encinas"],
            "site_prefix": [
                "PL", "PL", "PL", "PL", "ENC"],
            "rollup_label": [
                "Omicron", "BA.2.12", "BA.4.X", "BA.5.X", "BA.2.X"],
            "component_type": [
                "variant", "lineage", "lineage", "lineage", "lineage"]
        }

        expected_out_dict = {
            "site_location": [
                "PointLoma", "PointLoma", "PointLoma", "PointLoma"],
            "site_prefix": [
                "PL", "PL", "PL", "PL"],
            "rollup_label": [
                "Omicron", "BA.2.12", "BA.4.X", "BA.5.X"],
            "component_type": [
                "variant", "lineage", "lineage", "lineage"],
            "munged_lineage_label": [
                "Omicron", "BA.2.12", "BA.4.", "BA.5."],
            "dealiased_munged_lineage_label": [
                "Omicron", "B.1.1.529.2.12", "BA.4.", "B.1.1.529.5."]
        }

        dashboard_labels_df = pandas.DataFrame(dashboard_labels_dict)
        expected_out_df = pandas.DataFrame(expected_out_dict)
        real_out_df, real_out_prefix = reformat_labels_df(
            dashboard_labels_df, self.lineage_to_parent_dict, "PointLoma")

        self.assertEqual("PL", real_out_prefix)
        pandas.testing.assert_frame_equal(expected_out_df, real_out_df)

    def test_reformat_labels_df_prefix_error(self):
        dashboard_labels_dict = {
            "site_location": [
                "PointLoma", "PointLoma", "PointLoma", "PointLoma", "Encinas"],
            "site_prefix": [
                "PL", "PL", "PI", "PL", "ENC"],
            "rollup_label": [
                "Omicron", "BA.1.1", "BA.4.X", "BA.5.X", "BA.2.X"],
            "component_type": [
                "variant", "lineage", "lineage", "lineage", "lineage"]
        }

        dashboard_labels_df = pandas.DataFrame(dashboard_labels_dict)
        with self.assertRaisesRegex(ValueError, "site prefixes for"):
            reformat_labels_df(dashboard_labels_df,
                               self.lineage_to_parent_dict, "PointLoma")

    def test_make_freyja_w_id_df(self):
        expected_out_dict = {
        "summarized": [
            "[('BA.2* [Omicron (BA.2.X)]', 0.49641195397196025), ('Omicron', 0.46685900090836957), ('Other', 0.0067319954584884175)]",
            "[('Omicron', 0.49991486113136663), ('BA.2* [Omicron (BA.2.X)]', 0.4556013287335106), ('Other', 0.01207076124116462)]"],
        "lineages": [
            "BA.2.12.1 BA.2.12 BA.5.1 BA.5.2.1 BA.4 BA.4.1 BA.5.5 BA.5.2 BA.2.38 BA.2.16 BA.5.3.1 BE.1 BA.2.56 BF.1 BG.2 XAD BA.2.36 BA.2.65 BA.2.58 BA.2.13 miscBA2BA1PostSpike BA.2.11 BA.2.63 BA.2.53 BA.2.3.16 BA.2.50 BA.2.59 XQ BG.1 BA.2.19 BA.4.1.1 BA.2.48 BA.2.52 BA.2.70 BA.2.29 BA.2.72 BA.2.9.2 BA.2.10.3 BA.2.44 BA.2.71 BA.2.20 BA.2.31 BA.2.9.1 XZ BA.2.18 XY BA.2.22 BA.2.62 BA.5.3.2 BA.2.26 BA.2.61 BA.2.8 proposed757 BA.2.27 BA.2.25.1 BA.2.10.1 BA.2.3.7",
            "BA.2.12 BA.5.2 BA.4.1 BA.2.12.1 BA.5.1 BA.5.2.1 BA.5.5 BA.2.65 BA.4 BE.1 BG.2 BA.5.3.1 BA.2.3.5 miscBA2BA1PostSpike XAD BA.2.56 BA.2.3 BA.2.3.4 BG.1 BA.2.67 BA.2.61 BA.2.17 BA.2.22 BA.2.11 BA.2.42 BA.2.59 BA.2.10 BA.2.16 BA.2.27 BA.2.57 BA.2.52 BA.2.68 BA.2.72 BF.1 BA.4.1.1 BA.2.66 BA.2.8 BA.2.13 BA.1.1.5 XQ BA.2.71 BA.2.29 BA.2.3.16 BA.2.31 BA.2.53 BA.2.45 BA.2.70 BA.2.3.12 BA.5.3.2 BA.2.48 BA.2.19 BA.2.28 proposed590 BA.2.37 BA.2.40 BA.2.73"],
        "abundances": [
            "0.21823342 0.11696584 0.09523810 0.09436590 0.07060140 0.05007211 0.03996610 0.03476859 0.02966765 0.02391699 0.02351210 0.01724930 0.01116309 0.01028510 0.00901632 0.00835987 0.00813625 0.00787049 0.00782773 0.00652733 0.00541020 0.00528737 0.00458439 0.00410290 0.00377330 0.00348668 0.00341615 0.00306484 0.00268751 0.00262608 0.00255949 0.00225742 0.00220213 0.00219436 0.00206107 0.00202581 0.00199670 0.00199578 0.00196223 0.00189474 0.00189434 0.00186916 0.00183360 0.00179924 0.00179745 0.00168437 0.00167778 0.00166347 0.00162866 0.00161987 0.00156593 0.00135783 0.00132180 0.00128932 0.00126574 0.00126024 0.00114131",
            "0.21069000 0.12159864 0.11619024 0.10317434 0.05307850 0.05039021 0.04800864 0.03985987 0.03430699 0.02209150 0.01651844 0.01476350 0.01415340 0.01100568 0.00906176 0.00704470 0.00647347 0.00460503 0.00445935 0.00430377 0.00416445 0.00384183 0.00383441 0.00373471 0.00346779 0.00302982 0.00281367 0.00279720 0.00263366 0.00259605 0.00256129 0.00243105 0.00235849 0.00228919 0.00205717 0.00202122 0.00194230 0.00193510 0.00191316 0.00189274 0.00184190 0.00180144 0.00170077 0.00170068 0.00143396 0.00137958 0.00135124 0.00130661 0.00129484 0.00118534 0.00117706 0.00113843 0.00106508 0.00104502 0.00103862 0.00103306"],
        "samples": [
            "SEARCH-91626__E0003116__M08__220527_A01535_0137_BHY5VWDSX3__002",
            "SEARCH-91606__E0003116__I07__220527_A01535_0137_BHY5VWDSX3__002"]
        }
        expected_out_df = pandas.DataFrame(expected_out_dict)

        freyja_df = pandas.DataFrame(self.freyja_dict)
        real_out_df = make_freyja_w_id_df(freyja_df, "samples")
        pandas.testing.assert_frame_equal(expected_out_df, real_out_df)

    def test_validate_length_pass(self):
        validate_length([0,1], "List X", [2,3], "List Y")
        # if we didn't error out, we passed
        self.assertTrue(True)

    def test_validate_length_fail_no_source(self):
        expected_msg = "Found 2 records in List X but expected 1"
        with self.assertRaisesRegex(ValueError, expected_msg):
            validate_length([0,1], "List X", [3])

    def test_validate_length_fail_w_source(self):
        expected_msg = "Found 2 records in List X but expected 1 per List Y"
        with self.assertRaisesRegex(ValueError, expected_msg):
            validate_length([0,1], "List X", [3], "List Y")

    def test_explode_sample_freyja_results_duplicate_freyja_error(self):
        # multiple freyja records for single seq component id
        freyja_dict = {
            "summarized": [
                "[('BA.2* [Omicron (BA.2.X)]', 0.49641195397196025), ('Omicron', 0.46685900090836957), ('Other', 0.0067319954584884175)]",
                "[('Omicron', 0.49991486113136663), ('BA.2* [Omicron (BA.2.X)]', 0.4556013287335106), ('Other', 0.01207076124116462)]"],
            "lineages": [
                "BA.2.12.1 BA.2.12 BA.5.1 BA.5.2.1 BA.4 BA.4.1 BA.5.5 BA.5.2",
                "BA.2.12 BA.5.2 WA.4.1 BA.2.12.1 BA.5.1 BA.5.2.1 BA.5.5 BA.2.65"],
            "abundances": [
                "0.21823342 0.11696584 0.09523810 0.09436590 0.07060140 0.05007211 0.03996610 0.03476859",
                "0.21069000 0.12159864 0.11619024 0.10317434 0.05307850 0.05039021 0.04800864 0.03985987"],
            "samples": [
                "SEARCH-91626__E0003116__M08__220527_A01535_0137_BHY5VWDSX3__002",
                "SEARCH-91626__E0003116__M08__220527_A01535_0137_BHY5VWDSX3__002"]
        }

        freyja_df = pandas.DataFrame(freyja_dict)
        expected_err_msg = "Found 2 records in samples dataframe but expected 1"
        sample_id = "SEARCH-91626__E0003116__M08__220527_A01535_0137_BHY5VWDSX3__002"
        with self.assertRaisesRegex(ValueError, expected_err_msg):
            explode_sample_freyja_results(
                freyja_df, sample_id, self.sample_col_name,
                explode_variants=False)

    def test_explode_sample_freyja_results_lineage_abundance_mismatch_err(self):
        # lineage and abundance lists w diff numbers of entries
        freyja_dict = {
            "summarized": [
                "[('BA.2* [Omicron (BA.2.X)]', 0.49641195397196025), ('Omicron', 0.46685900090836957), ('Other', 0.0067319954584884175)]",
                "[('Omicron', 0.49991486113136663), ('BA.2* [Omicron (BA.2.X)]', 0.4556013287335106), ('Other', 0.01207076124116462)]"],
            "lineages": [
                "BA.2.12.1 BA.2.12 BA.5.1 BA.5.2.1 BA.4 BA.4.1 BA.5.5 BA.5.2",
                "BA.2.12 BA.5.2 WA.4.1 BA.2.12.1 BA.5.1 BA.5.2.1 BA.5.5 BA.2.65"],
            "abundances": [
                "0.21823342 0.11696584 0.09523810 0.09436590 0.07060140 0.05007211 0.03996610 0.03476859",
                "0.21069000 0.12159864 0.11619024 0.10317434 0.05307850 0.05039021 0.04800864 0.03985987"],
            "samples": [
                "SEARCH-91626__E0003116__M08__220527_A01535_0137_BHY5VWDSX3__002",
                "SEARCH-91606__E0003116__I07__220527_A01535_0137_BHY5VWDSX3__002"]
        }

        freyja_df = pandas.DataFrame(freyja_dict)
        freyja_df.loc[0, "abundances"] = "0.21823342 0.11696584 0.09523810 " \
                                         "0.09436590"
        expected_err_msg = "Found 4 records in abundances but expected 8 " \
                           "per lineages"
        sample_id = "SEARCH-91626__E0003116__M08__220527_A01535_0137_BHY5VWDSX3__002"
        with self.assertRaisesRegex(ValueError, expected_err_msg):
            explode_sample_freyja_results(
                freyja_df, sample_id, self.sample_col_name,
                explode_variants=False)

    def _help_test_explode_sample_freyja_results(
            self, do_explode_variants, expected_exploded_dict):
        freyja_dict = {
            "summarized": [
                "[('BA.2* [Omicron (BA.2.X)]', 0.49641195397196025), ('Omicron', 0.46685900090836957), ('Other', 0.0067319954584884175)]",
                "[('Omicron', 0.49991486113136663), ('BA.2* [Omicron (BA.2.X)]', 0.4556013287335106), ('Other', 0.01207076124116462)]"],
            "lineages": [
                "BA.2.12.1 BA.2.12 BA.5.1 BA.5.2.1 BA.4 BA.4.1 BA.5.5 BA.5.2",
                "BA.2.12 BA.5.2 BA.4.1 BA.2.12.1 BA.5.1 BA.5.2.1 BA.5.5 BA.2.65"],
            "abundances": [
                "0.21823342 0.11696584 0.09523810 0.09436590 0.07060140 0.05007211 0.03996610 0.03476859",
                "0.21069000 0.12159864 0.11619024 0.10317434 0.05307850 0.05039021 0.04800864 0.03985987"],
            "samples": [
                "SEARCH-91626__E0003116__M08__220527_A01535_0137_BHY5VWDSX3__002",
                "SEARCH-91606__E0003116__I07__220527_A01535_0137_BHY5VWDSX3__002"]
        }

        expected_sample_dict = {
            "summarized": [
                "[('Omicron', 0.49991486113136663), ('BA.2* [Omicron (BA.2.X)]', 0.4556013287335106), ('Other', 0.01207076124116462)]"],
            "lineages": [
                "BA.2.12 BA.5.2 BA.4.1 BA.2.12.1 BA.5.1 BA.5.2.1 BA.5.5 BA.2.65"],
            "abundances": [
                "0.21069000 0.12159864 0.11619024 0.10317434 0.05307850 0.05039021 0.04800864 0.03985987"],
            "samples": [
                "SEARCH-91606__E0003116__I07__220527_A01535_0137_BHY5VWDSX3__002"]
        }

        input_df = pandas.DataFrame(freyja_dict)
        expected_exploded_df = pandas.DataFrame(expected_exploded_dict)
        # index is 1 because it is the 2nd (0-based) record in input df
        expected_sample_df = pandas.DataFrame(expected_sample_dict, index=[1])

        real_exploded_df, real_sample_df = explode_sample_freyja_results(
            input_df, self.seq_pool_comp_id, self.sample_col_name,
            explode_variants=do_explode_variants)

        pandas.testing.assert_frame_equal(
            expected_exploded_df, real_exploded_df)
        pandas.testing.assert_frame_equal(
            expected_sample_df, real_sample_df)

    def test_explode_sample_freyja_results_w_variants(self):
        expected_exploded_dict = {
            "component": [
                "BA.2.12", "BA.5.2", "BA.4.1", "BA.2.12.1", "BA.5.1", "BA.5.2.1", "BA.5.5", "BA.2.65", "Omicron", "BA.2* [Omicron (BA.2.X)]", "Other"],
            "component_fraction": [
                0.21069000, 0.12159864, 0.11619024, 0.10317434, 0.05307850, 0.05039021, 0.04800864, 0.03985987, 0.49991486113136663, 0.4556013287335106, 0.01207076124116462],
            "component_type": [
                "lineage", "lineage", "lineage", "lineage", "lineage", "lineage", "lineage", "lineage", "variant", "variant", "variant"]
        }

        self._help_test_explode_sample_freyja_results(
            True, expected_exploded_dict)

    def test_explode_sample_freyja_results_wo_variants(self):
        expected_exploded_dict = {
            "component": [
                "BA.2.12", "BA.5.2", "BA.4.1", "BA.2.12.1", "BA.5.1", "BA.5.2.1", "BA.5.5", "BA.2.65"],
            "component_fraction": [
                0.21069000, 0.12159864, 0.11619024, 0.10317434, 0.05307850, 0.05039021, 0.04800864, 0.03985987],
            "component_type": [
                "lineage", "lineage", "lineage", "lineage", "lineage", "lineage", "lineage", "lineage"]
        }

        self._help_test_explode_sample_freyja_results(
            False, expected_exploded_dict)

    def test_explode_and_label_sample_freyja_results(self):
        freyja_dict = {
            "summarized": [
                "[('BA.2* [Omicron (BA.2.X)]', 0.49641195397196025), ('Omicron', 0.46685900090836957), ('Other', 0.0067319954584884175)]",
                "[('Omicron', 0.49991486113136663), ('BA.2* [Omicron (BA.2.X)]', 0.4556013287335106), ('Other', 0.01207076124116462)]"],
            "lineages": [
                "BA.2.12.1 BA.2.12 BA.5.1 BA.5.2.1 BA.4 BA.4.1 BA.5.5 BA.5.2",
                "BA.2.12 BA.5.2 WA.4.1 BA.2.12.1 BA.5.1 BA.5.2.1 BA.5.5 BA.2.65"],
            "abundances": [
                "0.21823342 0.11696584 0.09523810 0.09436590 0.07060140 0.05007211 0.03996610 0.03476859",
                "0.21069000 0.12159864 0.11619024 0.10317434 0.05307850 0.05039021 0.04800864 0.03985987"],
            "samples": [
                "SEARCH-91626__E0003116__M08__220527_A01535_0137_BHY5VWDSX3__002",
                "SEARCH-91606__E0003116__I07__220527_A01535_0137_BHY5VWDSX3__002"]
        }

        expected_sample_dict = {
            "summarized": [
                "[('Omicron', 0.49991486113136663), ('BA.2* [Omicron (BA.2.X)]', 0.4556013287335106), ('Other', 0.01207076124116462)]"],
            "lineages": [
                "BA.2.12 BA.5.2 WA.4.1 BA.2.12.1 BA.5.1 BA.5.2.1 BA.5.5 BA.2.65"],
            "abundances": [
                "0.21069000 0.12159864 0.11619024 0.10317434 0.05307850 0.05039021 0.04800864 0.03985987"],
            "samples": [
                "SEARCH-91606__E0003116__I07__220527_A01535_0137_BHY5VWDSX3__002"]
        }

        reformatted_labels_dict = {
            "site_location": [
                "PointLoma", "PointLoma", "PointLoma", "PointLoma"],
            "site_prefix": [
                "PL", "PL", "PL", "PL"],
            "rollup_label": [
                "Omicron", "BA.2.X", "BA.4.1", "BA.5.X"],
            "component_type": [
                "variant", "lineage", "lineage", "lineage"],
            "munged_lineage_label": [
                "Omicron", "BA.2.", "BA.4.1", "BA.5."],
            "dealiased_munged_lineage_label": [
                "Omicron", "BA.2.", "BA.4.1", "B.1.1.529.5."]
        }

        expected_out_dict = {
            "component": [
                "BA.2.12", "BA.5.2", "WA.4.1", "BA.2.12.1", "BA.5.1", "BA.5.2.1", "BA.5.5", "BA.2.65"],
            "component_fraction": [
                0.21069000, 0.12159864, 0.11619024, 0.10317434, 0.05307850, 0.05039021, 0.04800864, 0.03985987],
            "component_type": [
                "lineage", "lineage", "lineage", "lineage", "lineage", "lineage", "lineage", "lineage"],
            "lineage_label": [
                "BA.2.", "BA.5.", "Other lineage", "BA.2.", "BA.5.", "BA.5.", "BA.5.", "BA.2."],
            "variant_label": [
                "Omicron", "Omicron", "Other", "Omicron", "Omicron", "Omicron", "Omicron", "Omicron"]
        }

        input_df = pandas.DataFrame(freyja_dict)
        label_dict = pandas.DataFrame(reformatted_labels_dict)
        expected_out_df = pandas.DataFrame(expected_out_dict)
        # index is 1 because it is the 2nd (0-based) record in input df
        expected_sample_df = pandas.DataFrame(expected_sample_dict, index=[1])

        real_l_df, real_s_df = explode_and_label_sample_freyja_results(
            input_df, self.seq_pool_comp_id, self.sample_col_name, label_dict,
            self.lineage_to_parent_dict, self.curated_lineages,
            explode_variants=False)

        pandas.testing.assert_frame_equal(
            expected_out_df, real_l_df)
        pandas.testing.assert_frame_equal(
            expected_sample_df, real_s_df)

    def test_get_freyja_results_fp(self):
        expected_out = f"{self.dummy_dir}/dummy_campus_2022-07-25_16-54-16_freyja_aggregated.tsv"
        real_out = get_freyja_results_fp(self.dummy_dir)
        self.assertEqual(expected_out, real_out)

    def test_load_inputs_from_input_dir(self):
        expected_labels_dict = {
            "site_location": [
                "PointLoma", "PointLoma", "PointLoma", "PointLoma", "PointLoma"],
            "site_prefix": [
                "PL", "PL", "PL", "PL", "PL"],
            "rollup_label": [
                "Omicron", "MadeUp", "BA.5.X", "BA.1.1.X", "BA.2.12"],
            "component_type": [
                "variant", "variant", "lineage", "lineage", "lineage"]
        }

        freyja_dict = {
            "Unnamed: 0": [
                "SEARCH-91626__E0003116__M08__220527_A01535_0137_BHY5VWDSX3__002.tsv",
                "SEARCH-91606__E0003116__I07__220527_A01535_0137_BHY5VWDSX3__002.tsv"],
            "summarized": [
                "[('BA.2* [Omicron (BA.2.X)]', 0.49641195397196025), ('Omicron', 0.46685900090836957), ('Other', 0.0067319954584884175)]",
                "[('Omicron', 0.49991486113136663), ('BA.2* [Omicron (BA.2.X)]', 0.4556013287335106), ('Other', 0.01207076124116462)]"],
            "lineages": [
                "BA.2.12.1 BA.2.12 BA.5.1 BA.5.2.1 BA.4 BQ.4.1 BA.5.5 BA.5.2",
                "BA.2.12 BA.5.2 BA.4.1 BA.2.12.1 BF.1 BA.5.2.1 BA.5.5 BA.2.65"],
            "abundances": [
                "0.21823342 0.11696584 0.09523810 0.09436590 0.07060140 0.05007211 0.03996610 0.03476859",
                "0.21069000 0.12159864 0.11619024 0.10317434 0.05307850 0.05039021 0.04800864 0.03985987"],
            "resid": [
                9.099812474,
                8.794045167],
            "coverage": [
                98.9399057,
                99.14724275]
        }

        labels_fp = f"{self.dummy_dir}/dummy_labels_2022-07-11_22-32-05.csv"
        expected_labels_df = pandas.DataFrame(expected_labels_dict)
        expected_freyja_df = pandas.DataFrame(freyja_dict)

        labels_df, l_to_parents_dict, cur_lineages, freyja_df = \
            load_inputs_from_input_dir(labels_fp, self.dummy_dir)
        pandas.testing.assert_frame_equal(expected_labels_df, labels_df)
        self.assertDictEqual(self.lineage_to_parent_dict, l_to_parents_dict)
        self.assertEqual(self.curated_lineages, cur_lineages)
        pandas.testing.assert_frame_equal(expected_freyja_df, freyja_df)

    def test_get_ref_dir(self):
        ref_dir = get_ref_dir()
        # The output can't be tested for exact correctness because it is
        # an absolute path; settle for checking the part that is constant
        self.assertTrue(ref_dir.endswith("/cview-currents/reference_files"))
