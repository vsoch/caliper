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
        results = metric.get_results()

        # MetricBase has lookup by commit
        if isinstance(metric, ChangeMetricBase):

            # One is required
            assert results.get("by-group") or results.get("by-file")
            assert "0.0.1..0.0.11" in results.get("by-group") or ["0.0.1..0.0.11"]
            assert "0.0.1..0.0.11" in results.get("by-file") or ["0.0.1..0.0.11"]

        elif isinstance(metric, MetricBase):

            # One is required
            assert results.get("by-group") or results.get("by-file")

            # ensure if no result type is provided, passes
            assert "0.0.1" in results.get("by-group") or ["0.0.1"]
            assert "0.0.1" in results.get("by-file") or ["0.0.1"]
