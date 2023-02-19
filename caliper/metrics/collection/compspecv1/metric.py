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
from caliper.metrics.table import Table
from caliper.utils.file import get_tmpfile, read_file, recursive_find, write_json

try:
    # gast abstracts the ast of the actual python version. It is a requirement for
    # beniget and generally speaking a must-have for static analysis anyway.
    import beniget
    import gast as ast

    has_deps = True
except ImportError:
    has_deps = False


class AllImports(ast.NodeVisitor):
    """
    ast.Import and ast.ImportFrom are the only nodes that make use of alias,
    rely on that property to collect all imported definitions, not only the
    global ones.
    """

    def __init__(self, duc):
        self._result = set()
        self._duc = duc

    def visit_alias(self, node):
        self._result.add(self._duc.chains[node])

    def __iter__(self):
        return iter(self._result)

    def __contains__(self, value):
        return value in self._result


class Capture(ast.NodeVisitor):
    """
    Gathers the set of definitions used in a node but not locally defined.
    As an exception, we consider local imports as an external definition,
    because they come from "the outside".
    Also associates each of this definition to the set of attributes of this
    definition used with this node (if any).
    """

    def __init__(self, duc, imports):
        from collections import defaultdict

        self._chains = duc
        self._imports = imports  # all import definition, including local ones
        self._udc = beniget.UseDefChains(duc)
        self._users = set()  # users of local definitions
        self._captured = set()  # definitions that don't belong to local users
        self._attributes = defaultdict(set)  # maps def to attributes
        self.failed_visits = set()

    def visit_FunctionDef(self, node):
        # Initialize the set of node using a local variable. These nodes are
        # not part of the capture.
        for def_ in self._chains.locals[node]:
            # ignore local imports
            if def_ in self._imports:
                continue
            self._users.update(use.node for use in def_.users())
        try:
            self.generic_visit(node)
        except Exception:
            # Keep track of failed visits
            print(f"/failed/visit {node.name}")
            self.failed_visits.add(node.name)

    visit_AsyncFunctionDef = visit_FunctionDef

    visit_ClassDef = visit_FunctionDef

    def visit_Name(self, node):
        # Register reference to identifiers not locally defined.
        if isinstance(node.ctx, ast.Load):
            if node not in self._users:
                for def_ in self._udc.chains[node]:
                    self._captured.add(def_)

    def visit_Attribute(self, node):
        # Register usage of any attribute, but not modification of
        # existing attribute.
        if isinstance(node.ctx, ast.Load):
            for def_ in self._udc.chains[node.value]:
                self._attributes[def_].add(node.attr)
        self.generic_visit(node)

    def __iter__(self):
        return iter(self._captured)

    def attrs(self):
        return self._attributes


def imported(global_definitions, imports, node, duc):
    """
    Among all the definitions captured by `Capture`, some are builtin
    definitions (e.g. `print`). Filter them out. And some are local imports.
    Keep them!
    """
    captured = Capture(duc, imports)
    captured.visit(node)

    imported_defs = (global_definitions.union(imports)).intersection(captured)
    associated_attrs = captured.attrs()

    return imported_defs, associated_attrs, captured.failed_visits


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
    asname text NULLABLE,
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
    """
CREATE TABLE IF NOT EXISTS depends (
    parent text NULLABLE,
    attr text NULLABLE,
    function number NOT NULL,
    FOREIGN KEY (function) REFERENCES exports(id)
);
""",
]


