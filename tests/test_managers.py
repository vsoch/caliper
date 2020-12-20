__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

import os
import sys
import pytest


def test_pypi_manager(tmp_path):
    """test pypi manager"""
    print("Testing Pypi Manager")
    from caliper.managers import PypiManager

    manager = PypiManager("pypi:sregistry")
    assert manager.name == "pypi"
    assert manager.uri == "pypi:sregistry"
    assert manager.package_name == "sregistry"
    assert len(manager.specs) >= 82
    assert manager.baseurl == "https://pypi.python.org/pypi"

    # Ensure we have correct metadata
    for key in ["name", "version", "source", "hash"]:
        assert key in manager.specs[0]

    for key in ["filename", "type"]:
        assert key in manager.specs[0]["source"]
