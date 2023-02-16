__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2023, Vanessa Sochat"
__license__ = "MPL 2.0"

import os
import re
import sys
from datetime import datetime

import caliper.metrics.database as database
from caliper.logger import logger
from caliper.metrics.base import MetricBase
from caliper.utils.file import get_tmpfile, read_file, recursive_find

try:
    import parso

    has_parso = True
except ImportError:
    has_parso = False


def parse_function(func, modulepath, version):
    """
    Parse a function entry to add to exports defined by module.
    """
    new_func = {
        "name": func.name.value,
        "path": f"{modulepath}.{func.name.value}",
        "tag": version,
        "type": "function",
    }
    decorators = parse_decorators(func.get_decorators())
    if decorators:
        new_func["decorators"] = decorators

    params = get_function_params(func)
    if params:
        new_func["params"] = params
    return new_func


def parse_class(cls, modulepath, version):
    """
    Parse a class into an entry for our export listing.
    """
    root = modulepath.split(".", 1)[0]
    classpath = f"{modulepath}.{cls.name.value}"
    return {
        "root": root,
        "module": modulepath,
        "tag": version,
        "path": classpath,
        "name": cls.name.value,
        "type": "class",
    }


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


def get_function_params(func):
    """
    Get parameters for a function.
    """
    params = []
    for param in func.get_params():
        new_param = {
            "name": param.name.value,
            "position": param.position_index,
            "default_value": None,
        }
        if param.default:
            # This seems to present numbers as strings
            if not hasattr(param.default, "value"):
                new_param["default_value"] = param.default.get_code().strip()
                continue

            if param.default.type == "number":
                try:
                    new_param["default_value"] = int(param.default.value)
                except ValueError:
                    new_param["default_value"] = float(param.default.value)
            else:
                new_param["default_value"] = param.default.value

        # Is it expanded? (do we care?)
        if param.star_count:
            new_param["star_count"] = param.star_count

        # For now just get raw type
        if param.annotation:
            new_param["type"] = param.annotation.get_code().strip()
        params.append(new_param)
    return params


# The table will be flat - storage for our metrics we want to extract
# This design can be better optimized with a module table and more
# foreign keys.
create_metrics_table = [
    """
CREATE TABLE IF NOT EXISTS imports (
    root text NOT_NULL,
    path text NOT NULL,
    module text NULLABLE,
    import text NOT NULL,
    tag text NOT NULL
);""",
    """
CREATE TABLE IF NOT EXISTS exports (
    root text NOT_NULL,
    module text NOT NULL,
    path text NULLABLE,
    name text NULLABLE,
    type text NOT NULL,
    tag text NOT NULL
);""",
    """
CREATE TABLE IF NOT EXISTS params (
    name text NULLABLE,
    type text NULLABLE,
    position number NULLABLE,
    default_value text NULLABLE,
    function number NOT NULL,
    FOREIGN KEY (function) REFERENCES exports(id)
);
""",
]