class CompspecFacts:
    """
    Keep track of compatibility facts
    """

    def __init__(self):
        self.compat = {}
        self.versions = set()

    def add_missing_global(self, signature):
        """
        Globally missing across versions.
        """
        module = signature["module"]
        if "global" not in self.compat:
            self.compat["global"] = {}
        if module not in self.compat["global"]:
            self.compat["global"][module] = []
        missing = {
            "tag": "missing-module",
            "reason": "This module was not found in the database for any version",
            **signature,
        }
        if missing not in self.compat["global"][module]:
            self.compat["global"][module].append(missing)

    def add_incompatible(self, version, path, meta):
        """
        Add an incompatibility fact, simple for now (version, path, reason)

        We use the "tag" as an identifier, and we can eventually namespace these.
        """
        if version not in self.compat:
            self.compat[version] = {}
        if path not in self.compat[version]:
            self.compat[version][path] = []
        self.compat[version][path].append(meta)

    def save(self, path):
        """
        Save compat output to a path.
        """
        write_json(self.compat, path)

    def show_table(self):
        """
        Format the incompatibilities into a table.
        """
        # First row is titles
        rows = []
        for version, modules in self.compat.items():
            for path, items in modules.items():
                for item in items:
                    rows.append(
                        {
                            "version": version,
                            "path": path,
                            "tag": item["tag"],
                            "reason": item["reason"],
                        }
                    )

        t = Table(rows)
        t.table(title="Compspec Compatibilty Result", limit=None, sort_by="path")
        # TODO this seems off need to double check


