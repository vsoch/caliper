#!/usr/bin/env/python3

import os

from caliper.metrics import MetricsExtractor

here = os.path.dirname(os.path.abspath(__file__))


def main():
    # Just do two specs for a diff
    extractor = MetricsExtractor(working_dir=here)

    # Extract metric for compspec
    metric = extractor.extract_metric("compspec")

    # How to get results
    data = metric.get_results()
    assert data

    # TODO try https://github.com/davidhalter/parso
    # Just save to file and cleanup
    metric.save_json("./data", force=True)


if __name__ == "__main__":
    main()