class Compspec(MetricBase):
    name = "compspec"
    description = "for each commit, derive a composition specification"
    extractor = "json"

    def __init__(self, git=None, filename=__file__):
        """
        Create an extractor for Python facts that writes to a database.
        """
        # Parso is required to use
        if not has_parso:
            logger.exit("parso is required to for the compspec metric parser.")

        super().__init__(git=git, filename=filename)
        self.db_file = get_tmpfile(prefix="caliper-", suffix=".sqlite")
        self.db = database.Database(
            create_sql=create_metrics_table, filename=self.db_file
        )

    def extract(self):
        """
        Extract for a metric base assumes one timepoint, so we checkout the
        commit for the user.
        """
        # Not all extractors require commits (can be for current state)
        if not self.has_tags():
            now = datetime.now().strftime("%Y-%m-%d")
            logger.info(
                f"{self.git.folder} does not have tags, extracting for current state."
            )
            self._extract(commit=now)
            return

        for tag, index in self.iter_tags():
            self.git.checkout(str(tag.commit), dest=self.git.folder)
            self._extract(commit=index)

    def _extract(self, commit):
        """
        Main function to run extraction.
        """
        # Add the temporary directory to the PYTHONPATH
        sys.path.insert(0, self.git.folder)

        # Keep track of counts
        count = 0
        issue_count = 0

        for filename in recursive_find(self.git.folder, "*.py"):
            # Skip files that aren't a module
            dirname = os.path.dirname(filename)

            # Assume that we are looking for modules
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

            # Remove purelib or platlib
            # https://www.python.org/dev/peps/pep-0427/#what-s-the-deal-with-purelib-vs-platlib
            modulepath = re.sub("^(purelib|platlib)[.]", "", commit)
            self.add_functions(filename, modulepath, commit)

        if count:
            logger.debug(
                f"Successfully parsed {count} files. {issue_count} were skipped."
            )

    def _add_imports(self, module, modulepath, version):
        """
        Add imports for a module
        """
        root = modulepath.split(".")[0]

        # When the database context is open, we can access self.db.conn
        imports = []
        for lib in module.iter_imports():
            # This is in the format from X import ...
            from_names = []
            if hasattr(lib, "get_from_names"):
                from_names = list(lib.get_from_names())

            for defined in lib.get_defined_names():
                new_import = {
                    "root": root,
                    "path": modulepath,
                    "import": defined.value,
                    "tag": version,
                }
                if from_names:
                    for from_name in from_names:
                        new_import["module"] = from_name.value
                        imports.append(new_import)
                else:
                    new_import["module"] = None
                    imports.append(new_import)

        # Add imports to the database
        self.db.execute_many("imports", imports)

    def _add_exports(self, module, modulepath, version):
        """
        Add exports (functions, classes, etc) defined for a module
        """
        # self.execute_many("instances", rows)
        # Root of the module, so we can quickly see if we have it
        root = modulepath.split(".", 1)[0]

        # When the database context is open, we can access self.db.conn
        for cls in module.iter_classdefs():
            new_cls = parse_class(cls, modulepath, version)
            self.db.execute_one("exports", new_cls)
            func_id = self.db.conn.lastrowid

            # Parse functions / classes
            self._add_exports(cls, f"{modulepath}.{cls.name.value}", version)
            self._add_imports(cls, f"{modulepath}.{cls.name.value}", version)

        for func in module.iter_funcdefs():
            new_func = parse_function(func, modulepath, version)
            row = {
                "root": root,
                "module": modulepath,
                "path": new_func["path"],
                "name": new_func["name"],
                "type": "function",
                "tag": version,
            }
            self.db.execute_one("exports", row)

            # We need the function ID to add all the params
            # as a foreign key!
            func_id = self.db.conn.lastrowid
            for param in new_func.get("params", []):
                param["function"] = func_id
            if new_func.get("params"):
                self.db.execute_many("params", new_func["params"])

    def add_functions(self, filepath, modulepath, version):
        """
        Parse with... parso
        """
        filename = os.path.basename(filepath)
        source = read_file(filepath, readlines=False)

        # This can take a python version too.
        module = parso.parse(source)

        # If we have an init, then it's just the main class, otherwise module
        if filename != "__init__.py":
            modulepath = "%s.%s" % (modulepath, re.sub("[.]py$", "", filename))

        # Do the extraction keeping the database connection open
        with self.db:
            self._add_exports(module, modulepath, version)
            self._add_imports(module, modulepath, version)

    def get_results(self):
        """
        This exports to json, use with caution!
        """
        data = {}
        lookup = {}
        for export in self.db.execute("select rowid, * from exports"):
            # Top level of data indexed by version
            version = export[-1]
            if version not in data:
                data[version] = {}

            # Then by module name
            if export[1] not in data[version]:
                data[version][export[1]] = {"exports": []}
            new_export = {"path": export[2], "name": export[3], "type": export[4]}

            # This is the row id to match to a parameter later
            lookup[export[0]] = new_export
            data[version][export[1]]["exports"].append(new_export)

        for entry in self.db.execute("select rowid, * from imports"):
            version = export[-1]
            if version not in data:
                data[version] = {}
            if entry[1] not in data[version]:
                data[entry[1]] = {"imports": []}
            if "imports" not in data[version][entry[1]]:
                data[version][entry[1]]["imports"] = []
            new_import = {"path": entry[2]}
            if entry[3]:
                new_import["from"] = entry[3]
            if entry[4]:
                new_import["import"] = entry[4]
            data[version][entry[1]]["imports"].append(new_import)

        # This doesn't include the rowid
        for param in self.db.execute("select * from params"):
            func_id = param[-1]
            if "params" not in lookup[func_id]:
                lookup[func_id]["params"] = []
            lookup[func_id]["params"].append(
                {
                    "name": param[1],
                    "type": param[2],
                    "position": param[3],
                    "default": param[4],
                }
            )
        return data
