import os
from unittest import TestCase


class FileTestCase(TestCase):
    test_file_dir = os.path.dirname(os.path.abspath(__file__))
    test_data_dir = os.path.join(test_file_dir, "data")
    dummy_dir = os.path.join(test_data_dir, "dummy")
    gold_standard_dir = f"{test_data_dir}/gold_standard"
    test_temp_dir = f"{test_data_dir}/temp"
