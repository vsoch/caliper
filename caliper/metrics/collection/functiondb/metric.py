__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2024, Vanessa Sochat"
__license__ = "MPL 2.0"

import ast
import os
import re
import sys
from collections import namedtuple

from caliper.logger import logger
from caliper.metrics.base import MetricBase
from caliper.utils.file import read_file, recursive_find

Import = namedtuple("Import", ["module", "name", "alias", "calls"])
Variable = namedtuple("Variable", ["module", "name"])


def walk(node):
    """A custom walk function using ast to get function calls"""
    end = [node]
    for n in ast.iter_child_nodes(node):
        if isinstance(n, ast.Call):
            end.append(n)
            continue
        end += walk(n)
    return end


def unpack_node(node):
    """Given a node, parse to the end until we hit the calling function"""
    names = [node.func.attr] if hasattr(node.func, "attr") else []
    value = getattr(node.func, "value", node.func)
    while value:
        if hasattr(value, "id"):
            names.append(value.id)
        elif hasattr(value, "attr"):
            names.append(value.attr)
        if not hasattr(value, "value"):
            value = None
        else:
            value = value.value
    if names:
        names.reverse()
    return names


def get_node_modules(root):
    """Given the root of a tree, walk and get a lookup of nodes based on the
    name assigned or module name
    """
    nodes = {}

    # First derive all node names
    for node in ast.iter_child_nodes(root):
        if isinstance(node, ast.Import):
            module = []
        elif isinstance(node, ast.ImportFrom):
            module = node.module.split(".")
        else:
            continue
        for n in node.names:
            newnode = Import(module, n.name, n.asname, set())
            if n.asname:
                nodes[n.asname] = newnode
            else:
                nodes[n.name] = newnode

    return nodes


def get_function_lookup(filepath):
    """A helper to, given an input file, parse out imports and functions used"""
    # Define a structure for an import with module, name, and alias
    root = ast.parse(read_file(filepath, False))

    # Keep a lookup of nodes based on calling name
    nodes = get_node_modules(root)
    tree = walk(root)

    # TODO: need to be able to parse targets

    # Find where are all called functions (doesn't account for class functions)
    # Also we aren't capturing args yet
    for node in tree:
        # An assignment might contain a call to a known module function
        names = []
        if isinstance(node, ast.Assign) and hasattr(node.value, "func"):
            names = unpack_node(node.value)
        elif not isinstance(node, ast.Call):
            continue
        elif hasattr(node, "func") and isinstance(node.func, ast.Attribute):
            if hasattr(node.func.value, "id"):
                module = getattr(node.func.value, "id")
                if module in nodes:
                    nodes[module].calls.add(node.func.attr)

            elif hasattr(node.func.value, "attr"):
                names = unpack_node(node)

        if names:
            module, rest = names[0], names[1:]
            if module in nodes:
                nodes[module].calls.add(".".join(rest))
                # else is functions that are like func1().func2() (targets)

    return nodes


def add_functions_jedi(filepath, modulepath, lookup=None):
    """if ast cannot parse the script (SyntaxError) we can attempt a simple
    parsing with jedi instead.
    """
    lookup = lookup or {}

    # The user isn't required to have jedi installed
    try:
        import jedi
    except ImportError:
        logger.error("jedi is required to parse older Python versions.")
        return lookup

    filename = os.path.basename(filepath)

    source = read_file(filepath, readlines=False)
    script = jedi.Script(source, path=filename)

    # If we have an init, then it's just the main class, otherwise module
    if filename != "__init__.py":
        modulepath = "%s.%s" % (modulepath, re.sub("[.]py$", "", filename))

    # Add the modulepath to the lookup
    lookup[modulepath] = {}

    # Add each of functions and classes - ignore others for now
    for function in script.get_names():
        # A module
        if function.description.startswith("def"):
            for signatures in function.get_signatures():
                lookup[modulepath][function.full_name] = [
                    param.name for param in signatures.params
                ]

        elif function.description.startswith("class"):
            lookup[modulepath][function.full_name] = {}
            for method in function.defined_names():
                for signatures in method.get_signatures():
                    # TODO: we possibly should use the method full name instead
                    lookup[modulepath][function.full_name][method.name] = [
                        param.name for param in signatures.params
                    ]

    return lookup


def add_functions(filepath, modulepath, lookup=None):
    lookup = lookup or {}
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
        lookup[modulepath][function.name] = [arg.arg for arg in function.args.args]

    for classname in classes:
        methods = [n for n in classname.body if isinstance(n, ast.FunctionDef)]
        lookup[modulepath][classname.name] = {}
        for method in methods:
            lookup[modulepath][classname.name][method.name] = [
                arg.arg for arg in method.args.args
            ]

    return lookup


class Functiondb(MetricBase):
    name = "functiondb"
    description = "for each commit, derive a function database lookup"
    extractor = "json"

    def __init__(self, git):
        super().__init__(git, __file__)

    def _extract(self, commit):
        # Add the temporary directory to the PYTHONPATH
        sys.path.insert(0, self.git.folder)
        lookup = self.create_lookup(modules=True)

        # If we get here and there is nothing in the lookup, likely no module
        if not lookup:
            lookup = self.create_lookup(modules=False)

        return lookup

    def create_lookup(self, modules=True):
        """Given the self.git.folder, parse over filenames and extract modules.
        We won't be able to parse Python 2.x files. If modules=True, we require
        an __init__.py to parse. Otherwise, we parse any Python files found.
        """
        # We will return the lookup
        lookup = {}

        # Keep track of counts
        count = 0
        issue_count = 0

        for filename in recursive_find(self.git.folder, "*.py"):
            # Skip files that aren't a module
            dirname = os.path.dirname(filename)

            # Assume that we are looking for modules
            if modules and not os.path.exists(os.path.join(dirname, "__init__.py")):
                continue

            # The module path is needed for a script calling the function
            count += 1
            modulepath = ".".join(
                os.path.dirname(filename)
                .replace(self.git.folder, "")
                .strip("/")
                .split("/")
            )

            # Remove purelib or platlib
            # https://www.python.org/dev/peps/pep-0427/#what-s-the-deal-with-purelib-vs-platlib
            modulepath = re.sub("^(purelib|platlib)[.]", "", modulepath)

            # Ignore any scripts that ast cannot parse
            try:
                lookup = add_functions(filename, modulepath, lookup)
            except SyntaxError:
                lookup = add_functions_jedi(filename, modulepath, lookup)
            except Exception:
                logger.debug("Issue parsing %s, skipping" % filename)
                issue_count += 1
                pass

        if lookup:
            logger.debug(
                "Successfully parsed %s files. %s were skipped." % (count, issue_count)
            )
        return lookup

    def get_results(self):
        """we only return file level results, as there are no summed group results"""
        return self._data
