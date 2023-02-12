__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2023, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.metrics.base import MetricBase
from caliper.utils.file import recursive_find, read_file
from caliper.logger import logger

from collections import namedtuple
import ast
import os
import re
import sys


Import = namedtuple("Import", ["module", "name", "alias", "calls"])
Variable = namedtuple("Variable", ["module", "name"])

# Global variables, because we are terrible people
seen = set()
imports = set()

def add_functions(filepath, modulepath):
    """
    if ast cannot parse the script (SyntaxError) we can attempt a simple
    parsing with jedi instead.
    """
    try:
        import jedi
    except ImportError:
        logger.exit("jedi is required to for the compspec metric parser.")

    lookup = {}
    filename = os.path.basename(filepath)

    source = read_file(filepath, readlines=False)
    script = jedi.Script(source, path=filename)

    # If we have an init, then it's just the main class, otherwise module
    if filename != "__init__.py":
        modulepath = "%s.%s" % (modulepath, re.sub("[.]py$", "", filename))

    # Add the modulepath to the lookup
    lookup[modulepath] = {"exports": []}

    # Reset imports for the entire module
    global imports
    imports = set()

    # Add each of functions and classes - ignore others for now
    for entity in script.get_names():

        # Get the base entry for the jedi class
        # TODO does jedi have a better way to do this?
        entry = get_base_entry(entity)
        if "import " in entity.get_line_code():
            imports.add(entry['fullname'])
            continue

        lookup[modulepath]['exports'].append(entry)

    # Add imports if they are defined
    if imports:
        lookup[modulepath]['imports'] = list(imports)
    return lookup

def get_entry_definitions(entity):
    """
    Given an entity, get definitions
    """
    defs = []
    try:
        names = entity.defined_named()
    except:
        return defs

    for definition in names:

        # This can turn into a recursive mess
        if definition.full_name and definition.full_name in seen:
            continue

        # Mark seen
        seen.add(definition.full_name)

        # We get these as signatures
        if definition.type == "param":
            continue
        defs.append(get_base_entry(definition))
    return defs

def get_base_entry(entity):
    """
    Given a jedi api class (some entity) get a base entry.

    This is able to call itself by way of getting definitions and params.
    """
    docstring = entity.docstring()
    entry = {
        "description": entity.description,
        "fullname": entity.full_name,
        "modulename": entity.module_name,
        "modulepath": str(entity.module_path),
        "type": entity.type,
        "is_definition": entity.is_definition(),
        "is_stub": entity.is_stub(),
    }
    if docstring:
        entry["docstring"] = docstring

    # Assemble signature of parameters
    params = get_entry_params(entity)
    if params:
        entry["parameters"] = params

    # Assume if it's a module within a module, we would parse the file directly
    # If we don't do this we parse the entire Python install :)
    if entity.type == "module":
        return entry

    # These would be functions for a class, etc.
    defs = get_entry_definitions(entity)
    if defs:
        entry['definitions'] = defs
    return entry

def get_entry_params(entity):
    """
    Get parameters for an entity (if relevant)
    """
    params = []
    # TODO are there other signatures we are interested in?
    for sig in entity.get_signatures():
        for order, param in enumerate(sig.params):
            docstring = param.docstring()
            new_param = {
                "name": param.name,
                "type": param.type,
                "kind": param.kind.name,
                "order": order,
                "signature": sig.full_name,
            }
            if docstring:
                new_param["docstring"] = docstring
            params.append(new_param)
    return params


class Compspec(MetricBase):
    name = "compspec"
    description = "for each commit, derive a composition specification"
    extractor = "json"

    def _extract(self, commit=None):

        # Reset global cache to what we've seen
        global seen
        seen = set()

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