class Compspecv1(MetricBase):
    name = "compspecv1"
    description = "for each commit, derive a composition specification"
    extractor = "json"

    def __init__(self, git=None, filename=__file__, db_file=None):
        """
        Create an extractor for Python facts that writes to a database.
        """
        # Parso is required to use
        if not has_deps:
            logger.exit(
                "beniget and gast are required to for the compspec metric parser."
            )

        super().__init__(git=git, filename=filename)

        # Keep track of what we skip or fail to visit
        self.skips = {}
        self.failed_visits = {}

        if db_file and os.path.exists(db_file):
            self.db_file = db_file
            self.db = database.Database(filename=self.db_file)
        else:
            self.db_file = get_tmpfile(prefix="caliper-", suffix=".sqlite")
            self.db = database.Database(
                create_sql=create_metrics_table, filename=self.db_file
            )

        # Keep a cache of high level checks
        self.cache = {"modules": {}}

        # Keep a record of compatibility assessments
        # This can be stored by version
        self.compat = CompspecFacts()

    def inspect_trace(self, trace):
        """
        Given a trace of interest, determine if it's relevant and has an incompatibility.

        We could limit to a subset of calls, but instead we want to look at lines too.
        """
        # Just look at calls for now, we can get into more detail if needed
        if trace["event"] != "call":
            return

        # Query for the module, we can't say anything if we don't know about it
        # This checks for the root module, before the first "."
        if not self.query("has_module", trace["module"]):
            return

        # If we find a module directly, we are good (we already determined having it above)
        if trace["function"] == "<module>":
            return

        # Do a query to our database for the module, this will get it across versions
        modules = self.query("get_module", trace["path"])

        # Case 1: we don't have the specific module, it's missing
        if not modules:
            self.compat.add_missing_global(trace)
            return

        # Now check for compatibility of each version
        # Note that we could save whatever granularity of info we want here
        for module in modules:
            self.compat.versions.add(module["version"])

            # Immediate fail if the module doesn't have params
            if trace["args"] and not module.get("params"):
                args_called = "(%s)" % ",".join(trace["args"])
                self.compat.add_incompatible(
                    module["version"],
                    module["path"],
                    {
                        "trace": trace,
                        "module": module,
                        "tag": "too-many-args",
                        "reason": f"Found {args_called} in trace but function allows zero",
                    },
                )
                continue

            # Immediate fail if the trace has more args than provided
            if len(trace["args"]) > len(module.get("params", [])):
                args_called = "(%s)" % ",".join(trace["args"])
                args_found = "(%s)" % ",".join([x["name"] for x in module["params"]])
                self.compat.add_incompatible(
                    module["version"],
                    module["path"],
                    {
                        "trace": trace,
                        "module": module,
                        "tag": "too-many-args",
                        "reason": f"Found {args_called} in trace but function allows {args_found}",
                    },
                )
                continue

    # Queries

    def query(self, query_name, query):
        """
        Query the database for particular attributes and items
        """
        queries = {
            "has_module": self.query_has_module,
            "get_module": self.query_get_module,
        }
        if query_name not in queries:
            logger.exit(
                f"{query_name} is not a recognized query for the {self.name} metric"
            )
        return queries[query_name](query)

    def query_get_module(self, value):
        """
        Get a module by name
        """
        res = self.db.execute(f"SELECT *,rowid from exports WHERE path='{value}'")
        modules = []
        for x in res:
            module = {
                "root": x[0],
                "module": x[1],
                "path": x[2],
                "function": x[3],
                "type": x[4],
                "version": x[5],
            }
            params = self.db.execute(f"SELECT * from params WHERE function='{x[-1]}'")
            if params:
                module["params"] = [
                    {"name": p[0], "type": p[1], "position": p[2], "default": p[3]}
                    for p in params
                ]
            modules.append(module)
        return modules

    def query_has_module(self, value):
        """
        Determine if the database has a particular module.
        """
        # Ensure we are dealing with the root module name
        value = value.split(".")[0]

        # Check the cache first!
        if value in self.cache["modules"]:
            return self.cache["modules"][value]

        res = self.db.execute(f"SELECT count(*) from exports WHERE root='{value}'")
        has_module = bool(res[0][0] != 0)
        self.cache["modules"][value] = has_module
        return has_module

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

        Remaining questions I have using beniget:

        1. How do I derivate decorators and defaults?
        2. What should I be doing with the attributes and local variables?
        3. Class inheritance?
        4. Are args provided in correct order?
        """
        # Add the temporary directory to the PYTHONPATH
        if self.git.folder not in sys.path:
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
            modulepath = re.sub("^(purelib|platlib)[.]", "", modulepath)
            self.add_functions(filename, modulepath, commit)

        if count:
            logger.debug(
                f"Successfully parsed {count} files. {issue_count} were skipped."
            )

    def _add_imports(self, module, modulepath, version, ancestors, imports, duc):
        """
        Wrapper to add imports to enter into database as one transaction
        """
        importlist = []
        for import_ in imports:
            importlist.append(
                self._parse_import(module, modulepath, version, ancestors, import_, duc)
            )

        # Add imports to the database
        self.db.execute_many("imports", importlist)

    def _parse_import(self, module, modulepath, version, ancestors, imp, duc):
        """
        Parse imports for a module
        """
        root = modulepath.split(".")[0]
        parent = ancestors.parent(imp.node)

        # Add the new import
        new_import = {
            "root": root,
            "path": modulepath,
            "tag": version,
            "asname": None,
            "module": None,
        }

        if isinstance(parent, ast.Import):
            alias = imp.node
            if alias.asname:
                new_import.update({"import": alias.name, "asname": alias.asname})
            else:
                new_import.update({"import": alias.name})

        elif isinstance(parent, ast.ImportFrom):
            alias = imp.node
            if alias.asname:
                new_import.update(
                    {
                        "import": alias.name,
                        "module": parent.module,
                        "asname": alias.asname,
                    }
                )
            else:
                new_import.update({"import": alias.name, "module": parent.module})
        return new_import

    def _add_locals(self, imported_globals, used_attrs, func_id):
        """
        Add local variables a function needs to the depends table.
        """
        needs = []
        for def_ in imported_globals:
            attrs = used_attrs.get(def_, [])
            if not attrs:
                new_dep = {"parent": def_.name(), "function": func_id, "attr": None}
                needs.append(new_dep)
            else:
                for attr in attrs:
                    new_dep = {
                        "parent": def_.name(),
                        "function": func_id,
                        "attr": str(attr),
                    }
                    needs.append(new_dep)

        # Add needs (locals are types) to the database
        if needs:
            self.db.execute_many("depends", needs)

    def _add_function(
        self, module, modulepath, version, global_definitions, imports, function, duc
    ):
        """
        Add an export of type function

        Dump all global definitions used by this function, and the associated
        accessed attributes if any.

        Also lists attributes used for each argument, but only through direct
        access (i.e. not walking through assignments etc).
        """
        # self.execute_many("instances", rows)
        # Root of the module, so we can quickly see if we have it
        root = modulepath.split(".", 1)[0]
        imported_globals, used_attrs, failed_visits = imported(
            global_definitions, imports, function.node, duc
        )
        name = function.name()
        if version not in self.failed_visits:
            self.failed_visits[version] = set()
        self.failed_visits[version] = self.failed_visits[version].union(failed_visits)

        new_func = {
            "root": root,
            "module": modulepath,
            "path": f"{modulepath}.{name}",
            "name": name,
            "type": "function",
            "tag": version,
        }
        self.db.execute_one("exports", new_func)

        # The function id is needed to be a foreign key to params/locals
        func_id = self.db.conn.lastrowid

        # We will call these local variables general needs/depends
        # for a function.
        if imported_globals:
            self._add_locals(imported_globals, used_attrs, func_id)

        # Add function parameters to "params" table
        params = self._parse_params(function, used_attrs, duc, func_id)
        if params:
            self.db.execute_many("params", params)

    def _parse_params(self, function, used_attrs, duc, func_id):
        """
        Add local variables a function needs to the depends table.
        """
        params = []

        function_args = function.node.args
        all_function_args = (
            function_args.args
            + function_args.posonlyargs
            + (function_args.vararg or [])
            + function_args.kwonlyargs
        )

        for i, arg in enumerate(all_function_args):
            arg_def = duc.chains[arg]

            param = {
                "function": func_id,
                "name": arg_def.name(),
                "position": i,
                "default_value": None,
                "type": None,
            }

            # Not sure what these attributes are (and where they should go)
            attrs = used_attrs.get(arg_def)
            if arg_def.node.annotation:
                if hasattr(arg_def.node.annotation, "value"):
                    arg_type = arg_def.node.annotation.value.id

                    # A slice means typing with something like a union
                    if hasattr(arg_def.node.annotation.slice, "elts"):
                        arg_type_inner = []
                        for entry in arg_def.node.annotation.slice.elts:
                            if hasattr(entry, "id"):
                                arg_type_inner.append(entry.id)
                            else:
                                arg_type_inner.append(entry.value.id)

                        if arg_type_inner:
                            param["type"] = f"{arg_type}{arg_type_inner}"
                        else:
                            param["type"] = arg_def.node.annotation.slice.id
                    else:
                        param["type"] = arg_type
                else:
                    param["type"] = arg_def.node.annotation.id

            params.append(param)

            # I don't know what to do with these still
            # How do parameters have attributes?
            if attrs:
                # Just assume it's some local need?
                needs = []
                for attr in attrs:
                    new_dep = {
                        "parent": arg_def.name(),
                        "function": func_id,
                        "attr": str(attr),
                    }
                    needs.append(new_dep)
                if needs:
                    self.db.execute_many("depends", needs)

        return params

    def _add_class(
        self,
        module,
        modulepath,
        version,
        global_definitions,
        imports,
        cls,
        duc,
    ):
        """
        Add an export of type class.

        Dump all global definitions used by this function, and the associated
        accessed attributes if any.

        This includes both static fields and function members, as long as they are
        referenced within the class body.

        It does not walk through the bases when doing so.
        """
        class_name = cls.name()
        root = modulepath.split(".", 1)[0]
        imported_globals, used_attrs, failed_visits = imported(
            global_definitions, imports, cls.node, duc
        )
        if version not in self.failed_visits:
            self.failed_visits[version] = set()
        self.failed_visits[version] = self.failed_visits[version].union(failed_visits)

        classpath = f"{modulepath}.{class_name}"
        new_cls = {
            "root": root,
            "module": modulepath,
            "tag": version,
            "path": classpath,
            "name": class_name,
            "type": "class",
        }

        self.db.execute_one("exports", new_cls)
        class_id = self.db.conn.lastrowid

        # TODO how to get inherited functions?
        # include decorators?

        if imported_globals:
            self._add_locals(imported_globals, used_attrs, class_id)

    def add_functions(self, filepath, modulepath, version):
        """
        Parse with... parso
        """
        filename = os.path.basename(filepath)
        source = read_file(filepath, readlines=False)

        module = ast.parse(source)

        # If we have an init, then it's just the main class, otherwise module
        if filename != "__init__.py":
            modulepath = "%s.%s" % (modulepath, re.sub("[.]py$", "", filename))

        # def -> use chains compute the link between a definition and its uses.
        duc = beniget.DefUseChains()
        duc.visit(module)

        # any import, either global or local.
        all_imports = AllImports(duc)
        all_imports.visit(module)

        # this keeps a mapping between a node and its parent in the AST.
        ancestors = beniget.Ancestors()
        ancestors.visit(module)

        # this contains global imports, but not local ones. Same for functions,
        # classes etc.
        global_definitions = set(duc.locals[module])

        # Do the extraction keeping the database connection open
        with self.db:
            # Add all imports via one transaction
            self._add_imports(module, modulepath, version, ancestors, all_imports, duc)

            # Go through global definitions
            for definition in sorted(global_definitions, key=lambda x: x.name()):
                # Don't add a definition we've seen as an import
                if definition in all_imports:
                    continue

                elif isinstance(definition.node, ast.ClassDef):
                    self._add_class(
                        module,
                        modulepath,
                        version,
                        global_definitions,
                        all_imports,
                        definition,
                        duc,
                    )

                elif isinstance(
                    definition.node, (ast.FunctionDef, ast.AsyncFunctionDef)
                ):
                    self._add_function(
                        module,
                        modulepath,
                        version,
                        global_definitions,
                        all_imports,
                        definition,
                        duc,
                    )
                else:
                    # Keep track of what we are skipping
                    if version not in self.skips:
                        self.skips[version] = set()
                    self.skips[version].add(definition.name())

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
            new_export = {"path": export[3], "module": export[2], "name": export[4]}

            # This is the row id to match to a parameter later
            lookup[export[0]] = new_export
            data[version][export[1]]["exports"].append(new_export)

        for entry in self.db.execute("select rowid, * from imports"):
            version = entry[-1]
            if version not in data:
                data[version] = {}
            if entry[1] not in data[version]:
                data[version][entry[1]] = {"imports": []}
            if "imports" not in data[version][entry[1]]:
                data[version][entry[1]]["imports"] = []
            new_import = {"path": entry[2]}
            if entry[3]:
                new_import["from"] = entry[3]
            if entry[4]:
                new_import["import"] = entry[4]
            if entry[5]:
                new_import["as"] = entry[5]
            data[version][entry[1]]["imports"].append(new_import)

        # Calls - what the function uses (and thus depends on)
        for call in self.db.execute("select * from depends"):
            func_id = call[-1]
            if "needs" not in lookup[func_id]:
                lookup[func_id]["needs"] = []
            new_call = {"parent": call[0], "attr": call[1]}
            lookup[func_id]["needs"].append(new_call)

        # This doesn't include the rowid
        for param in self.db.execute("select * from params"):
            func_id = param[-1]
            if "params" not in lookup[func_id]:
                lookup[func_id]["params"] = []
            new_param = {"name": param[0], "position": param[2]}
            if param[1]:
                new_param["type"] = param[1]
            if param[3]:
                new_param["default"] = param[3]
            lookup[func_id]["params"].append(new_param)

        for version, failed_visits in self.failed_visits.items():
            if failed_visits:
                data[version]["failed_visits"] = list(failed_visits)

        for version, skips in self.skips.items():
            if skips:
                data[version]["skipped"] = list(skips)
        return data
