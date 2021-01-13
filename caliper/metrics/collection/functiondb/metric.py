__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.metrics.base import MetricBase
from caliper.utils.file import recursive_find
from inspect import getmembers, isfunction

import inspect
import os
import importlib
import sys


class Functiondb(MetricBase):

    name = "functiondb"
    description = "for each commit, derive a function database lookup"

    def __init__(self, git):
        super().__init__(git, __file__)

    def _extract(self, commit):

        # We will return the lookup
        lookup = {}

        # Add the temporary directory to the PYTHONPATH
        sys.path.insert(0, self.git.folder)

        # Helper function to populate lookup
        def add_functions(module):
            # member[0] is function name, member[1] is function
            for member in getmembers(module, isfunction):
                lookup[modulepath][member[0]] = {
                    key: param.default if not inspect._empty else "inspect._empty"
                    for key, param in dict(
                        inspect.signature(member[1]).parameters
                    ).items()
                }

        # Look for folders with an init
        for folder in recursive_find(self.git.folder, "__init__.py"):

            # First try importing the top level modules
            modulepath = ".".join(
                os.path.dirname(folder)
                .replace(self.git.folder, "")
                .strip("/")
                .split("/")
            )
            lookup[modulepath] = {}
            module = importlib.import_module(modulepath)
            add_functions(module)

            # Next look for other modules in each init folder
            for modulename in os.listdir(os.path.dirname(folder)):
                if (
                    modulename
                    in [
                        "__init__.py",
                        "__pycache__",
                    ]
                    or not modulename.endswith(".py")
                ):
                    continue

                try:
                    module = importlib.import_module(
                        "%s.%s" % (modulepath, modulename.replace(".py", ""))
                    )
                    add_functions(module)
                except:
                    pass

        return lookup

    def get_file_results(self):
        """return a lookup of changes, where each change has a list of files"""
        return self._data

    def get_group_results(self):
        """Get summed values (e.g., lines changed) across files"""
        return self._data
