__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2023, Vanessa Sochat"
__license__ = "MPL 2.0"

import os
import re
import sys

from caliper.logger import logger
from caliper.metrics.base import MetricBase
from caliper.utils.file import read_file, recursive_find


def add_functions(filepath, modulepath):
    """
    Parse with jedi and parse
    """
    try:
        import parso

    except ImportError:
        logger.exit("parso is required to for the compspec metric parser.")

    lookup = {}
    filename = os.path.basename(filepath)
    source = read_file(filepath, readlines=False)

    # This can take a python version too.
    module = parso.parse(source)

    # If we have an init, then it's just the main class, otherwise module
    if filename != "__init__.py":
        modulepath = "%s.%s" % (modulepath, re.sub("[.]py$", "", filename))

    # Add the modulepath to the lookup
    lookup[modulepath] = {}
    imports = get_module_imports(module)
    exports = get_module_exports(module, modulepath)

    if imports:
        lookup[modulepath]["imports"] = imports
    if exports:
        lookup[modulepath]["exports"] = exports

    return lookup


def get_module_exports(module, modulepath):
    """
    Get exports (functions, classes, etc) defined for a module
    """
    exports = []
    for cls in module.iter_classdefs():
        exports.append(parse_class(cls, modulepath))

    for func in module.iter_funcdefs():
        exports.append(parse_function(func, modulepath))
    return exports


def parse_function(func, modulepath):
    """
    Parse a function entry to add to exports defined by module.
    """
    new_func = {
        "name": func.name.value,
        "path": f"{modulepath}.{func.name.value}",
        "type": "function",
    }
    decorators = parse_decorators(func.get_decorators())
    if decorators:
        new_func["decorators"] = decorators

    params = get_function_params(func)
    if params:
        new_func["params"] = params
    return new_func


def parse_decorators(decorators):
    """
    Parse decorators into simple listing.
    """
    import parso.python.tree

    items = []
    for decorator in decorators:
        name = None
        for child in decorator.children:
            # This is the function name
            if isinstance(child, parso.python.tree.Name):
                name = child.value
                break

        # If we don't get the name, get the entire signatures
        signature = decorator.get_code().strip()
        if not name:
            name = signature
        items.append({"name": name, "signature": signature})
    return items


def parse_class(cls, modulepath):
    """
    Parse a class into an entry for our export listing.
    """
    classpath = f"{modulepath}.{cls.name.value}"
    new_cls = {"name": cls.name.value, "path": classpath, "type": "class"}
    exports = get_module_exports(cls, f"{modulepath}.{cls.name.value}")
    imports = get_module_imports(cls)
    if exports:
        new_cls["functions"] = exports
    if imports:
        new_cls["imports"] = exports
    return new_cls


def get_function_params(func):
    """
    Get parameters for a function.
    """
    params = []
    for param in func.get_params():
        new_param = {"name": param.name.value, "order": param.position_index}
        if param.default:
            # This seems to present numbers as strings
            if not hasattr(param.default, "value"):
                new_param["default"] = param.default.get_code().strip()
                continue

            if param.default.type == "number":
                try:
                    new_param["default"] = int(param.default.value)
                except ValueError:
                    new_param["default"] = float(param.default.value)
            else:
                new_param["default"] = param.default.value

        # Is it expanded? (do we care?)
        if param.star_count:
            new_param["star_count"] = param.star_count

        # For now just get raw type
        if param.annotation:
            new_param["type"] = param.annotation.get_code().strip()
        params.append(new_param)
    return params


def get_module_imports(module):
    """
    Get imports from a module.
    """
    imports = []
    for lib in module.iter_imports():
        new_import = {}

        # This is in the format from X import ...
        from_names = []
        if hasattr(lib, "get_from_names"):
            from_names = [x.value for x in lib.get_from_names()]

        if from_names:
            new_import["from"] = from_names

        # From <thing> import *
        if lib.is_star_import is True:
            new_import["star_import"] = True

        # This is the format <optional> import X
        defined_names = []
        for defined in lib.get_defined_names():
            defined_names.append(defined.value)
        if defined_names:
            new_import["import"] = defined_names
        imports.append(new_import)
    return imports


class Compspec(MetricBase):
    name = "compspec"
    description = "for each commit, derive a composition specification"
    extractor = "json"

    def _extract(self, commit=None):
        # Add the temporary directory to the PYTHONPATH
        sys.path.insert(0, self.git.folder)

        lookup = self.create_lookup(modules=True)

        # If we get here and there is nothing in the lookup, likely no module
        if not lookup:
            lookup = self.create_lookup(modules=False)

        return lookup

    def create_lookup(self, modules=True):
        """
        Given a repository, create a compspec lookup.
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
            lookup.update(add_functions(filename, modulepath))

        if lookup:
            logger.debug(
                f"Successfully parsed {count} files. {issue_count} were skipped."
            )
        return lookup

    def get_results(self):
        """
        We only return file level results, as there are no summed group results
        """
        return self._data
