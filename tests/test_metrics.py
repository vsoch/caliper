__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

import os
import sys
import pytest


def test_metrics_extractor(tmp_path):
    """test git manager"""
    print("Testing Metrics and Extractor")
    from caliper.managers import PypiManager

    manager = PypiManager("sif")

    from caliper.metrics import MetricsExtractor
    from caliper.metrics.base import MetricBase, ChangeMetricBase

    extractor = MetricsExtractor(manager)

    # prepare the repository
    repo = extractor.prepare_repository()
    extractor.extract_all()

    # test data export for each metric
    for name, metric in extractor:

        # File results should have lookup by version or
        file_results = metric.get_file_results()
        summed_results = metric.get_summed_results()

        # MetricBase has lookup by commit
        if isinstance(metric, ChangeMetricBase):
            assert "0.0.1..0.0.11" in file_results
            assert "0.0.1..0.0.11" in summed_results

            # Ensure they aren't empty or null
            file_result = file_results["0.0.1..0.0.11"][0]
            assert len(file_result) >= 7
            assert file_result["lines"] > 0

        elif isinstance(metric, MetricBase):
            assert "0.0.1" in file_results
            assert "0.0.1" in summed_results

            # Ensure they aren't empty or null
            summed_result = summed_results["0.0.1"]
            assert len(summed_result) >= 3
            assert summed_result["files"] > 0
