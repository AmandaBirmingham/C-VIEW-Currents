import os
import filecmp
from tests.filetestcase import FileTestCase
from src.generate_search_wastewater_lineages_report import \
    generate_dashboard_reports


class GenerateDashboardReportTest(FileTestCase):
    def test_generate_dashboard_reports(self):
        input_label_fp = \
            f"{self.dummy_dir}/dummy_labels_for_search.csv"
        dummy_out_dir = f"{self.dummy_dir}/dummy_search_outputs"

        # Note: optional last argument 'suppress' suppresses the creation of
        # intermediate exploded per-sample files
        arg_list = [f"{self.dummy_dir}/dummy_search_inputs",
                    self.test_temp_dir, input_label_fp, "suppress"]

        out_enc_is_file = out_pl_is_file = False
        out_enc_equal = out_pl_equal = False
        output_enc_fp = output_pl_fp = None
        try:
            output_pl_fp, output_enc_fp = generate_dashboard_reports(arg_list)

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
            if out_enc_is_file and out_pl_is_file and \
                    out_enc_equal and out_pl_equal:
                try:
                    os.remove(output_enc_fp)
                    os.remove(output_pl_fp)
                except OSError:
                    pass
