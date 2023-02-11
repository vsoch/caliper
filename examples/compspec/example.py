#!/usr/bin/env/python3

# This is one way to get releases!
from caliper.managers import PypiManager
from caliper.metrics import MetricsExtractor


def main():
    manager = PypiManager("oras") 
    
    # Just do two specs for a diff 
    extractor = MetricsExtractor(manager)
    
    # This repository will have each release version represented as a tagged commit
    extractor.prepare_repository()

    # Extract metric for compspec
    metric = extractor.extract_metric("compspec")

    # How to get results
    data = metric.get_results()

    # Just save to file and cleanup
    metric.save_json('./data')
    extractor.cleanup(force=True)

if __name__ == "__main__":
    main()
