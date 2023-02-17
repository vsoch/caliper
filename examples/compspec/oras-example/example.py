#!/usr/bin/env/python3

# This is one way to get releases!
# import json
import os
import sys

import pytest

from caliper.analysis.tracer import CommandTracer
from caliper.managers import PypiManager
from caliper.metrics import MetricsExtractor

here = os.path.abspath(os.path.dirname(__file__))

results = {}
sig = None


def main():
    # For this first part, we will create a manager and extract complete data for it
    manager = PypiManager("oras")

    # Just do two specs for a diff
    extractor = MetricsExtractor(manager)

    # This repository will have each release version represented as a tagged commit
    extractor.prepare_repository()

    # Extract metric for compspec
    metric = extractor.extract_metric("compspec")

    # For this second part, we will target an oras clone and try to trace the tests.
    oras_clone = os.path.join(here, "oras-py")
    if not os.path.exists(oras_clone):
        sys.exit(
            "Please clone oras to oras-py here, e.g., git clone --depth 1 https://github.com/oras-project/oras-py"
        )

    # EXAMPLE 1: Command trace
    # Prepare a command tracer - starting with just the utils tests (simplest ones)
    commands = [
        [pytest.main, ["-xs", "oras-py/oras/tests/test_utils.py"]],
        [pytest.main, ["-xs", "oras-py/oras/tests/test_oras.py"]],
    ]
    tracer = CommandTracer()

    # The tracer will add incompatibilities / results to the metric
    tracer.trace(metric, commands)

    # The metric.compat stores compatibilty information
    # NOTE this part is not complete yet
    metric.compat.save(os.path.join("oras-compat-facts.json"))
    metric.compat.show_table()

    # EXAMPLE 2: Pairwise diffs TODO
    # matrix = metric.get_diff_matrix()

    # Just save to file and cleanup
    metric.save_json("./data", force=True)
    extractor.cleanup(force=True)


if __name__ == "__main__":
    main()
