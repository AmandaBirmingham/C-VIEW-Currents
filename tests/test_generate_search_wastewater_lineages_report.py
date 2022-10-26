import os
import filecmp
from tests.filetestcase import FileTestCase
from src.generate_search_wastewater_lineages_report import \
    generate_dashboard_reports


class GenerateDashboardReportTest(FileTestCase):
    def test_generate_dashboard_reports(self):
        dummy_out_dir = f"{self.dummy_dir}/dummy_search_outputs"
        expected_freyja_fails_fp = f"{dummy_out_dir}/" \
                                   f"dummy_genexus_freyja_qc_fails.tsv"
        # TODO: I prefer that files that go into the temp dir don't have the
        #  "dummy" prefix, but this happens here because the name is auto-
        #  generated based on the freyja results file used; consider changing
        real_freyja_fails_fp = f"{self.test_temp_dir}/" \
                               f"dummy_genexus_freyja_qc_fails.tsv"

        # Note: optional last argument 'suppress' suppresses the creation of
        # intermediate exploded per-sample files
        arg_list = ["make_search_reports",
                    f"{self.dummy_dir}/dummy_search_inputs",
                    self.test_temp_dir, "suppress"]

        freyja_fails_is_file = out_enc_is_file = out_pl_is_file = False
        freyja_fails_equal = out_enc_equal = out_pl_equal = False
        output_enc_fp = output_pl_fp = None
        try:
            output_pl_fp, output_enc_fp = generate_dashboard_reports(arg_list)

            freyja_fails_is_file = os.path.isfile(real_freyja_fails_fp)
            self.assertTrue(freyja_fails_is_file)

            freyja_fails_equal = filecmp.cmp(
                real_freyja_fails_fp, expected_freyja_fails_fp)
            self.assertTrue(freyja_fails_equal)

            out_enc_is_file = os.path.isfile(output_enc_fp)
            self.assertTrue(out_enc_is_file)

            out_enc_equal = filecmp.cmp(
                output_enc_fp, f"{dummy_out_dir}/Encina_sewage_seqs.csv")
            self.assertTrue(out_enc_equal)

            out_pl_is_file = os.path.isfile(output_pl_fp)
            self.assertTrue(out_pl_is_file)

            out_pl_equal = filecmp.cmp(
                output_pl_fp,
                f"{dummy_out_dir}/PointLoma_sewage_seqs.csv")
            self.assertTrue(out_pl_equal)
        finally:
            if freyja_fails_is_file and out_enc_is_file and out_pl_is_file \
                    and freyja_fails_equal and out_enc_equal and out_pl_equal:
                try:
                    os.remove(real_freyja_fails_fp)
                    os.remove(output_enc_fp)
                    os.remove(output_pl_fp)
                except OSError:
                    pass
