__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.metrics.base import MetricBase
from caliper.utils.file import recursive_find, read_file
from caliper.logger import logger

import ast
import os
import re
import sys


class Functiondb(MetricBase):

    name = "functiondb"
    description = "for each commit, derive a function database lookup"
    extractor = "json"

    def __init__(self, git):
        super().__init__(git, __file__)

    def _extract(self, commit):

        # We will return the lookup
        lookup = {}

        # Add the temporary directory to the PYTHONPATH
        sys.path.insert(0, self.git.folder)

        # Checkout the right commit

        # Helper function to populate lookup
        def add_functions(filepath, modulepath):

            filename = os.path.basename(filepath)
            node = ast.parse(read_file(filepath, False))
            functions = [n for n in node.body if isinstance(n, ast.FunctionDef)]
            classes = [n for n in node.body if isinstance(n, ast.ClassDef)]

            # If we have an init, then it's just the main class, otherwise module
            if filename != "__init__.py":
                modulepath = "%s.%s" % (modulepath, re.sub("[.]py$", "", filename))

            # Add the modulepath to the lookup
            lookup[modulepath] = {}

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

        # Keep track of counts
        count = 0
        issue_count = 0
        for filename in recursive_find(self.git.folder, "*.py"):

            # Skip files that aren't a module
            dirname = os.path.dirname(filename)
            if not os.path.exists(os.path.join(dirname, "__init__.py")):
                continue

            # The module path is needed for a script calling the function
            count += 1
            modulepath = ".".join(
                os.path.dirname(filename)
                .replace(self.git.folder, "")
                .strip("/")
                .split("/")
            )

            # Ignore any scripts that ast cannot parse
            try:
                add_functions(filename, modulepath)
            except:
                logger.debug("Issue parsing %s, skipping" % filename)
                issue_count += 1
                pass

        logger.debug(
            "Successfully parsed %s files. %s were skipped." % (count, issue_count)
        )
        return lookup

    def get_results(self):
        """we only return file level results, as there are no summed group results"""
        return self._data
