import os
import filecmp
import pandas
from tests.filetestcase import FileTestCase
from src.generate_campus_wastewater_lineages_report import \
    generate_dashboard_report_df, generate_dashboard_report, _extract_bam_urls


class GenerateDashboardReportTest(FileTestCase):
    freyja_dict = {
        "Unnamed: 0": [
            "SEARCH-91626__E0003116__M08__220527_A01535_0137_BHY5VWDSX3__002.tsv",
            "SEARCH-91606__E0003116__I07__220527_A01535_0137_BHY5VWDSX3__002.tsv",
            "SEARCH-291606__X0003116__G07__230527_A01535_0137_BHY5VWDSX3__001.tsv"],
        "summarized": [
            "[('BA.2* [Omicron (BA.2.X)]', 0.49641195397196025), ('Omicron', 0.46685900090836957), ('Other', 0.0067319954584884175)]",
            "[('Omicron', 0.49991486113136663), ('BA.2* [Omicron (BA.2.X)]', 0.4556013287335106), ('Other', 0.01207076124116462)]",
            "[('Omicron', 0.69991486113136663), ('BA.2* [Omicron (BA.2.X)]', 0.2556013287335106), ('Other', 0.00207076124116462)]"],
        "lineages": [
            "BA.2.12.1 BA.2.12 BA.5.1 BA.5.2.1 BA.4 BA.4.1 BA.5.5 BA.5.2 BA.2.38 BA.2.16 BA.5.3.1 BE.1 BA.2.56 BF.1 BG.2 XAD BA.2.36 BA.2.65 BA.2.58 BA.2.13 miscBA2BA1PostSpike BA.2.11 BA.2.63 BA.2.53 BA.2.3.16 BA.2.50 BA.2.59 XQ BG.1 BA.2.19 BA.4.1.1 BA.2.48 BA.2.52 BA.2.70 BA.2.29 BA.2.72 BA.2.9.2 BA.2.10.3 BA.2.44 BA.2.71 BA.2.20 BA.2.31 BA.2.9.1 XZ BA.2.18 XY BA.2.22 BA.2.62 BA.5.3.2 BA.2.26 BA.2.61 BA.2.8 proposed757 BA.2.27 BA.2.25.1 BA.2.10.1 BA.2.3.7",
            "BA.2.12 BA.5.2 BA.4.1 BA.2.12.1 BA.5.1 BA.5.2.1 BA.5.5 BA.2.65 BA.4 BE.1 BG.2 BA.5.3.1 BA.2.3.5 miscBA2BA1PostSpike XAD BA.2.56 BA.2.3 BA.2.3.4 BG.1 BA.2.67 BA.2.61 BA.2.17 BA.2.22 BA.2.11 BA.2.42 BA.2.59 BA.2.10 BA.2.16 BA.2.27 BA.2.57 BA.2.52 BA.2.68 BA.2.72 BF.1 BA.4.1.1 BA.2.66 BA.2.8 BA.2.13 BA.1.1.5 XQ BA.2.71 BA.2.29 BA.2.3.16 BA.2.31 BA.2.53 BA.2.45 BA.2.70 BA.2.3.12 BA.5.3.2 BA.2.48 BA.2.19 BA.2.28 proposed590 BA.2.37 BA.2.40 BA.2.73",
            "BA.2.12 BA.5.2 BA.4.1 BA.2.12.1"],
        "abundances": [
            "0.21823342 0.11696584 0.09523810 0.09436590 0.07060140 0.05007211 0.03996610 0.03476859 0.02966765 0.02391699 0.02351210 0.01724930 0.01116309 0.01028510 0.00901632 0.00835987 0.00813625 0.00787049 0.00782773 0.00652733 0.00541020 0.00528737 0.00458439 0.00410290 0.00377330 0.00348668 0.00341615 0.00306484 0.00268751 0.00262608 0.00255949 0.00225742 0.00220213 0.00219436 0.00206107 0.00202581 0.00199670 0.00199578 0.00196223 0.00189474 0.00189434 0.00186916 0.00183360 0.00179924 0.00179745 0.00168437 0.00167778 0.00166347 0.00162866 0.00161987 0.00156593 0.00135783 0.00132180 0.00128932 0.00126574 0.00126024 0.00114131",
            "0.21069000 0.12159864 0.11619024 0.10317434 0.05307850 0.05039021 0.04800864 0.03985987 0.03430699 0.02209150 0.01651844 0.01476350 0.01415340 0.01100568 0.00906176 0.00704470 0.00647347 0.00460503 0.00445935 0.00430377 0.00416445 0.00384183 0.00383441 0.00373471 0.00346779 0.00302982 0.00281367 0.00279720 0.00263366 0.00259605 0.00256129 0.00243105 0.00235849 0.00228919 0.00205717 0.00202122 0.00194230 0.00193510 0.00191316 0.00189274 0.00184190 0.00180144 0.00170077 0.00170068 0.00143396 0.00137958 0.00135124 0.00130661 0.00129484 0.00118534 0.00117706 0.00113843 0.00106508 0.00104502 0.00103862 0.00103306",
            "0.40069000 0.02159864 0.01619024 0.11317434"]
    }

    cview_dict = {
        "sequenced_pool_component_id": [
            "SEARCH-91626__E0003116__M08__220527_A01535_0137_BHY5VWDSX3__002",
            "SEARCH-91606__E0003116__I07__220527_A01535_0137_BHY5VWDSX3__002",
            "SEARCH-291606__X0003116__G07__230527_A01535_0137_BHY5VWDSX3__001.tsv"],
        "sample_id": ["5.11.22.AS127", "5.15.22.AS061.R2", "3.17.22.UNLABELLED"],
        "sample_collection_datetime":
            ["2022-05-11 00:00:00+00:00", "2022-05-15 00:00:00+00:00",
             "2022-03-16 00:00:00+00:00"],
        "sample_sequencing_datetime":
            ["2022-05-27 00:00:00+00:00", "2022-05-27 00:00:00+00:00",
             "2022-03-17 00:00:00+00:00"],
        "sequencing_tech": ["Illumina", "Illumina", "Illumina"],
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

    labels_dict = {
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

    def test_generate_dashboard_report_df(self):
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
        }

        expected_out_dict = {
            'lineage': ['BA.2.12', 'BA.5.2', 'BA.4.1', 'BA.2.12.1', 'BF.1',
                        'BA.5.2.1', 'BA.5.5', 'BA.2.65', 'BA.2.12.1', 'BA.2.12',
                        'BA.5.1', 'BA.5.2.1', 'BA.4', 'BQ.4.1', 'BA.5.5',
                        'BA.5.2'],
            'lineage_fraction': [0.21069, 0.12159864, 0.11619024, 0.10317434,
                                 0.0530785, 0.05039021, 0.04800864, 0.03985987,
                                 0.21823342, 0.11696584, 0.0952381, 0.0943659,
                                 0.0706014, 0.05007211, 0.0399661, 0.03476859],
            'component_type': ["lineage" for x in range(16)],
            'lineage_label': ['BA.2.X', 'BA.5.X', 'BA.4.1', 'BA.2.X', 'BA.5.X',
                              'BA.5.X', 'BA.5.X', 'BA.2.X', 'BA.2.X', 'BA.2.X',
                              'BA.5.X', 'BA.5.X', 'Other lineage',
                              'Other lineage', 'BA.5.X', 'BA.5.X'],
            'variant_label': ['Omicron', 'Omicron', 'Omicron', 'Omicron',
                              'Omicron', 'Omicron', 'Omicron', 'Omicron',
                              'Omicron', 'Omicron', 'Omicron', 'Omicron',
                              'Omicron', 'Other', 'Omicron', 'Omicron'],
            'labels_datetime': ['2022-07-11 22:32:05' for x in range(16)],
            'freyja_run_datetime': ['2022-07-25 16:54:16' for x in range(16)],
            'sequenced_pool_component_id': ['SEARCH-91606__E0003116__I07__220527_A01535_0137_BHY5VWDSX3__002' for x in range(8)] + ['SEARCH-91626__E0003116__M08__220527_A01535_0137_BHY5VWDSX3__002' for x in range(8)],
            'external_sample_name': ['5.15.22.AS061.R2' for x in range(8)] + ['5.11.22.AS127' for x in range(8)],
            'external_sampler_name': ['AS061' for x in range(8)] + ['AS127' for x in range(8)],
            'sample_collection_datetime': ['2022-05-15 00:00:00' for x in range(8)] + ['2022-05-11 00:00:00' for x in range(8)],
            'sample_sequencing_datetime': ['2022-05-27 00:00:00' for x in range(16)],
            'sequencing_tech': ['Illumina' for x in range(16)]
        }

        freyja_df = pandas.DataFrame(freyja_dict)
        cview_df = pandas.DataFrame(self.cview_dict)
        labels_df = pandas.DataFrame(self.labels_dict)
        expected_out_df = pandas.DataFrame(expected_out_dict)

        output_df = generate_dashboard_report_df(
            cview_df, freyja_df, labels_df,
            self.lineage_to_parent_dict, self.curated_lineages,
            "2022-07-11 22:32:05", "2022-07-25 16:54:16")
        pandas.testing.assert_frame_equal(expected_out_df, output_df)

    def _test_generate_dashboard_report_df_error(
            self, expected_msg, freyja_df=None, cview_df=None):

        freyja_df = freyja_df if freyja_df is not None \
            else pandas.DataFrame(self.freyja_dict)
        cview_df = cview_df if cview_df is not None else \
            pandas.DataFrame(self.cview_dict)
        labels_df = pandas.DataFrame(self.labels_dict)

        with self.assertRaisesRegex(ValueError, expected_msg):
            generate_dashboard_report_df(
                cview_df, freyja_df, labels_df,
                self.lineage_to_parent_dict, self.curated_lineages,
                "2022-07-11_22-32-05", "2022-07-25_16-54-16")

    def test_generate_dashboard_report_df_missing_cview_match_error(self):
        # cview doesn't contain a match for all freyja records
        cview_df = pandas.DataFrame(self.cview_dict)
        cview_df.drop(index=0, inplace=True)
        expected_err_msg = "Found 1 records in freyja-cview merge but " \
                           "expected 3 per freyja results"
        self._test_generate_dashboard_report_df_error(
            expected_err_msg, cview_df=cview_df)

    def test_generate_dashboard_report(self):
        expected_dashboard_report_fp = \
            f"{self.dummy_dir}/dummy_campus_ww_lineages_report.csv"
        expected_freyja_fails_fp = \
            f"{self.dummy_dir}/dummy_freyja_qc_fails.tsv"

        out_freyja_fails_fp = f"{self.test_temp_dir}/" \
                              f"dummy_campus_2022-07-25_16-54-16_" \
                              f"freyja_qc_fails.tsv"

        arg_list = ["generate_campus_wastewater_lineages_report.py",
                    self.dummy_dir, self.test_temp_dir]

        out_report_is_file = out_fails_is_file = False
        out_report_equal = out_fails_equal = False
        output_fp = None
        try:
            output_fp = generate_dashboard_report(arg_list)

            out_fails_is_file = os.path.isfile(out_freyja_fails_fp)
            self.assertTrue(out_fails_is_file)

            out_fails_equal = filecmp.cmp(
                out_freyja_fails_fp, expected_freyja_fails_fp)
            self.assertTrue(out_fails_equal)

            out_report_is_file = os.path.isfile(output_fp)
            self.assertTrue(out_report_is_file)

            out_report_equal = filecmp.cmp(
                output_fp, expected_dashboard_report_fp)
            self.assertTrue(out_report_equal)
        finally:
            if out_fails_is_file and out_report_is_file and\
                    out_fails_equal and out_report_equal:
                try:
                    os.remove(out_freyja_fails_fp)
                    os.remove(output_fp)
                except OSError:
                    pass

    def test__extract_bam_urls(self):
        input_cview_summary_fp = \
            f"{self.dummy_dir}/dummy_cview_summary-report_all.csv"

        expected_urls_fp = \
            f"{self.dummy_dir}/dummy_cview_summary_report_rtl_" \
            f"wastewater_highcov_s3_urls.txt"

        out_is_file = False
        out_equal = False
        output_fp = None
        try:
            output_fp = _extract_bam_urls(
                input_cview_summary_fp,
                "s3://dummy/dummy_cview_summary_all.csv",
                self.test_temp_dir)

            out_is_file = os.path.isfile(output_fp)
            self.assertTrue(out_is_file)

            out_equal = filecmp.cmp(output_fp, expected_urls_fp)
            self.assertTrue(out_equal)
        finally:
            if out_is_file and out_equal:
                try:
                    os.remove(output_fp)
                except OSError:
                    pass
