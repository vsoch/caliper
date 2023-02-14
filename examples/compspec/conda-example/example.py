#!/usr/bin/env/python3

# This is one way to get releases!
from caliper.managers import CondaManager
from caliper.metrics import MetricsExtractor


def main():
    # channel, subdir, package name
    manager = CondaManager("conda-forge/noarch/redo")

    # Just do two specs for a diff
    extractor = MetricsExtractor(manager)

    # This repository will have each release version represented as a tagged commit
    extractor.prepare_repository()

    # Extract metric for compspec
    metric = extractor.extract_metric("compspec")

    # How to get results
    data = metric.get_results()
    assert data

    # Just save to file and cleanup
    metric.save_json("./data", force=True)
    extractor.cleanup(force=True)


if __name__ == "__main__":
    main()
