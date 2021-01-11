__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2021, Vanessa Sochat"
__license__ = "MPL 2.0"

import os
import sys
import pytest

here = os.path.abspath(os.path.dirname(__file__))


def test_pypi_analyze(tmp_path):
    """test pypi analyzer"""
    print("Testing Pypi Analyer")
    from caliper.analysis import CaliperAnalyzer
    from caliper.utils.file import read_json

    config_file = os.path.join(here, "data", "analyze", "caliper.yaml")
    client = CaliperAnalyzer(config_file)
    analyzer = client.get_analyzer()
    analyzer.run_analysis(cleanup=True)

    outdir = os.path.join(here, "data", "analyze", ".caliper")
    assert os.path.exists(outdir)
    outfile = os.path.join(outdir, "data", "pypi-sif-0.0.11-python-cp27.json")
    assert os.path.exists(outfile)

    # Check fields in output file
    result = read_json(outfile)
    for key in ["inputs", "tests", "requirements.txt"]:
        assert key in result and result[key] is not None
    for key in [
        "dependency",
        "outfile",
        "dockerfile",
        "force",
        "exists",
        "name",
        "tests",
        "cleanup",
        "outdir",
    ]:
        assert key in result["inputs"] and result["inputs"][key] is not None
