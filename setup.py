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
            'generate_search_wastewater_lineages_report=src.generate_search_wastewater_lineages_report:main',
            'freyja_download=src.freyja_processing_utils:freyja_download'
        ]}
)
