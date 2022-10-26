# ----------------------------------------------------------------------------
# Copyright (c) 2018-2022, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
from setuptools import setup, find_packages


setup(
    name='cview-currents',
    version="0.1.0",
    license='BSD-3-Clause',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'download_report_inputs=src.freyja_processing_utils:download_inputs',
            'make_freyja_metadata=src.generate_search_wastewater_lineages_report:generate_freyja_metadata',
            'make_search_reports=src.generate_search_wastewater_lineages_report:generate_reports',
            'make_campus_reports=src.generate_campus_wastewater_lineages_report:generate_reports',
            'get_cview_bam_urls=src.generate_campus_wastewater_lineages_report:get_bam_urls'
        ]}
)
