#!/usr/bin/env python3

__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2021, Vanessa Sochat"
__license__ = "MPL 2.0"

import argparse
from caliper.utils.file import read_json, write_json
from distutils.version import StrictVersion

import sys
from glob import glob
import os
import re

here = os.path.dirname(os.path.abspath(__file__))

def get_parser():
    parser = argparse.ArgumentParser(description="Caliper Analysis Data Parser")
    parser.add_argument(
        "--package",
        dest="package",
        help="package on pypi to plot (should correspond to input files)",,
    )
    parser.add_argument(
        "-d",
        "--dir",
        dest="dirname",
        help="path to root caliper directory with results (defaults to .caliper)",
        default=".caliper",
    )
    return parser


def iter_files(dirname, package):
    """A helper function to iterate over result files (and skip others)"""
    # regular expression to identify raw result files
    result_regex = (
        "pypi-%s-(?P<tfversion>.+)-python-cp(?P<pversion>[0-9]+)[.]json" % package
    )

    for filename in glob("%s/*" % dirname):
        # Skip over non result files
        if not re.search(result_regex, filename):
            continue
        yield filename


class DependencyVersion:
    """Small helper class to easily derive versions"""

    def __init__(self, filename, package):
        result_regex = (
            "pypi-%s-(?P<tfversion>.+)-python-cp(?P<pversion>[0-9]+)[.]json" % package
        )
        self.match = re.search(result_regex, filename)

    @property
    def tfversion(self):
        return self.match["tfversion"]

    @property
    def pyversion(self):
        return self.match["pversion"]


def main():
    """main entrypoint for caliper analysis"""
    parser = get_parser()

    # If an error occurs while parsing the arguments, the interpreter will exit with value 2
    args, extra = parser.parse_known_args()

    # A package is required!
    if not args.package:
        sys.exit("Please specify a package that corresponds to your .caliper/data with --package.")

    dirname = os.path.abspath(args.dirname) if args.dirname else args.dirname
    if not dirname or not os.path.exists(dirname):
        sys.exit("A --dir directory folder with results is required.")

    # Step 1: build matrix of fail/success to plot
    results = parse_tests(dirname, args.package)


def parse_tests(dirname, package):
    """Assemble all tests results into one large data structure. This will
    be too large to load into the browser at once, but should be okay for Flask.
    """
    results = {}
    datadir = os.path.join(dirname, "data")

    # We need to keep a list of tests so the data structure is consistent
    tests = set()

    # We also want the versions sorted
    versions = set()
    groups = {}
    for filename in iter_files(datadir, package):
        basename = os.path.basename(filename)
        dep = DependencyVersion(filename, package)

        # Don't include release candidates, or a/b, etc.
        if re.search("(rc|a|b)", basename):
            continue

        if dep.tfversion not in groups:
            groups[dep.tfversion] = []
        groups[dep.tfversion].append(filename)
        versions.add(dep.tfversion)

    # Sort the versions, we will add them to groups
    versions = list(versions)
    versions.sort(key=StrictVersion)

    # Loop through sorted versions
    for version in versions:
        for filename in groups[version]:
            basename = os.path.basename(filename)

            # Create object to parse versions
            dep = DependencyVersion(filename, package)
            results[dep.pyversion] = []
            result = read_json(filename)
            for test in result.get("tests", []):
                tests.add(test)

    # Read in input files, organize by python version, library version
    for version in versions:
        for filename in groups[version]:
            basename = os.path.basename(filename)

            # Create object to parse versions
            dep = DependencyVersion(filename, package)

            # Make sure the test has at least one result
            result = read_json(filename)
            if "tests" not in result:
                result["tests"] = {"build": {"retval": result["build_retval"]}}

            # Make sure we have all tests, ordered the same, -1 indicates not run
            result_tests = result.get("tests", [])
            test_list = []
            for test in tests:
                if test in result_tests:
                    entry = result_tests[test]
                else:
                    entry = {"retval": -1}

                # y axis will be module version, x axis will be test name
                entry["x_name"] = test
                entry["y_module"] = dep.tfversion
                test_list.append(entry)

            results[dep.pyversion] += test_list

    # Write to output file so we can generate a d3
    outfile = os.path.join(here, "test-results-by-python.json")
    write_json(results, outfile)
    return outfile


if __name__ == "__main__":
    main()
