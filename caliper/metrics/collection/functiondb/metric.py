__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.metrics.base import MetricBase
from caliper.utils.file import recursive_find, read_file

import ast
import os
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
        def add_functions(filename, modulepath):

            node = ast.parse(read_file(filename, False))
            functions = [n for n in node.body if isinstance(n, ast.FunctionDef)]
            classes = [n for n in node.body if isinstance(n, ast.ClassDef)]

            # Add each of functions and classes - ignore default values for now
            for function in functions:
                lookup[modulepath][function.name] = [
                    arg.arg for arg in function.args.args
                ]

            for classname in classes:
                methods = [n for n in classname.body if isinstance(n, ast.FunctionDef)]
                lookup[modulepath][classname.name] = {}
                for method in methods:
                    lookup[modulepath][classname.name][method.name] = [
                        arg.arg for arg in method.args.args
                    ]

        # Look for folders with an init
        for filename in recursive_find(self.git.folder, "*.py"):

            # Skip files that aren't a module
            dirname = os.path.dirname(filename)
            if not os.path.exists(os.path.join(dirname, "__init__.py")):
                continue

            # The module path is needed for a script calling the function
            modulepath = ".".join(
                os.path.dirname(filename)
                .replace(self.git.folder, "")
                .strip("/")
                .split("/")
            )
            lookup[modulepath] = {}

            # Ignore any scripts that ast cannot parse
            try:
                add_functions(filename, modulepath)
            except:
                pass

        return lookup

    def get_file_results(self):
        """we only return file level results, as there are no summed group results"""
        return self._data
